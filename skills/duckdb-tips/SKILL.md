---
name: duckdb-tips
description: Optimize, review, and troubleshoot DuckDB SQL and data layouts. Use when a coding agent must improve a slow DuckDB query, reduce memory or I/O, analyze EXPLAIN or profiling output, choose joins or indexes, optimize aggregations and scans, tune parallelism, or design tables and Parquet data for selective analytical queries.
---

# DuckDB Query Optimization

Optimize from evidence, not folklore. Preserve query semantics and correctness before improving speed.

## Required workflow

1. Establish the workload: table sizes, storage format/location, expected result cardinality, repeated-query frequency,
   write/read ratio, memory limit, and DuckDB version.
2. Capture a baseline with representative data and warm-up policy. Use `EXPLAIN ANALYZE` for operator timing and
   cardinalities.
3. Find the dominant cost: scan/I/O, cardinality explosion, join, aggregation, sort, repeated parsing/planning, or
   spill.
4. Apply the smallest relevant optimization from this guide.
5. Re-run the same benchmark and compare runtime, rows processed, bytes/files read, peak memory, and result equality.
6. Report the reason each change helps. Do not claim an improvement without measurement.

## 1. Project only required columns

**Reason:** DuckDB is columnar. Referencing fewer columns reduces storage reads, decompression, vector materialization,
memory traffic, and intermediate-row width. This matters especially for wide tables and Parquet/remote scans.

**Bad**

```sql
SELECT *
FROM events
WHERE event_type = 'purchase';
```

**Good**

```sql
SELECT user_id, revenue, occurred_at
FROM events
WHERE event_type = 'purchase';
```

Also avoid carrying unused columns through joins and CTEs. Project narrow inputs before expensive operators when the
optimizer cannot eliminate them.

## 2. Write pushdown-friendly filters

**Reason:** Filters that can be evaluated at the scan reduce rows and row groups read before joins, sorts, and
aggregates. Direct predicates on physical columns can use Parquet statistics and DuckDB zonemaps.

### Prefer direct, typed predicates

**Bad** — transforming the filtered column can prevent row-group pruning:

```sql
SELECT user_id
FROM events
WHERE CAST(occurred_at AS DATE) = DATE '2026-07-28';
```

**Good** — equivalent half-open range on the stored column:

```sql
SELECT user_id
FROM events
WHERE occurred_at >= TIMESTAMP '2026-07-28 00:00:00'
  AND occurred_at < TIMESTAMP '2026-07-29 00:00:00';
```

Or materialize a commonly filtered expression:

```sql
CREATE TABLE events_optimized AS
SELECT *, CAST(occurred_at AS DATE) AS event_date
FROM events
ORDER BY event_date, tenant_id;
```

```sql
SELECT user_id
FROM events_optimized
WHERE event_date = DATE '2026-07-28';
```

### Filter before a blocking or cardinality-expanding operation

DuckDB normally pushes safe predicates automatically. Rewrite only when `EXPLAIN ANALYZE` shows the filter remains above
a join, window, aggregate, `UNION`, or other barrier.

**Bad**

```sql
SELECT *
FROM (SELECT e.*,
             row_number() OVER (
        PARTITION BY user_id ORDER BY occurred_at DESC
    ) AS rn
      FROM events e) x
WHERE event_type = 'purchase';
```

**Good** — filter before computing the window when semantics permit:

```sql
SELECT *
FROM (SELECT e.*,
             row_number() OVER (
        PARTITION BY user_id ORDER BY occurred_at DESC
    ) AS rn
      FROM events e
      WHERE event_type = 'purchase') x;
```

### Do not optimize textual predicate order

The order of independent `AND` conditions is not a reliable optimization because DuckDB reorders and pushes filters.

**Bad advice**

```sql
-- Do not claim this is faster merely because user_id appears first.
WHERE user_id = 'specific-user' AND year = 2026
```

Focus on predicate shape, selectivity, and whether pushdown appears in the plan.

## 3. Prevent accidental cardinality explosions

**Reason:** Intermediate row counts dominate CPU and memory. A missing or incomplete join condition can multiply both
inputs and make every later operator expensive.

**Bad**

```sql
SELECT *
FROM orders,
     customers;
```

