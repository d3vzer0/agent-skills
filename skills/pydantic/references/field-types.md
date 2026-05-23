---
name: field-types
description: Pydantic-supported field types and annotation utilities
---

# Field Types

Sources: [Standard Library Types](https://docs.pydantic.dev/latest/api/standard_library_types/), [Pydantic Types API](https://docs.pydantic.dev/latest/api/types/), [Network Types API](https://docs.pydantic.dev/latest/api/networks/), [pydantic-extra-types docs](https://docs.pydantic.dev/latest/api/pydantic_extra_types_color/).

This reference is intended to be usable without a local copy of the Pydantic documentation.

## Selection Rules

- Prefer normal Python and standard library types first.
- Use `Annotated[T, Field(...)]` or `Annotated[T, ...]` metadata for constraints on type arguments and reusable constrained aliases.
- Prefer `StringConstraints` with `Annotated[str, ...]` over `constr()` for new code.
- Prefer `Field(gt=..., min_length=..., pattern=...)` or `annotated_types` over `con*` factories when static analysis and readability matter.
- Use strict types or `Strict()` only when coercion is unsafe.
- Use `pydantic-extra-types` only when the dependency is already present or the domain-specific type is worth adding.
- Most strict and constrained behavior can be expressed either with specialized Pydantic types or with `Annotated` metadata. Prefer the form that is clearer to the project and type checker.

## Standard Library Field Types

| Category | Field types |
| --- | --- |
| Boolean | `bool` |
| Strings | `str` |
| Bytes | `bytes`, `bytearray` |
| Integers | `int` |
| Floating point | `float` |
| Decimal | `decimal.Decimal` |
| Complex | `complex` |
| Fractions | `fractions.Fraction` |
| Date and time | `datetime.datetime`, `datetime.date`, `datetime.time`, `datetime.timedelta` |
| Enums | `enum.Enum`, `enum.IntEnum`, custom enum subclasses |
| None | `None`, `NoneType`, `Literal[None]` |
| Collections | `list[T]`, `tuple[...]`, `set[T]`, `frozenset[T]`, `collections.deque[T]` |
| Abstract collections | `collections.abc.Sequence[T]`, `Iterable[T]`, `Mapping[K, V]` and related ABCs |
| Dictionaries | `dict[K, V]`, `typing.TypedDict`, `typing_extensions.TypedDict` |
| Named tuples | `typing.NamedTuple`, `collections.namedtuple` |
| Callables | `typing.Callable` |
| IP address types | `ipaddress.IPv4Address`, `IPv6Address`, `IPv4Interface`, `IPv6Interface`, `IPv4Network`, `IPv6Network` |
| UUID | `uuid.UUID` |
| Types/classes | `type`, `type[T]` |
| Literals | `typing.Literal[...]` |
| Any | `typing.Any` |
| Hashable | `typing.Hashable`, `collections.abc.Hashable` |
| Regex patterns | `re.Pattern` |
| Paths | `pathlib.Path`, `PurePath`, `PosixPath`, `WindowsPath` variants |

## Standard Library Type Notes

- Prefer concrete containers like `list[T]` and `dict[K, V]` over abstract containers for performance and predictable output conversion.
- `tuple[T, ...]` validates variable-length tuples; `tuple[A, B]` validates fixed-length positional tuples.
- `TypedDict` is useful for validating structured dictionaries without creating a `BaseModel` class.
- `Literal[...]` is the simplest way to constrain a field to exact values.
- `Any` disables type validation for that field, but validators and serializers can still run.
- `Callable` checks that a value is callable; Pydantic does not validate callable signatures.
- `re.Pattern` accepts compiled regex patterns and may parse valid regex strings.

## Strict Types and Metadata

| Type | Use |
| --- | --- |
| `Strict()` | `Annotated` metadata to require strict validation for a type. |
| `StrictBool` | Strict boolean, no lax coercion. |
| `StrictInt` | Strict integer, no lax coercion. |
| `StrictFloat` | Strict float, no lax coercion. |
| `StrictStr` | Strict string, no lax coercion. |
| `StrictBytes` | Strict bytes, no lax coercion. |

```python
from typing import Annotated

from pydantic import BaseModel, Strict, StrictInt


class Model(BaseModel):
    id: StrictInt
    name: Annotated[str, Strict()]
```

## Numeric Types

| Type or factory | Use |
| --- | --- |
| `PositiveInt` | `int > 0`. |
| `NegativeInt` | `int < 0`. |
| `NonPositiveInt` | `int <= 0`. |
| `NonNegativeInt` | `int >= 0`. |
| `FiniteFloat` | Float excluding `inf`, `-inf`, and `nan`. |
| `PositiveFloat` | `float > 0`. |
| `NegativeFloat` | `float < 0`. |
| `NonPositiveFloat` | `float <= 0`. |
| `NonNegativeFloat` | `float >= 0`. |
| `AllowInfNan` | `Annotated` metadata controlling whether `inf`, `-inf`, and `nan` are allowed. |
| `conint(...)` | Constrained integer factory. |
| `confloat(...)` | Constrained float factory. |
| `condecimal(...)` | Constrained `Decimal` factory. |

## String and Bytes Types

| Type or factory | Use |
| --- | --- |
| `StringConstraints` | `Annotated[str, StringConstraints(...)]` constraints and normalization. |
| `constr(...)` | Constrained string factory. Prefer `StringConstraints` for new code. |
| `conbytes(...)` | Constrained bytes factory. |
| `ImportString` | Import an object from a dotted Python path string. |

```python
from typing import Annotated

from pydantic import BaseModel, StringConstraints


Slug = Annotated[str, StringConstraints(pattern=r'^[a-z0-9-]+$', to_lower=True)]


class Model(BaseModel):
    slug: Slug
```

## Collection Constraint Factories

| Factory | Use |
| --- | --- |
| `conlist(T, ...)` | Constrained list. |
| `conset(T, ...)` | Constrained set. |
| `confrozenset(T, ...)` | Constrained frozenset. |

Prefer `Annotated` on the collection or item type when it is clearer:

```python
from typing import Annotated

from pydantic import Field

Scores = Annotated[list[Annotated[int, Field(ge=0)]], Field(min_length=1)]
```

## Date, Time, and UUID Types

| Type or factory | Use |
| --- | --- |
| `PastDate` | Date before today. |
| `FutureDate` | Date after today. |
| `PastDatetime` | Datetime in the past. |
| `FutureDatetime` | Datetime in the future. |
| `AwareDatetime` | Datetime requiring timezone info. |
| `NaiveDatetime` | Datetime requiring no timezone info. |
| `condate(...)` | Constrained date factory. |
| `UUID1` | UUID version 1. |
| `UUID3` | UUID version 3. |
| `UUID4` | UUID version 4. |
| `UUID5` | UUID version 5. |
| `UUID6` | UUID version 6. |
| `UUID7` | UUID version 7. |
| `UUID8` | UUID version 8. |

## Path Types

| Type | Use |
| --- | --- |
| `FilePath` | Existing file path. |
| `DirectoryPath` | Existing directory path. |
| `NewPath` | Path intended for a new file or directory. |
| `SocketPath` | Existing Unix socket path. |

## Secret and JSON Types

| Type | Use |
| --- | --- |
| `Secret[T]` | Generic secret wrapper. |
| `SecretStr` | Secret string masked in repr and dumps unless explicitly revealed. |
| `SecretBytes` | Secret bytes masked in repr and dumps unless explicitly revealed. |
| `Json[T]` | JSON string that is parsed into `T`. |
| `JsonValue` | Any value representable as JSON: object, array, string, bool, number, or null. |

## Encoded and Base64 Types

| Type | Use |
| --- | --- |
| `EncodedBytes` | `Annotated` metadata for bytes encoded/decoded through an encoder. |
| `EncodedStr` | `Annotated` metadata for strings encoded/decoded through an encoder. |
| `EncoderProtocol` | Protocol for custom encoders used by `EncodedBytes` and `EncodedStr`. |
| `Base64Encoder` | Standard base64 encoder. |
| `Base64Bytes` | Base64-encoded bytes field. |
| `Base64Str` | Base64-encoded string field. |
| `Base64UrlBytes` | URL-safe base64 bytes field. |
| `Base64UrlStr` | URL-safe base64 string field. |

## Payment and Size Types

| Type | Use |
| --- | --- |
| `PaymentCardNumber` | Payment card number validation and brand metadata. Prefer `pydantic-extra-types` in codebases following the V2 package split. |
| `ByteSize` | Human-readable byte sizes such as `10MB`, serialized as bytes/int-like values. |

## URL Type Notes

- Pydantic V2 URL and DSN types do not inherit from `str`. Convert with `str(url)` when passing to APIs requiring strings.
- Use DSN-specific types when the scheme and host rules matter, for example `PostgresDsn` for database configuration.
- Use `UrlConstraints` with `Annotated` for custom allowed schemes, host requirements, or length limits.

## Network and Email Types

| Type | Use |
| --- | --- |
| `AnyUrl` | Generic URL. |
| `AnyHttpUrl` | HTTP or HTTPS URL with broad constraints. |
| `HttpUrl` | HTTP or HTTPS URL with stricter defaults. |
| `FileUrl` | File URL. |
| `FtpUrl` | FTP URL. |
| `AnyWebsocketUrl` | WebSocket URL with broad constraints. |
| `WebsocketUrl` | WebSocket URL with stricter defaults. |
| `UrlConstraints` | `Annotated` metadata for URL constraints. |
| `PostgresDsn` | PostgreSQL DSN. |
| `CockroachDsn` | CockroachDB DSN. |
| `AmqpDsn` | AMQP DSN. |
| `RedisDsn` | Redis DSN. |
| `MongoDsn` | MongoDB DSN. |
| `KafkaDsn` | Kafka DSN. |
| `NatsDsn` | NATS DSN. |
| `MySQLDsn` | MySQL DSN. |
| `MariaDBDsn` | MariaDB DSN. |
| `ClickHouseDsn` | ClickHouse DSN. |
| `SnowflakeDsn` | Snowflake DSN. |
| `EmailStr` | Email address string. Requires the email validation extra/dependency. |
| `NameEmail` | Name plus email address pair. |
| `IPvAnyAddress` | IPv4 or IPv6 address. |
| `IPvAnyInterface` | IPv4 or IPv6 interface. |
| `IPvAnyNetwork` | IPv4 or IPv6 network. |

## Validation and Schema Annotation Utilities

These are not standalone domain types, but they are valid in field annotations and are often used with field types.

| Utility | Use |
| --- | --- |
| `InstanceOf[T]` | Validate that a value is an instance of `T`. |
| `SkipValidation[T]` | Skip validation for a type or nested type part. |
| `ValidateAs(Model, converter)` | Validate a custom type through a Pydantic-supported type. |
| `AfterValidator`, `BeforeValidator`, `PlainValidator`, `WrapValidator` | Attach validator functions with `Annotated`. |
| `PlainSerializer`, `WrapSerializer`, `SerializeAsAny` | Attach serializer behavior with `Annotated`. |
| `WithJsonSchema` | Attach JSON Schema metadata with `Annotated`. |
| `GetPydanticSchema` | Reduce custom schema boilerplate for advanced custom types. |
| `Tag` | Tag union choices for discriminated unions. |
| `Discriminator` | Configure discriminated union selection. |
| `FailFast` | Stop validation on first error for supported containers. |
| `OnErrorOmit` | Omit invalid items instead of failing for supported container item annotations. |

## Optional pydantic-extra-types

The public Pydantic documentation includes API pages for these optional `pydantic-extra-types` modules. Use them when the package is installed or the project accepts the dependency.

| Module | Field types covered |
| --- | --- |
| `pydantic_extra_types.color` | Color values. |
| `pydantic_extra_types.country` | Country codes and country-related values. |
| `pydantic_extra_types.currency_code` | ISO currency codes. |
| `pydantic_extra_types.coordinate` | Latitude, longitude, and coordinate values. |
| `pydantic_extra_types.isbn` | ISBN identifiers. |
| `pydantic_extra_types.language_code` | Language codes. |
| `pydantic_extra_types.mac_address` | MAC addresses. |
| `pydantic_extra_types.payment` | Payment card and payment-related values. |
| `pydantic_extra_types.pendulum_dt` | Pendulum date/time values. |
| `pydantic_extra_types.phone_numbers` | Phone numbers. |
| `pydantic_extra_types.routing_numbers` | Routing numbers. |
| `pydantic_extra_types.script_code` | Script codes. |
| `pydantic_extra_types.semantic_version` | Semantic versions. |
| `pydantic_extra_types.timezone_name` | Time zone names. |
| `pydantic_extra_types.ulid` | ULID identifiers. |
