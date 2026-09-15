#!/usr/bin/env python3
"""Install selected ADX skills with conflict-safe symlinks."""
import argparse
from pathlib import Path

SKILLS = ('adx-dev', 'adx-standalone', 'adx-3vm', 'adx-buildkit')
ROOT = Path(__file__).resolve().parents[1]


def install(destination, names):
    destination = Path(destination).expanduser()
    names = tuple(dict.fromkeys(names))
    if not set(names).issubset(SKILLS):
        raise ValueError('unknown skill')
    for name in names:
        source, target = ROOT / name, destination / name
        if not (source / 'SKILL.md').is_file():
            raise ValueError(f'missing source skill: {name}')
        if target.exists() or target.is_symlink():
            if not target.is_symlink() or target.resolve() != source.resolve():
                raise ValueError(f'conflicting destination: {target}')
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = destination / name
        if not target.is_symlink():
            target.symlink_to(ROOT / name, target_is_directory=True)
    return [str(destination / name) for name in names]


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination', required=True, type=Path)
    p.add_argument('--skill', action='append', choices=SKILLS)
    a = p.parse_args()
    try:
        print('\n'.join(install(a.destination, a.skill or SKILLS)))
    except (ValueError, OSError) as e:
        p.exit(1, str(e) + '\n')
