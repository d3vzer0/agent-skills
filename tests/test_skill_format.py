import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import pytest
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    ValidationError,
    field_validator,
)
from typing_extensions import Annotated

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
SKILL_NAME_RE = r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$"
MARKDOWN_LINK_RE = re.compile(r"!?(?<!\\)\[[^\]]+\]\(([^)]+)\)")

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SkillName = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=64, pattern=SKILL_NAME_RE)
]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=20)]


class SkillFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: SkillName
    description: Description
    license: NonEmptyString | None = None
    compatibility: (
        NonEmptyString | list[NonEmptyString] | dict[str, NonEmptyString] | None
    ) = None
    metadata: dict[str, NonEmptyString] | None = None

    @field_validator("description")
    @classmethod
    def description_must_be_one_line(cls, value: str) -> str:
        if "\n" in value:
            raise ValueError("description must be a single line")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_keys_must_be_non_empty(
        cls, value: dict[str, str] | None
    ) -> dict[str, str] | None:
        if value is not None and any(not key.strip() for key in value):
            raise ValueError("metadata keys must be non-empty strings")
        return value

    @field_validator("compatibility")
    @classmethod
    def compatibility_keys_must_be_non_empty(cls, value: Any) -> Any:
        if isinstance(value, dict) and any(not key.strip() for key in value):
            raise ValueError("compatibility keys must be non-empty strings")
        return value


def parse_skill_file(path: Path) -> tuple[SkillFrontmatter, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        pytest.fail(f"{path}: SKILL.md must start with YAML frontmatter")

    try:
        end = lines.index("---", 1)
    except ValueError:
        pytest.fail(f"{path}: YAML frontmatter must end with ---")

    raw_frontmatter = "\n".join(lines[1:end])
    raw_body = "\n".join(lines[end + 1 :]).strip()

    try:
        data = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as exc:
        pytest.fail(f"{path}: invalid YAML frontmatter: {exc}")

    if not isinstance(data, dict):
        pytest.fail(f"{path}: YAML frontmatter must be a mapping")

    try:
        frontmatter = SkillFrontmatter.model_validate(data)
    except ValidationError as exc:
        pytest.fail(f"{path}: invalid frontmatter:\n{exc}")

    return frontmatter, raw_body


def skill_directories() -> list[Path]:
    return sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())


def iter_relative_markdown_links(markdown_path: Path) -> list[str]:
    text = markdown_path.read_text(encoding="utf-8")
    links: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(text):
        target = match.group(1).strip()
        if not target or target.startswith("#"):
            continue
        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc:
            continue
        links.append(unquote(parsed.path))
    return links


def test_skills_directory_contains_only_skill_directories() -> None:
    assert SKILLS_DIR.exists(), "skills/ directory is required"

    root_files = sorted(path.name for path in SKILLS_DIR.iterdir() if path.is_file())
    assert root_files == [], (
        f"skills/ should contain skill directories only, found files: {root_files}"
    )

    assert skill_directories(), "skills/ must contain at least one skill directory"


def test_each_skill_has_valid_skill_md() -> None:
    names: dict[str, Path] = {}

    for skill_dir in skill_directories():
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists(), f"{skill_dir}: missing SKILL.md"

        frontmatter, body = parse_skill_file(skill_file)

        assert frontmatter.name == skill_dir.name, (
            f"{skill_file}: frontmatter name {frontmatter.name!r} must match directory {skill_dir.name!r}"
        )
        assert frontmatter.name not in names, (
            f"{skill_file}: duplicate skill name {frontmatter.name!r}; "
            f"already used by {names[frontmatter.name]}"
        )
        assert body, f"{skill_file}: markdown body must not be empty"
        assert body.lstrip().startswith("# "), (
            f"{skill_file}: markdown body should start with an H1 heading"
        )

        names[frontmatter.name] = skill_file


def test_skill_markdown_links_resolve_inside_skill_directory() -> None:
    for skill_dir in skill_directories():
        skill_root = skill_dir.resolve()

        for markdown_path in sorted(skill_dir.rglob("*.md")):
            for link in iter_relative_markdown_links(markdown_path):
                assert not Path(link).is_absolute(), (
                    f"{markdown_path}: link must be relative: {link}"
                )

                resolved = (markdown_path.parent / link).resolve()
                try:
                    resolved.relative_to(skill_root)
                except ValueError:
                    pytest.fail(
                        f"{markdown_path}: link escapes skill directory: {link}"
                    )

                assert resolved.exists(), (
                    f"{markdown_path}: link target does not exist: {link}"
                )
