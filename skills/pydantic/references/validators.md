---
name: validators
description: Field and model validators in Pydantic V2
---

# Validators

Sources: [Validators](https://docs.pydantic.dev/latest/concepts/validators/), [Functional Validators API](https://docs.pydantic.dev/latest/api/functional_validators/), [Errors](https://docs.pydantic.dev/latest/errors/errors/).

This reference is intended to be usable without a local copy of the Pydantic documentation.

## General Rules

- Prefer built-in types, `Field` constraints, and `Annotated` before custom validators.
- Validator callables must return the validated value unless they raise an error.
- Raise `ValueError` for most custom validation failures.
- Use `PydanticCustomError` when you need a stable custom error type and context.
- Avoid mutating raw input in `before` validators if you may later raise an error, especially with unions.
- Use decorator validators when a rule belongs to one model or many fields on one model.
- Use `Annotated` validators when a rule should be reusable as part of a type annotation.

## Field Validators

- `mode='after'` runs after Pydantic internal validation and is usually safest.
- `mode='before'` runs on raw input before internal validation.
- `mode='plain'` terminates validation immediately and skips internal validation.
- `mode='wrap'` receives a handler and can run before, after, or around internal validation.
- Decorator validators are class methods and can target one field, many fields, or `'*'`.
- `@field_validator(...)` checks that named fields exist by default; set `check_fields=False` for base-class validators targeting subclass fields.
- Use `mode='before'` with `Any` input typing because raw input can be any object.

```python
from pydantic import BaseModel, field_validator


class Model(BaseModel):
    number: int

    @field_validator('number')
    @classmethod
    def is_even(cls, value: int) -> int:
        if value % 2:
            raise ValueError('number must be even')
        return value
```

## Annotated Validators

- Use `AfterValidator`, `BeforeValidator`, `PlainValidator`, and `WrapValidator` for reusable validation attached to a type.
- For `Annotated`, `before` and `wrap` validators run from right to left, then `after` validators run from left to right.
- Decorator validators are converted to annotated metadata and added last.

```python
from typing import Annotated

from pydantic import AfterValidator, BaseModel


def is_even(value: int) -> int:
    if value % 2:
        raise ValueError('number must be even')
    return value


EvenInt = Annotated[int, AfterValidator(is_even)]


class Model(BaseModel):
    number: EvenInt
```

## Model Validators

- Use model validators for cross-field invariants or whole-input checks.
- `mode='after'` is an instance method and must return `self`.
- `mode='before'` is usually a class method and receives raw input as `Any`.
- `mode='wrap'` receives a handler and can intercept validation success or failure.
- `before` model validators receive raw input and should defensively handle non-dict inputs when `from_attributes=True` or custom inputs are possible.
- Model validators defined on a base class run for subclasses; overriding the validator in a subclass replaces the base implementation.

```python
from typing_extensions import Self

from pydantic import BaseModel, model_validator


class User(BaseModel):
    password: str
    password_repeat: str

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError('passwords do not match')
        return self
```

## ValidationInfo

- Add a `ValidationInfo` parameter to access already validated data, context, validation mode, and field name.
- `info.data` is available for field validators and is `None` for model validators.
- `info.data` only contains fields that have already been validated based on field order.
- Pass context through `model_validate(..., context={...})` or `TypeAdapter.validate_python(..., context={...})`.
- `info.mode` is `'python'`, `'json'`, or `'strings'`.
- `info.field_name` is populated for field validators.

```python
from pydantic import BaseModel, ValidationInfo, field_validator


class User(BaseModel):
    password: str
    password_repeat: str

    @field_validator('password_repeat')
    @classmethod
    def passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if value != info.data['password']:
            raise ValueError('passwords do not match')
        return value
```

## JSON Schema Input Types

- `before`, `plain`, and `wrap` validators may accept inputs different from the field annotation.
- Use `json_schema_input_type` when JSON Schema should advertise the wider accepted input type.

```python
from typing import Any

from pydantic import BaseModel, field_validator


class Model(BaseModel):
    value: str

    @field_validator('value', mode='before', json_schema_input_type=int | str)
    @classmethod
    def cast_ints(cls, value: Any) -> Any:
        return str(value) if isinstance(value, int) else value
```

## Special Validation Utilities

- `InstanceOf[T]` validates that a value is an instance of `T`.
- `SkipValidation[T]` skips validation for a field or nested type part.
- `ValidateAs(Model, converter)` validates a custom type through a supported Pydantic model.
- `PydanticUseDefault` tells Pydantic to use the field default from a validator.

## Validator Mode Cheat Sheet

| Validator | Runs | Input type | Must call handler? | Typical use |
| --- | --- | --- | --- | --- |
| Field `after` | After internal field validation | Annotated field type | No handler | Type-safe checks and normalization. |
| Field `before` | Before internal field validation | `Any` raw input | No handler | Accept alternate input shapes before Pydantic parses. |
| Field `plain` | Instead of internal field validation | `Any` raw input | No handler | Fully custom validation. Use sparingly. |
| Field `wrap` | Around internal field validation | `Any` raw input | Usually | Catch errors, retry/truncate, or conditionally bypass validation. |
| Model `after` | After whole model validation | `self` | No handler | Cross-field invariant checks. |
| Model `before` | Before model validation | `Any` raw input | No handler | Reject or reshape whole input objects. |
| Model `wrap` | Around model validation | `Any` raw input | Usually | Logging, instrumentation, fallback, or error interception. |

## Custom Error Types

```python
from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError


class Model(BaseModel):
    answer: int

    @field_validator('answer')
    @classmethod
    def validate_answer(cls, value: int) -> int:
        if value % 42 == 0:
            raise PydanticCustomError(
                'the_answer_error',
                '{number} is the answer',
                {'number': value},
            )
        return value
```

## Validation Context

```python
from pydantic import BaseModel, ValidationInfo, field_validator


class Model(BaseModel):
    text: str

    @field_validator('text')
    @classmethod
    def remove_stopwords(cls, value: str, info: ValidationInfo) -> str:
        if isinstance(info.context, dict):
            stopwords = set(info.context.get('stopwords', ()))
            return ' '.join(word for word in value.split() if word.lower() not in stopwords)
        return value


Model.model_validate({'text': 'This is an example'}, context={'stopwords': ['this', 'is']})
```
