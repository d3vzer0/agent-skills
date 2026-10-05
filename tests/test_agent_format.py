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
FLAT_PERMISSION_KEYS = {
    "todowrite",
    "question",
    "webfetch",
    "websearch",
    "doom_loop",
}

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AgentName = Annotated[str, StringConstraints(pattern=AGENT_NAME_RE)]
PermissionAction = Literal["allow", "ask", "deny"]
PermissionRule = PermissionAction | dict[NonEmptyString, PermissionAction]
Permissions = PermissionAction | dict[NonEmptyString, PermissionRule]


class AgentFrontmatter(BaseModel):
    # This collection deliberately rejects unknown provider options at top level.
    # Provider-specific settings belong in options to make typos detectable.
    model_config = ConfigDict(extra="forbid", strict=True)

    description: NonEmptyString
    mode: Literal["subagent"]
    permission: Permissions
    name: AgentName | None = None
    model: Annotated[str, StringConstraints(pattern=r"^[^/\s]+/\S+$")] | None = None
    variant: NonEmptyString | None = None
    hidden: bool | None = None
    color: (
        Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
        | Literal[
            "primary", "secondary", "accent", "success", "warning", "error", "info"
        ]
        | None
    ) = None
    steps: Annotated[int, Field(gt=0, le=9007199254740991)] | None = None
    options: dict[str, Any] | None = None
    disable: bool | None = None
    temperature: float | None = None
    top_p: float | None = None

    @field_validator("description")
    @classmethod
    def description_must_be_one_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("description must be a single line")
        return value

    @field_validator("permission")
    @classmethod
    def permission_rules_must_match_tool_shape(cls, value: Permissions) -> Permissions:
        # OpenCode permits custom tool keys with PermissionRuleConfig.
        if isinstance(value, dict):
            for tool, rule in value.items():
                if tool in FLAT_PERMISSION_KEYS and isinstance(rule, dict):
                    raise ValueError(f"{tool} only accepts a flat permission action")
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
        frontmatter, body = parse_agent_file(path)
        if frontmatter.name is not None:
            assert frontmatter.name == path.stem, (
                f"{path}: frontmatter name must match filename stem"
            )
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


def validate_task_references(
    path: Path, frontmatter: AgentFrontmatter, names: set[str]
) -> None:
    if not isinstance(frontmatter.permission, dict):
        return
    rules = frontmatter.permission.get("task")
    if not isinstance(rules, dict):
        return
    for name, action in rules.items():
        if action != "allow" or any(char in name for char in "*?"):
            continue
        assert name in names, f"{path}: allowed task agent does not exist: {name}"


def test_agent_delegation_references_exist() -> None:
    names = {path.stem for path in agent_files()}
    for path in agent_files():
        frontmatter, _ = parse_agent_file(path)
        validate_task_references(path, frontmatter, names)


@pytest.mark.parametrize(
    ("updates", "error_location"),
    [
        ({"description": " "}, ("description",)),
        ({"description": "First line\nSecond line"}, ("description",)),
        ({"mode": "primary"}, ("mode",)),
        ({"permission": {"edit": "approve"}}, ("permission",)),
        ({"permission": {"question": {"*": "allow"}}}, ("permission",)),
        ({"permission": {"task": {" ": "allow"}}}, ("permission",)),
        ({"steps": True}, ("steps",)),
        ({"color": "not-a-theme-color"}, ("color",)),
        ({"model": "missing-provider"}, ("model",)),
        ({"prompt": "Not a frontmatter field"}, ("prompt",)),
    ],
)
def test_agent_frontmatter_rejects_invalid_config(
    updates: dict[str, Any], error_location: tuple[str, ...]
) -> None:
    data = {
        "description": "Reviews an OpenHound integration.",
        "mode": "subagent",
        "permission": {"edit": "deny"},
        **updates,
    }
    with pytest.raises(ValidationError) as exc_info:
        AgentFrontmatter.model_validate(data)
    assert any(
        error["loc"][: len(error_location)] == error_location
        for error in exc_info.value.errors()
    )


def test_task_references_handle_wildcards_and_reject_missing_agents() -> None:
    frontmatter = AgentFrontmatter.model_validate(
        {
            "description": "Coordinates bounded OpenHound work.",
            "mode": "subagent",
            "permission": {
                "task": {"*": "deny", "openhound-*": "allow", "worker": "allow"},
                "edit": {"*": "deny", "tests/**": "allow"},
                "jira_*": "allow",
            },
        }
    )
    validate_task_references(Path("coordinator.md"), frontmatter, {"worker"})
    with pytest.raises(
        AssertionError, match="allowed task agent does not exist: worker"
    ):
        validate_task_references(Path("coordinator.md"), frontmatter, set())
