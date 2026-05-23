---
name: type-adapter-settings
description: TypeAdapter and pydantic-settings usage
---

# TypeAdapter and Settings

Sources: [TypeAdapter](https://docs.pydantic.dev/latest/concepts/type_adapter/), [TypeAdapter API](https://docs.pydantic.dev/latest/api/type_adapter/), [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), [pydantic-settings API](https://docs.pydantic.dev/latest/api/pydantic_settings/).

This reference is intended to be usable without a local copy of the Pydantic documentation.

## TypeAdapter Purpose

- Use `TypeAdapter` to validate, serialize, and generate JSON Schema for types that are not `BaseModel` subclasses.
- Good fits include `list[Model]`, primitives, standard dataclasses, `TypedDict`, unions, and reusable constrained types.
- Do not use `TypeAdapter` as a field annotation inside a model.

```python
from typing_extensions import TypedDict

from pydantic import TypeAdapter


class User(TypedDict):
    name: str
    id: int


adapter = TypeAdapter(list[User])
users = adapter.validate_python([{'name': 'Fred', 'id': '3'}])
payload = adapter.dump_json(users)
```

## TypeAdapter Validation

- `validate_python()` validates Python objects.
- `validate_json()` validates JSON strings or bytes.
- `validate_strings()` validates string-key/string-value data for supported types.
- `dump_python()` serializes to Python values.
- `dump_json()` returns `bytes`, unlike `BaseModel.model_dump_json()` which returns `str`.
- `json_schema()` returns JSON Schema for the wrapped type.
- Validation methods accept options such as `strict`, `extra`, `context`, `by_alias`, and `by_name` where applicable.
- Dump methods accept options similar to model dumping, such as `mode`, `include`, `exclude`, `by_alias`, `exclude_none`, `round_trip`, and `context`.

## Performance

- Creating a `TypeAdapter` builds a pydantic-core schema and has non-trivial overhead.
- Create adapters once and reuse them in loops or hot paths.

```python
from pydantic import TypeAdapter


INT_LIST_ADAPTER = TypeAdapter(list[int])


def parse_ids(value: object) -> list[int]:
    return INT_LIST_ADAPTER.validate_python(value)
```

## Config with TypeAdapter

- Pass `config=ConfigDict(...)` when the wrapped type does not own config.
- Do not pass config when wrapping a type that already supports config directly.

```python
from pydantic import ConfigDict, TypeAdapter


adapter = TypeAdapter(list[str], config=ConfigDict(coerce_numbers_to_str=True))
```

## Rebuilding TypeAdapter Schema

- Use `defer_build=True` when schema construction should be delayed.
- Use `adapter.rebuild()` after forward references become available.

```python
from pydantic import ConfigDict, TypeAdapter


adapter = TypeAdapter('MyType', config=ConfigDict(defer_build=True))
MyType = int
adapter.rebuild()
assert adapter.validate_python('1') == 1
```

## Settings Management

- Pydantic settings support lives in the separate `pydantic-settings` package.
- Import `BaseSettings` from `pydantic_settings`, not from `pydantic`.
- Use settings classes for environment variables, secrets files, and application configuration.
- Prefer `SettingsConfigDict` for settings-specific config.
- Settings are regular Pydantic models after values are loaded, so fields, validators, aliases, constraints, secrets, and serialization rules all apply.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='APP_')

    database_url: str
    debug: bool = False
```

## Common SettingsConfigDict Options

| Option | Use |
| --- | --- |
| `env_prefix='APP_'` | Prefix environment variable names. |
| `env_file='.env'` | Load dotenv file values. |
| `env_file_encoding='utf-8'` | Dotenv file encoding. |
| `case_sensitive=True` | Make environment variable lookup case-sensitive. |
| `env_nested_delimiter='__'` | Populate nested models from variables like `APP_DB__HOST`. |
| `secrets_dir='/run/secrets'` | Load values from files in a secrets directory. |
| `extra='ignore'` | Ignore extra dotenv values not modeled by settings. |

## Environment Names

- By default, a field like `database_url` uses `DATABASE_URL`, plus any configured prefix.
- `Field(alias=...)` changes both validation and serialization alias behavior.
- For environment-only naming, prefer settings-specific alias features when used by the project, or document the alias behavior clearly.
- Secrets should use `SecretStr` or `SecretBytes` when string representation may be logged.

## Settings Review Checks

- Do not commit secrets or generated local environment files.
- Keep parsing and type conversion on the settings model rather than command handlers.
- Use field aliases or environment settings intentionally when environment variable names differ from Python field names.
- Add tests that set environment variables explicitly and isolate process environment state.
- Check precedence when multiple sources are configured. Constructor keyword arguments generally override environment and dotenv values.