**Good**

```sql
SELECT o.order_id, c.segment
FROM orders o
         JOIN customers c
              ON o.customer_id = c.id;
```

When a many-to-many join is intentional, estimate its output first:

```sql
SELECT count(*)
FROM left_table l
         JOIN right_table r ON l.key = r.key;
```

Treat `CROSS_PRODUCT`, unexpectedly large actual cardinalities, and rapidly growing join inputs as red flags.

## 4. Use the join that matches the question

**Reason:** A regular join returns columns and may duplicate rows. Semi/anti joins answer existence questions without
materializing duplicate matches.

### Existence test

**Bad** — join then deduplicate:

```sql
SELECT DISTINCT o.customer_id
FROM orders o
         JOIN customers c ON c.id = o.customer_id
WHERE c.segment = 'enterprise';
```

**Good**

```sql
SELECT DISTINCT o.customer_id
FROM orders o
WHERE EXISTS (SELECT 1
              FROM customers c
              WHERE c.id = o.customer_id
                AND c.segment = 'enterprise');
```

Or use an explicit semi join:

```sql
SELECT DISTINCT o.customer_id
FROM orders o SEMI JOIN customers c
ON c.id = o.customer_id
    AND c.segment = 'enterprise';
```

### Missing-match test

**Bad**

```sql
SELECT o.*
FROM orders o
         LEFT JOIN customers c ON c.id = o.customer_id
WHERE c.id IS NULL;
```

**Good**

```sql
SELECT o.*
FROM orders o
WHERE NOT EXISTS (SELECT 1
                  FROM customers c
                  WHERE c.id = o.customer_id);
```

### Let DuckDB choose build/probe sides by default

DuckDB's optimizer can reorder inner joins and swap build/probe sides using statistics. Do not assume placing the
smaller table on a particular textual side improves performance. Intervene only after profiling shows a bad join order;
then update statistics, simplify estimates, or materialize a selective intermediate result.

## 5. Reduce rows before joins

**Reason:** Joining fewer rows reduces hash-table size, probes, memory, and downstream aggregation cost.

### Pre-aggregate when mathematically equivalent

**Bad**

```sql
SELECT u.segment, sum(e.revenue)
FROM events e
         JOIN users u ON u.id = e.user_id
WHERE e.event_type = 'purchase'
GROUP BY u.segment;
```

**Good**

```sql
WITH user_revenue AS (SELECT user_id, sum(revenue) AS total_revenue
                      FROM events
                      WHERE event_type = 'purchase'
                      GROUP BY user_id)
SELECT u.segment, sum(ur.total_revenue)
FROM user_revenue ur
         JOIN users u ON u.id = ur.user_id
GROUP BY u.segment;
```

Only pre-aggregate when it preserves semantics. Check duplicate dimension keys, outer joins, non-additive metrics, and
distinct counts.

### Materialize a selective stage when estimates or reuse justify it

```sql
CREATE
OR REPLACE TEMP TABLE recent_purchases AS
SELECT user_id, revenue
FROM events
WHERE event_type = 'purchase'
  AND occurred_at >= DATE '2026-01-01';

ANALYZE
recent_purchases;
```

Use this when the stage is reused, substantially smaller, or needed to force a stable join boundary. Do not materialize
every CTE: extra scans and writes can be slower.

## 6. Combine related aggregations

**Reason:** `GROUPING SETS`, `ROLLUP`, and conditional aggregates can replace repeated scans and repeated hash
aggregation.

**Bad** — three scans:

```sql
SELECT 'total' AS level, NULL AS region, NULL AS product_id, sum(revenue)
FROM events;
SELECT 'region', region, NULL, sum(revenue)
FROM events
GROUP BY region;
SELECT 'product', region, product_id, sum(revenue)
FROM events
GROUP BY region, product_id;
```

**Good** — one logical aggregation pipeline:

```sql
SELECT region, product_id, sum(revenue) AS revenue
FROM events
GROUP BY GROUPING SETS (
    (),
    (region),
    (region, product_id)
    );
```

For several metrics at the same grain, use `FILTER` instead of separate queries:

```sql
SELECT count(*) FILTER (WHERE event_type = 'login') AS logins, count(*) FILTER (WHERE event_type = 'purchase') AS purchases
FROM events;
```

