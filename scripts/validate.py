#!/usr/bin/env python3
"""Validate the four skill contracts and local Markdown references without third-party packages."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('adx-dev', 'adx-standalone', 'adx-3vm', 'adx-buildkit')


def validate(root=ROOT):
    errors = []
    for name in SKILLS:
        skill = root / name / 'SKILL.md'
        if not skill.is_file():
            errors.append(f'missing {name}')
            continue
        content = skill.read_text()
        match = re.match(r'\A---\nname: ([a-z0-9-]+)\ndescription: ([^\n]+)\n---\n', content)
        if not match or match[1] != name or len(match[2]) > 1024:
            errors.append(f'invalid frontmatter: {skill}')
        ui = root / name / 'agents/openai.yaml'
        if not ui.is_file() or '$' + name not in ui.read_text():
            errors.append(f'missing invocation metadata: {name}')
    for doc in root.rglob('*.md'):
        if '.git' in doc.parts or 'out' in doc.parts:
            continue
        for target in re.findall(r'\]\(([^\s)]+)\)', doc.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            if not (doc.parent / target.split('#')[0]).exists():
                errors.append(f'broken link: {doc.relative_to(root)} -> {target}')
        if '[TODO:' in doc.read_text():
            errors.append(f'unfinished scaffold: {doc}')
    return errors


if __name__ == '__main__':
    errors = validate()
    print('\n'.join(errors) if errors else 'Four skills and all local Markdown references validated')
    sys.exit(bool(errors))
