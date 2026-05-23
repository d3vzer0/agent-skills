---
name: pydantic
description: Use when designing, implementing, reviewing, or debugging Pydantic models, validators or serializers.
license: MIT
compatibility: opencode
metadata:
  category: python
  language: python
  framework: pydantic
  pydantic_version: "2"
---

# Pydantic

Use this skill for Pydantic V2 data validation work in Python codebases.

## When to Use

- Creating or changing `BaseModel`, `RootModel`, Pydantic dataclass, or settings classes.
- Adding field constraints, aliases, defaults, strictness, validators, serializers, or JSON Schema metadata.
- Validating non-model types with `TypeAdapter`.
- Debugging `ValidationError`, `PydanticUserError`, schema rebuild, forward reference, coercion, or serialization behavior.
- Reviewing or migrating code that still uses Pydantic V1 APIs like `dict()`, `json()`, `parse_obj()`, `@validator`, `@root_validator`, or `Config`.

## Operating Rules

- Treat this skill and its references as the primary offline guide. If more detail is needed and internet access is available, use the public Pydantic documentation at `https://docs.pydantic.dev/latest/`.
- Model data shape with type annotations first, then add `Field`, `Annotated`, validators, or config only where needed.
- Put validation and normalization on the Pydantic model that owns the data. Use field validators for single-field logic and model validators for cross-field invariants.
- Prefer built-in Pydantic features over custom parsing, custom conversion, or hand-written schema logic. Use the source links in each reference only for deeper edge cases.
- Remember that Pydantic validation guarantees the output type and constraints, not that input data was already valid.
- Be explicit about coercion. Pydantic is lax by default; use strict validation when accepting coercion would be unsafe.
- Verify behavior with both valid and invalid examples, including the exact `ValidationError` locations when validation rules matter.

## Workflow

1. Identify the Pydantic version and the task category: model design, field constraints, validators, serialization, settings, TypeAdapter, JSON Schema, or migration.
2. Check the project's existing Pydantic style before adding new patterns.
3. Implement the smallest model or validation change that expresses the data contract.
4. Add or update tests that validate successful parsing, rejected inputs, default handling, aliases, strictness, and serialization where applicable.
5. Run focused tests, and include a quick direct model instantiation check when a dedicated test suite is unavailable.

## Core References

| Topic | Use For | Reference |
| --- | --- | --- |
| Models and validation | `BaseModel`, validation methods, extra data, forward refs, `RootModel` | [models-validation](references/models-validation.md) |
| Fields and aliases | `Field`, defaults, `Annotated`, constraints, aliases | [fields-aliases](references/fields-aliases.md) |
| Field types | Standard library, Pydantic, network, strict, constrained, encoded, and optional extra field types | [field-types](references/field-types.md) |
| Validators | `field_validator`, `model_validator`, validation context, errors | [validators](references/validators.md) |
| Config and strict mode | `ConfigDict`, global config, strict validation | [config-strict-mode](references/config-strict-mode.md) |
| Serialization and JSON Schema | `model_dump`, serializers, schema generation | [serialization-json-schema](references/serialization-json-schema.md) |
| TypeAdapter and settings | Ad-hoc validation, settings management | [type-adapter-settings](references/type-adapter-settings.md) |

## Templates

| Template | Use For |
| --- | --- |
| [model.py.md](templates/model.py.md) | Starting a Pydantic V2 `BaseModel` with config, constraints, validation, and dumps. |
| [validators.py.md](templates/validators.py.md) | Copyable field, model, `ValidationInfo`, and reusable `Annotated` validator patterns. |
| [settings.py.md](templates/settings.py.md) | Starting a `pydantic-settings` configuration model with secret-safe patterns. |

## Scripts

| Script | Use For |
| --- | --- |
| [list_pydantic_fields.py](scripts/list_pydantic_fields.py) | Importing a Pydantic V2 model and printing field annotations, aliases, defaults, and metadata. |

## Quick Patterns

```python
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class User(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: int
    email: Annotated[str, Field(min_length=3)]
    display_name: str = Field(default='Anonymous', validate_default=True)

    @field_validator('email', mode='after')
    @classmethod
    def require_at_sign(cls, value: str) -> str:
        if '@' not in value:
            raise ValueError('email must contain @')
        return value


try:
    user = User.model_validate({'id': '123', 'email': 'a@example.com'})
except ValidationError as exc:
    print(exc.errors())
else:
    print(user.model_dump())
```

```python
from pydantic import TypeAdapter

ids_adapter = TypeAdapter(list[int])
ids = ids_adapter.validate_python(['1', 2, 3])
payload = ids_adapter.dump_json(ids)
```

## Common Review Checks

- Required fields have no defaults; optional-nullable fields use `T | None` and still need `= None` if they are not required.
- Defaults that must be validated use `Field(validate_default=True)` or `ConfigDict(validate_default=True)`.
- Mutable defaults are intentional. Pydantic deep-copies unhashable defaults, but `default_factory` is clearer for generated values.
- Cross-field validators account for field order when using `ValidationInfo.data`.
- Aliases distinguish validation input names from serialization output names when they differ.
