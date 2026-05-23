---
name: fields-aliases
description: Field customization, defaults, constraints, Annotated, and aliases in Pydantic V2
---

# Fields and Aliases

Sources: [Fields](https://docs.pydantic.dev/latest/concepts/fields/), [Aliases](https://docs.pydantic.dev/latest/concepts/alias/), [Field API](https://docs.pydantic.dev/latest/api/fields/), [Aliases API](https://docs.pydantic.dev/latest/api/aliases/).

This reference is intended to be usable without a local copy of the Pydantic documentation.

## Field Basics

- Use `Field()` to add constraints, defaults, aliases, immutability, deprecation, and JSON Schema metadata.
- `name: str = Field(frozen=True)` is still required because no default was provided.
- Avoid `Field(...)` unless the project already uses it; static type checkers handle normal required annotations better.
- Use normal assignment syntax for defaults that static type checkers should understand.

```python
from pydantic import BaseModel, Field


class User(BaseModel):
    name: str
    age: int = Field(default=20, ge=0)
```

## Annotated Pattern

- Use `Annotated[T, Field(...)]` for reusable constrained types and constraints on nested type parts.
- Use assignment form for `default`, `default_factory`, and `alias` when static type checker constructor support matters.
- Put metadata on the top-level field type when it applies to the field, not only one union branch.
- Use `Annotated` for element constraints, reusable constrained aliases, validators, serializers, and JSON Schema metadata.

```python
from typing import Annotated

from pydantic import BaseModel, Field

PositiveInt = Annotated[int, Field(gt=0)]


class Model(BaseModel):
    count: PositiveInt
    scores: list[Annotated[int, Field(ge=0)]]
```

## Defaults

- A field is not required if it has a default value or `default_factory`.
- `Optional[T]` or `T | None` does not imply a default of `None` in Pydantic V2.
- Use `Field(default_factory=...)` for generated defaults.
- A default factory may accept one `data` argument containing already validated previous fields.
- Field order matters for default factories that use `data`.
- In Pydantic V2, `Any` and `Optional[T]` have no implicit `None` default.

```python
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    email: EmailStr
    username: str = Field(default_factory=lambda data: data['email'])
```

## Validate Defaults

- Defaults are not validated by default.
- Use `Field(validate_default=True)` for a field or `ConfigDict(validate_default=True)` for a model.

```python
from pydantic import BaseModel, Field


class Model(BaseModel):
    age: int = Field(default='12', validate_default=True)
```

## Mutable Defaults

- Pydantic deep-copies unhashable mutable defaults for each instance.
- Prefer `default_factory` when it makes generated state clearer.

## Common Field Parameters

| Parameter | Use |
| --- | --- |
| `default` | Explicit default value. |
| `default_factory` | Callable default, optionally accepting already validated data. |
| `alias` | Input and output alias unless overridden by directional aliases. |
| `validation_alias` | Input-only alias, string, `AliasPath`, or `AliasChoices`. |
| `serialization_alias` | Output-only alias. |
| `title`, `description`, `examples` | JSON Schema metadata. |
| `json_schema_extra` | Extra JSON Schema properties as a dict or callable. |
| `exclude` | Exclude field during serialization. |
| `frozen` | Prevent assignment to this field. |
| `validate_default` | Validate the default value. |
| `deprecated` | Mark field as deprecated in JSON Schema and emit warnings on access. |
| `discriminator` | Discriminator for tagged unions. |
| `strict` | Enable strict validation for the field when supported. |
| `gt`, `ge`, `lt`, `le`, `multiple_of` | Numeric constraints. |
| `min_length`, `max_length` | String, bytes, and collection length constraints. |
| `pattern` | Regex pattern for strings. |
| `union_mode` | Union validation strategy, commonly `'smart'` or `'left_to_right'`. |
| `fail_fast` | Stop validation after the first error for supported containers. |

## Required, Optional, and Nullable

| Annotation/default | Required? | Allows `None`? |
| --- | --- | --- |
| `x: str` | Yes | No |
| `x: str = 'abc'` | No | No |
| `x: str | None` | Yes | Yes |
| `x: str | None = None` | No | Yes |
| `x: Any` | Yes | Yes, because `Any` accepts any value |
| `x: Any = None` | No | Yes |

## Aliases

- `alias` applies to both validation and serialization.
- `validation_alias` applies only to input validation.
- `serialization_alias` applies only to output serialization.
- `model_dump(by_alias=True)` is required to serialize using aliases unless model config changes the default.
- If both `alias` and `validation_alias` are set, `validation_alias` wins for input.
- If both `alias` and `serialization_alias` are set, `serialization_alias` wins for output.

```python
from pydantic import BaseModel, Field


class User(BaseModel):
    name: str = Field(validation_alias='username', serialization_alias='displayName')


user = User.model_validate({'username': 'jdoe'})
assert user.model_dump(by_alias=True) == {'displayName': 'jdoe'}
```

## AliasPath and AliasChoices

- Use `AliasPath` to read nested input paths.
- Use `AliasChoices` to accept multiple input names.

```python
from pydantic import AliasChoices, AliasPath, BaseModel, Field


class User(BaseModel):
    first_name: str = Field(validation_alias=AliasChoices('first_name', AliasPath('names', 0)))
```

## Alias Generators

- Use `ConfigDict(alias_generator=...)` for consistent naming conventions.
- Built-in generators include `to_camel`, `to_pascal`, and `to_snake`.
- Use `AliasGenerator` when validation and serialization naming conventions differ.
- Explicit field aliases take precedence by default.
- Use `alias_priority=1` to allow a generated alias to override a field alias; use `alias_priority=2` to force the field alias to win.

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Item(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    item_id: int
```

## Alias Configuration

- Validation uses aliases by default: `ConfigDict(validate_by_alias=True)`.
- Validation by field name is off by default: `ConfigDict(validate_by_name=False)`.
- To allow both names and aliases for input, use `ConfigDict(validate_by_alias=True, validate_by_name=True)`.
- Serialization by alias is off by default unless `by_alias=True` is passed or `ConfigDict(serialize_by_alias=True)` is set.

```python
from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    my_field: str = Field(alias='myAlias')


Model.model_validate({'myAlias': 'x'})
Model.model_validate({'my_field': 'x'})
```
