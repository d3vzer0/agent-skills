---
name: serialization-json-schema
description: Serialization and JSON Schema generation in Pydantic V2
---

# Serialization and JSON Schema

Sources: [Serialization](https://docs.pydantic.dev/latest/concepts/serialization/), [JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/), [Functional Serializers API](https://docs.pydantic.dev/latest/api/functional_serializers/), [JSON Schema API](https://docs.pydantic.dev/latest/api/json_schema/).

This reference is intended to be usable without a local copy of the Pydantic documentation.

## Serialization Modes

- Python mode may produce Python objects that are not JSON serializable.
- JSON mode converts values to JSON-compatible types where possible.
- `model_dump()` returns a Python object, usually a dict for models.
- `model_dump(mode='json')` returns JSON-compatible Python data.
- `model_dump_json()` returns a JSON string.
- `TypeAdapter.dump_python()` and `TypeAdapter.dump_json()` provide equivalent behavior for non-model types.
- Iterating over a model or calling `dict(model)` does not recursively convert nested models; use `model_dump()` for recursive conversion.
- If a value cannot be serialized to JSON, Pydantic raises `PydanticSerializationError`.

```python
from datetime import datetime

from pydantic import BaseModel


class Event(BaseModel):
    at: datetime
    tags: tuple[str, ...]


event = Event(at='2032-06-01T12:13:14', tags=('a', 'b'))
event.model_dump()
event.model_dump(mode='json')
event.model_dump_json()
```

## Include, Exclude, and Aliases

- Use `include` and `exclude` to control fields at serialization time.
- Use `exclude_unset`, `exclude_defaults`, and `exclude_none` for common filtering modes.
- Use `by_alias=True` to emit serialization aliases.
- Field order is preserved in serialized output.
- `include` and `exclude` can be sets or nested dictionaries.
- `exclude_unset=True` omits fields not explicitly set during validation.
- `exclude_defaults=True` omits fields equal to their default value.
- `exclude_none=True` omits fields whose value is `None`.
- `round_trip=True` asks Pydantic to emit values suitable for validating back into non-idempotent types such as `Json[T]`.
- `warnings` controls serialization warnings: `True`/`'warn'`, `False`/`'none'`, or `'error'`.
- `fallback` can provide a function for otherwise unknown values.

```python
model.model_dump(include={'id', 'name'}, exclude_none=True, by_alias=True)
```

## Field Serializers

- Use `@field_serializer` or `PlainSerializer` and `WrapSerializer` for custom field output.
- Plain serializers bypass Pydantic serialization for the field.
- Wrap serializers receive a handler and can call Pydantic serialization before modifying the result.
- Only one serializer can be defined per field.
- Serializer functions can specify `return_type=...` or a return annotation so Pydantic can validate/serialize the serializer output.
- Decorator serializers can target multiple fields or `'*'`.

```python
from pydantic import BaseModel, field_serializer


class Model(BaseModel):
    name: str

    @field_serializer('name')
    def serialize_name(self, value: str) -> str:
        return value.upper()
```

## Model Serializers

- Use `@model_serializer` when the whole model's output shape needs customization.
- Plain model serializers may return values that are not dictionaries.
- Wrap model serializers receive a handler for the default serialized model.
- Use model serializers sparingly because they can replace the whole output shape and may surprise API consumers.

```python
from pydantic import BaseModel, model_serializer


class User(BaseModel):
    username: str

    @model_serializer(mode='plain')
    def serialize_model(self) -> str:
        return self.username
```

## Serialization Context

- Serialization functions can accept an `info` parameter.
- Pass context through `model_dump(context={...})` or `model_dump_json(context={...})`.
- Read context from `info.context`.
- `info.mode` is `'python'` or `'json'`.
- Serialization info also exposes runtime options like `exclude_unset` and `serialize_as_any`.

## Subclass Serialization

- Pydantic V2 serializes nested model-like subclasses according to the annotated field type by default.
- This prevents accidentally leaking fields from subclass instances.
- Use `SerializeAsAny` or runtime `serialize_as_any=True` only when duck-typed subclass serialization is intentional.

## JSON Schema Generation

- Use `Model.model_json_schema()` for model schema.
- Use `TypeAdapter(T).json_schema()` for arbitrary types.
- Pydantic generates schema from the same type annotations, fields, config, and validators used for validation.
- Use `mode='validation'` or `mode='serialization'` when schema differs by direction.
- Input and output schemas can differ when aliases, computed fields, validators, or serializers change accepted or emitted shapes.
- Field order in the schema follows model field order.

```python
from pydantic import BaseModel, Field


class User(BaseModel):
    name: str = Field(description='Display name')


schema = User.model_json_schema()
```

## JSON Schema Methods and Arguments

| API | Use |
| --- | --- |
| `Model.model_json_schema(by_alias=True, ref_template='#/$defs/{model}', mode='validation')` | Generate model JSON Schema. |
| `TypeAdapter(T).json_schema(...)` | Generate schema for arbitrary supported types. |
| `models_json_schema([(Model, 'validation'), ...])` | Generate combined schemas for multiple models. |

Common arguments:

- `by_alias=True` uses aliases in schema property names.
- `ref_template` controls `$ref` values.
- `mode='validation'` describes accepted input.
- `mode='serialization'` describes emitted output.

## JSON Schema Customization

- Use `Field(title=..., description=..., examples=...)` for field-level metadata.
- Use `json_schema_extra={...}` on `Field` or `ConfigDict` for extra schema data.
- Use `WithJsonSchema` with `Annotated` for reusable schema metadata.
- Use `json_schema_input_type` on validators that accept inputs wider than the field annotation.
- Avoid custom core schema hooks unless normal Pydantic metadata cannot express the requirement.

```python
from typing import Annotated

from pydantic import BaseModel, Field, WithJsonSchema


ExternalId = Annotated[
    str,
    Field(pattern=r'^[A-Z0-9]+$'),
    WithJsonSchema({'type': 'string', 'examples': ['ABC123']}),
]


class Model(BaseModel):
    external_id: ExternalId
```

## Computed Fields

- Use `@computed_field` to include a property or cached property in serialization and JSON Schema.
- Computed fields are output values, not input fields.

```python
from pydantic import BaseModel, computed_field


class Rectangle(BaseModel):
    width: float
    height: float

    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height
```
