import re
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import unquote, urlparse

import pytest
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SUBAGENTS_DIR = REPO_ROOT / "subagents"
AGENT_NAME_RE = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
MARKDOWN_LINK_RE = re.compile(r"!?(?<!\\)\[[^\]]+\]\(([^)]+)\)")
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ModelReference = Annotated[
    str, StringConstraints(pattern=r"^[^/#\s]+/[^#\s]+(?:#[^#\s]+)?$")
]


class PermissionRule(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    action: NonEmptyString
    resource: NonEmptyString
    effect: Literal["allow", "ask", "deny"]

    @field_validator("action")
    @classmethod
    def action_must_not_use_legacy_names(cls, value: str) -> str:
        if value in {"bash", "task"}:
            raise ValueError(
                "use V2 actions shell and subagent instead of bash and task"
            )
        return value


class ExpandedModelReference(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    providerID: NonEmptyString
    model: NonEmptyString
    variant: NonEmptyString | None = None


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    headers: dict[NonEmptyString, str] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)


class AgentFrontmatter(BaseModel):
    # Validate documented V2 Markdown fields; the body supplies the system prompt.
    model_config = ConfigDict(extra="forbid", strict=True)

    description: NonEmptyString
    mode: Literal["subagent"]
    permissions: list[PermissionRule]
    model: ModelReference | ExpandedModelReference | None = None
    hidden: bool | None = None
    color: Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")] | None = None
    steps: Annotated[int, Field(gt=0, le=9007199254740991)] | None = None
    disabled: bool | None = None
    request: AgentRequest | None = None

    @field_validator("description")
    @classmethod
    def description_must_be_one_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("description must be a single line")
        return value


def parse_agent_file(path: Path) -> tuple[AgentFrontmatter, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        pytest.fail(f"{path}: agent file must start with YAML frontmatter")

    try:
        end = lines.index("---", 1)
    except ValueError:
        pytest.fail(f"{path}: YAML frontmatter must end with ---")

    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        pytest.fail(f"{path}: invalid YAML frontmatter: {exc}")

    if not isinstance(data, dict):
        pytest.fail(f"{path}: YAML frontmatter must be a mapping")

    try:
        frontmatter = AgentFrontmatter.model_validate(data)
    except ValidationError as exc:
        pytest.fail(f"{path}: invalid frontmatter:\n{exc}")

    return frontmatter, "\n".join(lines[end + 1 :]).strip()


def agent_files() -> list[Path]:
    return sorted(SUBAGENTS_DIR.glob("*.md"))


def iter_relative_markdown_links(path: Path) -> list[str]:
    links: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(path.read_text(encoding="utf-8")):
        target = match.group(1).strip()
        if not target or target.startswith("#"):
            continue
        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc:
            continue
        links.append(unquote(parsed.path))
    return links


def test_subagents_directory_contains_only_agent_files() -> None:
    assert SUBAGENTS_DIR.is_dir(), "subagents/ directory is required"
    assert agent_files(), "subagents/ must contain at least one agent template"

    for path in sorted(SUBAGENTS_DIR.iterdir()):
        assert path.is_file() and path.suffix == ".md", (
            f"{path}: subagents/ should contain Markdown agent files only"
        )
        assert re.fullmatch(AGENT_NAME_RE, path.stem), (
            f"{path}: agent filename must be lowercase and hyphen-separated"
        )


def test_each_agent_has_valid_frontmatter_and_body() -> None:
    for path in agent_files():
        _, body = parse_agent_file(path)
        assert body, f"{path}: Markdown body must not be empty"
        assert body.startswith("# "), f"{path}: body should start with an H1 heading"


def test_agent_markdown_links_resolve_inside_repository() -> None:
    repo_root = REPO_ROOT.resolve()
    for path in agent_files():
        for link in iter_relative_markdown_links(path):
            assert not Path(link).is_absolute(), (
                f"{path}: local links must be relative: {link}"
            )
            resolved = (path.parent / link).resolve()
            assert resolved.is_relative_to(repo_root), (
                f"{path}: link escapes repository: {link}"
            )
            assert resolved.exists(), f"{path}: link target does not exist: {link}"


def validate_subagent_references(
    path: Path, frontmatter: AgentFrontmatter, names: set[str]
) -> None:
    for rule in frontmatter.permissions:
        if rule.action != "subagent" or rule.effect != "allow":
            continue
        if any(char in rule.resource for char in "*?"):
            continue
        assert rule.resource in names, (
            f"{path}: allowed subagent does not exist: {rule.resource}"
        )


def test_agent_delegation_references_exist() -> None:
    names = {path.stem for path in agent_files()}
    for path in agent_files():
        frontmatter, _ = parse_agent_file(path)
        validate_subagent_references(path, frontmatter, names)


@pytest.mark.parametrize(
    ("updates", "error_location"),
    [
        ({"description": " "}, ("description",)),
        ({"description": "First line\nSecond line"}, ("description",)),
        ({"mode": "primary"}, ("mode",)),
        ({"permissions": {"edit": "deny"}}, ("permissions",)),
        ({"permissions": "deny"}, ("permissions",)),
        (
            {"permissions": [{"action": "edit", "resource": "*", "effect": "approve"}]},
            ("permissions", 0, "effect"),
        ),
        (
            {"permissions": [{"action": "edit", "effect": "deny"}]},
            ("permissions", 0, "resource"),
        ),
        (
            {"permissions": [{"action": " ", "resource": "*", "effect": "deny"}]},
            ("permissions", 0, "action"),
        ),
        (
            {"permissions": [{"action": "edit", "resource": " ", "effect": "deny"}]},
            ("permissions", 0, "resource"),
        ),
        (
            {"permissions": [{"action": "task", "resource": "*", "effect": "deny"}]},
            ("permissions", 0, "action"),
        ),
        (
            {"permissions": [{"action": "bash", "resource": "*", "effect": "deny"}]},
            ("permissions", 0, "action"),
        ),
        (
            {
                "permissions": [
                    {"action": "edit", "resource": "*", "effect": "deny", "typo": True}
                ]
            },
            ("permissions", 0, "typo"),
        ),
        ({"steps": True}, ("steps",)),
        ({"color": "not-a-theme-color"}, ("color",)),
        ({"model": "missing-provider"}, ("model",)),
        ({"model": "anthropic/model#"}, ("model",)),
        ({"prompt": "Not a frontmatter field"}, ("prompt",)),
        ({"system": "Put the prompt in the Markdown body"}, ("system",)),
        ({"permission": {"edit": "deny"}}, ("permission",)),
        ({"temperature": 0.1}, ("temperature",)),
        ({"top_p": 0.9}, ("top_p",)),
        ({"disable": True}, ("disable",)),
        ({"tools": {"edit": False}}, ("tools",)),
        ({"maxSteps": 5}, ("maxSteps",)),
        ({"variant": "high"}, ("variant",)),
        ({"options": {}}, ("options",)),
        ({"request": {"headers": {"x-agent": 1}}}, ("request", "headers", "x-agent")),
    ],
)
def test_agent_frontmatter_rejects_invalid_config(
    updates: dict[str, Any], error_location: tuple[str | int, ...]
) -> None:
    data = {
        "description": "Reviews an OpenHound integration.",
        "mode": "subagent",
        "permissions": [{"action": "edit", "resource": "*", "effect": "deny"}],
        **updates,
    }
    with pytest.raises(ValidationError) as exc_info:
        AgentFrontmatter.model_validate(data)
    assert any(
        error["loc"][: len(error_location)] == error_location
        for error in exc_info.value.errors()
    )


def test_subagent_references_handle_wildcards_and_reject_missing_agents() -> None:
    frontmatter = AgentFrontmatter.model_validate(
        {
            "description": "Coordinates bounded OpenHound work.",
            "mode": "subagent",
            "permissions": [
                {"action": "subagent", "resource": "*", "effect": "deny"},
                {"action": "subagent", "resource": "openhound-*", "effect": "allow"},
                {"action": "subagent", "resource": "worker", "effect": "allow"},
                {"action": "edit", "resource": "*", "effect": "deny"},
                {"action": "edit", "resource": "tests/**", "effect": "allow"},
                {"action": "jira_*", "resource": "*", "effect": "allow"},
            ],
        }
    )
    assert [rule.resource for rule in frontmatter.permissions[:3]] == [
        "*",
        "openhound-*",
        "worker",
    ]
    validate_subagent_references(Path("coordinator.md"), frontmatter, {"worker"})
    with pytest.raises(AssertionError, match="allowed subagent does not exist: worker"):
        validate_subagent_references(Path("coordinator.md"), frontmatter, set())


@pytest.mark.parametrize(
    "model",
    [
        "anthropic/claude-sonnet-4-5",
        "anthropic/claude-sonnet-4-5#high",
        {"providerID": "anthropic", "model": "claude-sonnet-4-5", "variant": "high"},
    ],
)
def test_agent_frontmatter_accepts_v2_model_and_request(
    model: str | dict[str, str],
) -> None:
    frontmatter = AgentFrontmatter.model_validate(
        {
            "description": "Reviews changes for correctness and regressions.",
            "mode": "subagent",
            "model": model,
            "permissions": [
                {"action": "edit", "resource": "*", "effect": "deny"},
                {"action": "shell", "resource": "*", "effect": "deny"},
            ],
            "disabled": False,
            "color": "#ff6b6b",
            "steps": 8,
            "request": {
                "headers": {"x-agent": "reviewer"},
                "body": {"temperature": 0.1},
            },
        }
    )
    assert frontmatter.model_dump(exclude_none=True)["model"] == model
    assert frontmatter.request is not None
    assert frontmatter.request.headers == {"x-agent": "reviewer"}
    assert frontmatter.request.body == {"temperature": 0.1}
    assert frontmatter.disabled is False
