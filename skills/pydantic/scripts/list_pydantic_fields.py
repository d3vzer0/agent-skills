#!/usr/bin/env python3
"""Print Pydantic V2 field metadata for a model.

Pass a model import string as `module:ClassName` or `module.ClassName`.
Run from the project root, or set PYTHONPATH so the target module is importable.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any


def import_object(import_path: str) -> Any:
    if ':' in import_path:
        module_name, object_path = import_path.split(':', 1)
    else:
        module_name, _, object_path = import_path.rpartition('.')
    if not module_name or not object_path:
        raise ValueError('model must be an import path like package.module:Model or package.module.Model')

    obj: Any = importlib.import_module(module_name)
    for part in object_path.split('.'):
        obj = getattr(obj, part)
    return obj


def safe_repr(value: Any) -> str | None:
    if value is None:
        return None
    text = repr(value)
    if len(text) > 160:
        return f'{text[:157]}...'
    return text


def field_summary(model: type[Any]) -> list[dict[str, Any]]:
    fields = getattr(model, 'model_fields', None)
    if fields is None:
        raise TypeError(f'{model!r} does not expose Pydantic V2 model_fields')

    rows: list[dict[str, Any]] = []
    for name, field in fields.items():
        rows.append(
            {
                'name': name,
                'annotation': safe_repr(field.annotation),
                'required': field.is_required(),
                'default': None if field.is_required() else safe_repr(field.default),
                'default_factory': safe_repr(field.default_factory),
                'alias': field.alias,
                'validation_alias': safe_repr(field.validation_alias),
                'serialization_alias': field.serialization_alias,
                'metadata': [safe_repr(item) for item in field.metadata],
            }
        )
    return rows


def print_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print('No fields found.')
        return

    headers = ['name', 'required', 'annotation', 'alias', 'validation_alias', 'serialization_alias', 'default']
    widths = {
        header: max(len(header), *(len(str(row.get(header) or '')) for row in rows))
        for header in headers
    }
    print('  '.join(header.ljust(widths[header]) for header in headers))
    print('  '.join('-' * widths[header] for header in headers))
    for row in rows:
        print('  '.join(str(row.get(header) or '').ljust(widths[header]) for header in headers))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', help='Model import path, e.g. package.module:Model')
    parser.add_argument('--json', action='store_true', help='Print JSON instead of a table')
    args = parser.parse_args(argv)

    try:
        model = import_object(args.model)
        rows = field_summary(model)
    except Exception as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        print_table(rows)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