## 7. Sort on load for selective scans

**Reason:** DuckDB automatically stores min/max metadata (zonemaps) for general-purpose columns. Clustering similar
values narrows each row group's range, allowing irrelevant row groups to be skipped. This complements column pruning; it
is not a traditional secondary index.

Use when tables are large, filters are selective and predictable, data is on disk/Parquet/S3/HTTP, and slower writes are
acceptable. Expect little benefit for full scans or unpredictable filters.

### Choose keys from real filter patterns

**Bad** — arbitrary or high-cardinality-first ordering:

```sql
CREATE TABLE events_sorted AS
SELECT *
FROM events
ORDER BY event_id;
```

**Good** — frequent, selective filters; lower-cardinality keys often first:

```sql
CREATE TABLE events_sorted AS
SELECT *
FROM events
ORDER BY region, event_type, tenant_id;
```

```sql
SELECT user_id, occurred_at
FROM events_sorted
WHERE region = 'eu-west'
  AND event_type = 'login'
  AND tenant_id = 42;
```

For time-heavy workloads, test bucketed time before exact timestamps:

```sql
CREATE TABLE events_sorted AS
SELECT *, date_trunc('month', occurred_at) AS event_month
FROM events
ORDER BY event_month, tenant_id;
```

### Prefer sorted bulk loads

**Bad**

```sql
-- Repeated single-row or tiny inserts fragment physical ordering.
INSERT INTO target
VALUES (?, ?, ?);
```

**Good**

```sql
INSERT INTO target
SELECT *
FROM staging
ORDER BY region, event_type, tenant_id;
```

For append-heavy tables, periodically rebuild/re-sort if independently sorted batches overlap enough to weaken pruning.

### Sort string prefixes when appropriate

DuckDB zonemaps for `VARCHAR` use the first bytes of string values; sorting a prefix can reduce sort cost while
preserving similar pruning.

```sql
CREATE TABLE strings_sorted AS
SELECT *
FROM strings
ORDER BY long_value[:8];
```

Validate with representative filters; prefix collisions reduce effectiveness.

## 8. Use ART indexes narrowly

**Reason:** ART indexes can accelerate point and extremely selective single-column lookups and enforce `PRIMARY KEY`/
`UNIQUE` constraints. They add memory, load, update, and maintenance cost and do not accelerate joins, aggregations, or
sorting.

**Bad** — indexing by reflex for an analytical scan:

```sql
CREATE INDEX idx_events_time ON events (occurred_at);
SELECT date_trunc('day', occurred_at), sum(revenue)
FROM events
GROUP BY 1;
```

**Good** — highly selective point lookup, after bulk loading:

```sql
CREATE INDEX idx_users_id ON users (user_id);
SELECT display_name
FROM users
WHERE user_id = 42;
```

Guidelines:

- Create explicit ART indexes only after measurement shows a highly selective lookup bottleneck.
- Create them after bulk loading.
- Ensure the index fits in memory during creation and leaves enough memory for analytical queries.
- Do not expect an ART index to negate sorted-table zonemap benefits; the mechanisms coexist. The optimizer may choose
  either an ART scan or zonemap-pruned scan.
- Do not state that range predicates always ignore ART indexes; verify the actual plan for the current DuckDB version
  and selectivity.

## 9. Inspect plans and profiles

**Reason:** Query text alone does not reveal actual cardinalities, optimizer decisions, parallel work, file pruning, or
spills.

Start with:

```sql
EXPLAIN
ANALYZE
SELECT category, sum(revenue)
FROM sales
WHERE sale_date >= DATE '2026-01-01'
GROUP BY category;
```

Read these signals:

- **Scan:** projected columns, pushed filters, rows/files read, and row-group pruning.
- **Cardinality:** estimated versus actual rows. Large mismatches can produce poor join orders or algorithms.
- **Join:** `CROSS_PRODUCT`, nested-loop joins on large inputs, or explosive intermediate rows.
- **Aggregate/sort:** high-cardinality grouping keys, large sorts, or most runtime concentrated in one blocking
  operator.
- **Parallel timing:** operator times are cumulative across threads; their sum can exceed wall-clock runtime.

