---
name: model-template
description: Pydantic V2 BaseModel template with validation and serialization examples
---

# BaseModel Template

Use this as a starting point for a Pydantic V2 model. Replace field names and constraints with the target domain model.

```python
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class ExampleModel(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True,
    )

    id: int
    name: Annotated[str, Field(min_length=1, max_length=100)]
    tags: list[Annotated[str, Field(min_length=1)]] = Field(default_factory=list)
    is_active: bool = True

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str) -> str:
        if not value:
            raise ValueError('name must not be empty')
        return value


def parse_example(data: object) -> ExampleModel:
    return ExampleModel.model_validate(data)


try:
    model = parse_example({'id': '123', 'name': 'Example'})
except ValidationError as exc:
    print(exc.errors())
else:
    print(model.model_dump())
    print(model.model_dump_json())
```

## Checklist

- Use `extra='forbid'` for external API input unless unknown keys are intentionally allowed.
- Use `Field(default_factory=...)` for generated or mutable defaults.
- Use `validate_default=True` for defaults that must be parsed or checked.
- Add invalid-input tests for every custom validator and important constraint.
- Prefer `model_validate_json()` when validating JSON strings or bytes.
