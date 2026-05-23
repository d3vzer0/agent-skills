---
name: config-strict-mode
description: ConfigDict and strict validation patterns in Pydantic V2
---

# Config and Strict Mode

Sources: [Configuration](https://docs.pydantic.dev/latest/concepts/config/), [ConfigDict API](https://docs.pydantic.dev/latest/api/config/), [Strict Mode](https://docs.pydantic.dev/latest/concepts/strict_mode/).

This reference is intended to be usable without a local copy of the Pydantic documentation.

## ConfigDict

- Configure models with a `model_config = ConfigDict(...)` class attribute.
- A plain dict also works, but `ConfigDict` is clearer and typed.
- V1 inner `Config` classes are deprecated.
- Some config options can also be passed as class arguments, such as `class Model(BaseModel, frozen=True): ...`.

```python
from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    name: str
```

## Inheritance and Boundaries

- Model config is inherited by subclasses.
- Subclass config is merged with parent config.
- Pydantic models and Pydantic dataclasses are configuration boundaries, so parent model config is not propagated into nested Pydantic models.
- Standard library dataclasses and `TypedDict` may receive propagated config unless they define their own.

## Common Config Options

- `extra='ignore'`, `extra='forbid'`, or `extra='allow'` controls unknown input keys.
- `strict=True` enables strict validation by default for the model.
- `validate_assignment=True` validates assignment after model creation.
- `validate_default=True` validates default values.
- `from_attributes=True` validates from object attributes, replacing V1 `orm_mode`.
- `frozen=True` prevents model field assignment, replacing V1 `allow_mutation=False`.
- `validate_by_alias` and `validate_by_name` control input names.
- `serialize_by_alias` controls alias use during serialization.
- `str_to_lower`, `str_to_upper`, and `str_strip_whitespace` normalize string fields.
- `str_min_length` and `str_max_length` apply model-wide string length constraints.
- `coerce_numbers_to_str=True` allows numbers to validate as strings in lax mode.
- `arbitrary_types_allowed=True` allows arbitrary user-defined classes as field types with instance checks.
- `revalidate_instances` controls whether model/dataclass instances are revalidated when nested.
- `ignored_types` allows unannotated class attributes of specific descriptor-like types.
- `json_schema_extra` adds model-level JSON Schema metadata.
- `defer_build=True` defers schema construction until first validation/serialization.

| Config | Typical value | Effect |
| --- | --- | --- |
| `extra` | `'ignore'`, `'forbid'`, `'allow'` | Unknown input fields. |
| `strict` | `True` or `False` | Default strictness. |
| `validate_assignment` | `True` | Validate attribute assignment. |
| `validate_default` | `True` | Validate field defaults. |
| `from_attributes` | `True` | Read object attributes for model validation. |
| `frozen` | `True` | Prevent field assignment. |
| `populate_by_name` | `True` | Legacy-ish shortcut for allowing field-name population. Prefer explicit `validate_by_name` in newer V2 code. |
| `validate_by_alias` | `True` or `False` | Accept aliases during validation. |
| `validate_by_name` | `True` or `False` | Accept field names during validation. |
| `serialize_by_alias` | `True` or `False` | Emit aliases by default during serialization. |

## Strict Mode

- Pydantic is lax by default and coerces values when possible.
- Strict mode rejects many coercions and requires actual instances of the annotated type in Python mode.
- JSON mode can still be looser for some types, such as dates represented as JSON strings.
- Use strictness when coercion would hide invalid or unsafe input.
- Strict mode can be enabled per validation call, per field, per type annotation, or model-wide.
- Strict behavior may differ between Python and JSON input. JSON has no native date or UUID objects, so some string inputs remain valid in JSON strict mode.

## Enable Strictness Per Call

```python
from pydantic import BaseModel, ValidationError


class Model(BaseModel):
    x: int


Model.model_validate({'x': '123'})

try:
    Model.model_validate({'x': '123'}, strict=True)
except ValidationError:
    pass
```

## Enable Strictness Per Field

```python
from pydantic import BaseModel, Field


class User(BaseModel):
    name: str
    age: int = Field(strict=True)
```

## Enable Strictness with Annotated or Strict Types

```python
from typing import Annotated

from pydantic import BaseModel, Strict, StrictInt


class User(BaseModel):
    id: Annotated[int, Strict()]
    age: StrictInt
```

## Enable Strictness Per Model

```python
from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    age: int = Field(strict=False)
```

## Dataclasses and TypedDict

- Use `@pydantic.dataclasses.dataclass(config=ConfigDict(...))` for Pydantic dataclass config.
- Use `__pydantic_config__ = ConfigDict(...)` on stdlib dataclasses.
- Use `@with_config(ConfigDict(...))` for `TypedDict` config.

```python
from typing_extensions import TypedDict

from pydantic import ConfigDict, with_config


@with_config(ConfigDict(str_to_lower=True))
class Payload(TypedDict):
    name: str
```

## TypeAdapter Config

- Pass `config=ConfigDict(...)` to `TypeAdapter` for types that do not already own config.
- Config cannot be provided when the wrapped type directly supports its own config.

## Config Migration Notes

- V1 `Config` inner classes still work but are deprecated.
- Prefer `model_config = ConfigDict(...)` in new code.
- `orm_mode=True` becomes `from_attributes=True`.
- `allow_mutation=False` becomes `frozen=True`.
- `schema_extra` becomes `json_schema_extra`.
- `validate_all` becomes `validate_default`.
