---
name: settings-template
description: pydantic-settings template for environment-driven configuration
---

# Settings Template

Use `pydantic-settings` for application settings loaded from environment variables or secrets files.

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='APP_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    database_url: str
    api_key: SecretStr
    debug: bool = False
    request_timeout_seconds: float = Field(default=10.0, gt=0)


settings = Settings()
```

## Test Pattern

```python
from pytest import MonkeyPatch


def test_settings_from_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('APP_DATABASE_URL', 'postgresql://localhost/app')
    monkeypatch.setenv('APP_API_KEY', 'secret')

    settings = Settings()

    assert settings.database_url == 'postgresql://localhost/app'
    assert settings.api_key.get_secret_value() == 'secret'
```

## Checklist

- Import `BaseSettings` from `pydantic_settings`, not `pydantic`.
- Use `SecretStr` or `SecretBytes` for sensitive values.
- Keep `.env` files out of published repositories.
- Use test environment isolation with `monkeypatch` or equivalent.
- Avoid printing `model_dump()` for settings containing secrets unless output is intentionally masked.