Do not use invented universal thresholds such as “any node over 50% is the bottleneck” or “10x mismatch always means the
optimizer chose the wrong join.” Interpret the complete plan and validate experimentally.

## 10. Control memory and spilling

**Reason:** Hash joins, sorts, windows, and aggregations can exceed available memory. DuckDB can spill supported
operators to `temp_directory`, but disk I/O is slower and some workloads can still fail out of memory.

Inspect temporary files:

```sql
SELECT *
FROM duckdb_temporary_files();
```

Set explicit limits when needed:

```sql
SET
memory_limit = '8GB';
SET
temp_directory = '/fast-local-disk/duckdb-tmp';
```

**Bad:** raising threads or memory blindly while several DuckDB processes compete for the same host.

**Good:** reduce input width/rows first, use fast local temporary storage, set per-process budgets, and benchmark
concurrency.

For persistent OOMs, split the workload, materialize smaller stages, reduce threads, or rewrite operations that require
large blocking state.

## 11. Tune parallelism by measurement

**Reason:** DuckDB parallelizes scans and operators across row groups. More threads can improve throughput until CPU,
memory bandwidth, storage, row-group count, or operator serial sections become limiting. More threads also increase
memory pressure.

```sql
SELECT current_setting('threads');
SET
threads = 8;
```

**Bad:** hard-code “physical core count” or “16 threads” as universally optimal.

**Good:** benchmark a small set of values on the deployment hardware and workload, including concurrent-query scenarios.
Select the best total throughput or latency target, not the highest thread count.

## 12. Reuse prepared statements for repeated small queries

**Reason:** Prepared statements avoid repeating some parsing and planning work. The benefit is most visible when the
query itself is short and executed many times with different parameters.

**Bad** — rebuild SQL text for every point lookup:

```python
for user_id in ids:
    con.execute(f"SELECT name FROM users WHERE user_id = {user_id}")
```

**Good** — parameterize safely:

```python
for user_id in ids:
    con.execute(
        "SELECT name FROM users WHERE user_id = ?",
        [user_id],
    )
```

For large sets, prefer one set-based query over many point queries:

```sql
SELECT u.user_id, u.name
FROM users u
         JOIN requested_ids r USING (user_id);
```

## 13. Precompute repeated analytical results deliberately

**Reason:** A coarser summary table can reduce hundreds of millions of source rows to thousands. This is a data-model
optimization, not query-result caching.

**Bad** — assume a macro caches results:

```sql
CREATE
MACRO daily_active_users(d) AS (
    SELECT count(DISTINCT user_id)
    FROM sessions
    WHERE session_date = d
);
```

Macros expand SQL; they do not materialize or cache the result.

**Good** — maintain an explicit summary table:

```sql
CREATE
OR REPLACE TABLE daily_session_metrics AS
SELECT session_date,
       count(DISTINCT user_id) AS active_users,
       count(*)                AS sessions
FROM sessions
GROUP BY session_date;
```

Use when the same aggregation is queried frequently and the refresh policy is acceptable. Document freshness and
recomputation strategy.

## Output format for optimization reviews

Return findings in this order:

1. **Observed bottleneck** — cite plan/profile evidence.
2. **Recommended change** — show revised SQL or configuration.
3. **Why it helps** — name the reduced work: columns, rows, cardinality, I/O, memory, planning, or spill.
4. **Correctness risks** — note semantic assumptions.
5. **Validation** — provide an `EXPLAIN ANALYZE` or benchmark comparison and result-equivalence check.
6. **Rejected folklore** — call out suggestions not supported by the plan, such as predicate-text order, join-text side,
   or reflexive indexing.

## Official references

Use current DuckDB documentation when version-specific behavior matters:

- Performance guide: https://duckdb.org/docs/current/guides/performance/overview
- Profiling and `EXPLAIN ANALYZE`: https://duckdb.org/docs/current/guides/meta/explain_analyze
- Indexes: https://duckdb.org/docs/current/sql/indexes
- Join operations: https://duckdb.org/docs/current/guides/performance/join_operations
- Workload tuning: https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads
- Sorting on insert: https://duckdb.org/2025/05/14/sorting-for-fast-selective-queries
