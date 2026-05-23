---
name: models-validation
description: Pydantic V2 model design and validation methods
---

# Models and Validation

Sources: [Models](https://docs.pydantic.dev/latest/concepts/models/), [BaseModel API](https://docs.pydantic.dev/latest/api/base_model/), [RootModel API](https://docs.pydantic.dev/latest/api/root_model/).

This reference is intended to be usable without a local copy of the Pydantic documentation.

## BaseModel Basics

- Define fields as annotated class attributes on `BaseModel` subclasses.
- Required fields have no default value.
- Defaults make fields optional for input, but the annotation still controls the output type.
- Pydantic may coerce inputs in default lax mode, such as `'123'` to `123` for an `int` field.
- Use `model_dump()` instead of `dict()` for recursive model-to-dict serialization.
- Access fields with normal attributes. Inspect class-level field definitions with `Model.model_fields`.
- `ValidationError` is raised when input cannot be parsed into the declared output type.

```python
from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(str_max_length=50)

    id: int
    name: str = 'Jane Doe'


user = User(id='123')
assert user.id == 123
assert user.model_dump() == {'id': 123, 'name': 'Jane Doe'}
```

## Core BaseModel API

| API | Purpose |
| --- | --- |
| `model_validate(obj, *, strict=None, extra=None, from_attributes=None, context=None, by_alias=None, by_name=None)` | Validate a Python object into a model. |
| `model_validate_json(json_data, *, strict=None, extra=None, context=None, by_alias=None, by_name=None)` | Validate JSON string/bytes into a model. |
| `model_validate_strings(obj, *, strict=None, extra=None, context=None, by_alias=None, by_name=None)` | Validate nested string data using JSON-mode coercion. |
| `model_dump(...)` | Serialize to Python values, usually a dict. |
| `model_dump_json(...)` | Serialize to a JSON string. |
| `model_json_schema(...)` | Generate JSON Schema. |
| `model_copy(update=None, deep=False)` | Copy a model, optionally updating fields. |
| `model_construct(...)` | Construct without validation for trusted data only. |
| `model_rebuild(...)` | Rebuild schema for forward references or generics. |
| `model_post_init(context)` | Hook called after model initialization and validation. |
| `model_fields` | Class mapping of field names to `FieldInfo`. |
| `model_computed_fields` | Class mapping of computed fields. |
| `model_fields_set` | Instance set of fields explicitly provided by input. |
| `model_extra` | Instance extra input fields when `extra='allow'`. |

## Validation Entry Points

- `Model(...)` validates keyword arguments in Python mode.
- `Model.model_validate(obj)` validates dictionaries, model instances, and arbitrary objects when enabled.
- `Model.model_validate_json(data)` validates JSON strings or bytes and is usually faster for JSON payloads than `json.loads()` plus `model_validate()`.
- `Model.model_validate_strings(data)` validates nested string-key/string-value dictionaries using JSON-mode coercion.
- Validation methods can accept runtime options like `strict`, `extra`, and `context`.
- Use `from_attributes=True` in config or validation call to read values from object attributes instead of mapping keys.
- Use `by_alias` and `by_name` to control accepted input names at runtime.

```python
from datetime import datetime

from pydantic import BaseModel, Field


class User(BaseModel):
    id: int
    name: str
    signup_ts: datetime | None = None


User.model_validate({'id': '123', 'name': 'Jane'})
User.model_validate_json('{"id": 123, "name": "Jane"}')
User.model_validate_strings({'id': '123', 'name': 'Jane'})
```

## Error Handling

- Catch `pydantic.ValidationError` around validation boundaries.
- `str(exc)` is human-readable and includes location, message, error type, input value, and input type.
- `exc.errors()` returns structured dictionaries. Common keys include `type`, `loc`, `msg`, `input`, `ctx`, and `url`.
- Test `loc` and `type` when the exact failing field or error kind is contractually important.

```python
from pydantic import BaseModel, ValidationError


class Model(BaseModel):
    count: int


try:
    Model.model_validate({'count': 'bad'})
except ValidationError as exc:
    assert exc.errors()[0]['loc'] == ('count',)
    assert exc.errors()[0]['type'] == 'int_parsing'
```

## Extra Data

- Default behavior ignores extra input keys.
- Use `ConfigDict(extra='forbid')` to reject unknown keys.
- Use `ConfigDict(extra='allow')` to preserve extra keys in `model_extra` and dumps.
- Runtime validation can override model config with `Model.model_validate(data, extra='forbid')`.

```python
from pydantic import BaseModel, ConfigDict


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
```

## Forward References

- Use `model_rebuild()` when annotations refer to symbols that are not ready during class creation.
- `model_rebuild()` replaces V1 `update_forward_refs()`.
- Call it on the outermost model after all nested types are defined.
- Pydantic usually handles forward annotations automatically, but explicit rebuilds are useful after dynamic imports or mutually recursive declarations.

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class Node(BaseModel):
    name: str
    children: list[Node] = Field(default_factory=list)


Node.model_rebuild()
```

## model_construct

- `model_construct()` creates a model without validation.
- It does not convert nested dictionaries to nested model instances.
- Use it only with trusted already-validated data.
- Do not assume it is faster; Pydantic V2 narrowed the performance gap.
- For `extra='forbid'`, `model_construct()` ignores unexpected data instead of raising because no validation runs.

## RootModel

- Use `RootModel[T]` for models whose root value is a non-object type like `list[str]`.
- `RootModel` replaces V1 `__root__` custom root models.
- The root value is stored on the `.root` attribute.

```python
from pydantic import RootModel


class Tags(RootModel[list[str]]):
    pass


tags = Tags.model_validate(['a', 'b'])
assert tags.root == ['a', 'b']
```

## Field Order

- Field order is preserved in JSON Schema, validation errors, and serialization.
- Field order matters when validators or default factories read already validated data.

## Private Attributes

- Leading-underscore attributes are private attributes, not model fields.
- Use `PrivateAttr(default_factory=...)` for explicit private defaults.
- Private attributes are not validated and are not included in schema.

## Immutability and Assignment

- Models are mutable by default.
- Use `ConfigDict(frozen=True)` or `class Model(BaseModel, frozen=True): ...` to prevent field assignment.
- Faux immutability does not make nested mutable objects immutable.
- Use `ConfigDict(validate_assignment=True)` when assignment should be validated.

```python
from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    count: int


model = Model(count=1)
model.count = '2'
assert model.count == 2
```
