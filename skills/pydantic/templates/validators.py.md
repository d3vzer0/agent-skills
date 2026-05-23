---
name: validators-template
description: Pydantic V2 field, model, and Annotated validator examples
---

# Validators Template

Use built-in types and `Field` constraints first. Add validators only when the rule cannot be expressed declaratively.

## Field Validator

```python
from pydantic import BaseModel, field_validator


class Model(BaseModel):
    code: str

    @field_validator('code')
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if '-' not in value:
            raise ValueError('code must contain a dash')
        return value
```

## Cross-Field Model Validator

```python
from typing_extensions import Self

from pydantic import BaseModel, model_validator


class Credentials(BaseModel):
    password: str
    password_repeat: str

    @model_validator(mode='after')
    def passwords_match(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError('passwords do not match')
        return self
```

## ValidationInfo

```python
from pydantic import BaseModel, ValidationInfo, field_validator


class Model(BaseModel):
    country: str
    postal_code: str

    @field_validator('postal_code')
    @classmethod
    def validate_postal_code(cls, value: str, info: ValidationInfo) -> str:
        country = info.data.get('country')
        if country == 'US' and len(value) not in (5, 10):
            raise ValueError('US postal code must be 5 or 10 characters')
        return value
```

## Reusable Annotated Validator

```python
from typing import Annotated

from pydantic import AfterValidator, BaseModel


def must_be_even(value: int) -> int:
    if value % 2:
        raise ValueError('value must be even')
    return value


EvenInt = Annotated[int, AfterValidator(must_be_even)]


class Model(BaseModel):
    count: EvenInt
```

## Checklist

- Return the validated value from every validator.
- Use `mode='after'` unless raw input handling is required.
- Treat `ValidationInfo.data` as order-dependent.
- Use `json_schema_input_type` when a before/plain/wrap validator accepts inputs wider than the annotation.
