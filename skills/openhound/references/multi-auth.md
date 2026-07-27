# OpenHound Multi-Auth

Use this reference when a collector supports more than one authentication method.

## Purpose

Multi-auth collectors should model each authentication flow explicitly while keeping the collection pipeline static and maintainable. Use DLT `configspec` credential classes and a single `Union[...] = dlt.secrets.value` source parameter instead of many optional secret parameters on the source function.

## Core Pattern

Define one `@configspec` class per authentication mode:

```python
from typing import Literal, Union

import dlt
from dlt.common.configuration import configspec
from dlt.common.configuration.specs import CredentialsConfiguration


@configspec
class TokenCredentials(CredentialsConfiguration):
    auth: Literal["token"] = "token"
    token: str = None
    api_url: str = "https://api.example.com"


@configspec
class AppCredentials(CredentialsConfiguration):
    auth: Literal["app"] = "app"
    client_id: str = None
    private_key_path: str = None
    installation_id: str = None
    api_url: str = "https://api.example.com"


@app.source(name="example", max_table_nesting=0)
def source(
    credentials: Union[TokenCredentials, AppCredentials] = dlt.secrets.value,
):
    ctx = build_context(credentials)

    return (
        users(ctx),
        groups(ctx),
        memberships(ctx),
    )
```

Keep the source signature narrow. The source should usually accept one `credentials` argument plus non-secret parameters such as collection mode, region, tenant, organization, host, or feature flags.

## Credential Class Rules

- Create one credential class per auth mode.
- Use a discriminator field such as `auth` when the collector branches on credential type or when secrets files need to show the selected auth mode clearly.
- Put only fields required by that auth mode on the auth-specific class.
- Put shared non-secret fields in a shared base `@configspec` class when useful.
- Do not create one generic credential class with many mostly-optional secret fields.
- Do not collect, log, yield, or emit secret values.

Example with shared fields:

```python
@configspec
class ExampleCredentials(CredentialsConfiguration):
    api_url: str = "https://api.example.com"
    tenant: str | None = None


@configspec
class TokenCredentials(ExampleCredentials):
    auth: Literal["token"] = "token"
    token: str = None


@configspec
class ClientCredentials(ExampleCredentials):
    auth: Literal["client"] = "client"
    client_id: str = None
    client_secret: str = None
```

## Runtime Auth Code

Keep protocol-specific auth logic out of resource and transformer functions.

Use `auth.py` or `client.py` for:

- Token refresh.
- Session or client construction.
- Private key or certificate loading.
- OAuth, JWT, app installation, or SDK credential adapters.
- Retry policies and auth-aware HTTP client setup.

Resource functions should use clients from `SourceContext` and should not request or refresh tokens directly.

## Source Branching

Auth mode should select credentials, clients, context, or explicit resource groups. It should not register resources dynamically.

```python
def build_context(credentials: TokenCredentials | AppCredentials) -> SourceContext:
    if credentials.auth == "token":
        return SourceContext(client=token_client(credentials))

    if credentials.auth == "app":
        return SourceContext(client=app_client(credentials))

    raise ValueError(f"Unsupported auth mode: {credentials.auth}")
```

If auth mode or collection mode affects which data can be collected, return explicit resource groups:

```python
@app.source(name="example", max_table_nesting=0)
def source(
    credentials: Union[TokenCredentials, AppCredentials] = dlt.secrets.value,
    collection: Literal["all", "directory", "resources"] = "all",
):
    ctx = build_context(credentials)

    if collection == "directory":
        return directory_resources(ctx)

    if collection == "resources":
        return resource_inventory(ctx)

    return (*directory_resources(ctx), *resource_inventory(ctx))
```

## Static Resource Registration

Resource and transformer registration must remain static and explicit.

- Do not create `@app.resource(...)` or `@app.transformer(...)` registrations dynamically from loops, factories, registries, reflection, closures, or config-driven generation.
- Define every collected table as a separately named resource or transformer function with its own decorator.
- Group already-defined resources with plain helper functions such as `directory_resources(ctx)` only when it improves source readability.
- Helper functions may choose which explicit resources to return, but they must not create new decorated functions.

## DLT Secrets Shape

Document a secrets example for each supported auth mode. Keep examples specific enough that users know which fields are required.

```toml
[sources.source.example.credentials]
auth = "token"
token = "..."
api_url = "https://api.example.com"
```

```toml
[sources.source.example.credentials]
auth = "app"
client_id = "example-client-id"
private_key_path = "/path/to/key.pem"
installation_id = "12345"
api_url = "https://api.example.com"
```

Environment variable examples can be included when useful, but avoid documenting secrets that the collector does not actually read.

## Extension Metadata

`extension.yaml` should describe the supported auth modes and all credential fields. Make clear that only fields for the selected auth mode are required.

If the metadata format cannot express conditional requirements, use descriptions such as:

```yaml
credentials:
  - name: auth
    description: Authentication mode. Supported values are token and app.
    required: true
  - name: token
    description: API token. Required when auth is token.
    required: false
  - name: client_id
    description: App client ID. Required when auth is app.
    required: false
```

Keep metadata names aligned with the `configspec` fields and the DLT secrets examples.

## Checklist

- Each auth mode has a dedicated `@configspec` credential class.
- The source uses one `credentials: Union[...] = dlt.secrets.value` parameter.
- Shared non-secret fields are factored into a shared base class when useful.
- Auth-specific runtime code lives in `auth.py` or `client.py`, not resource functions.
- Resource and transformer decorators are static and explicit.
- Auth or collection mode only selects clients, context, or explicit resource groups.
- DLT secrets examples exist for each auth mode.
- `extension.yaml` documents each auth mode and required fields.
- Secrets are never collected, emitted, logged, or added to graph properties.
- Read `references/source-collection.md` and `references/validate-extension.md` before finishing.
