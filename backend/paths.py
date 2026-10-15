import hashlib
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'dist', 'build', '.dependiq', '.tox'}
MAX_FILES = 10000
MAX_BYTES = 2_000_000


def approved_roots():
    value = os.getenv('DEPENDIQ_APPROVED_ROOTS', '')
    return [Path(p).expanduser().resolve() for p in value.split(os.pathsep) if p] or [PROJECT / 'samples']


def approve(path: str) -> Path:
    raw = Path(path).expanduser()
    if not raw.is_absolute():
        raise ValueError('Use an absolute repository path.')
    root = raw.resolve()
    if not root.is_dir():
        raise ValueError('Repository directory does not exist.')
    if not any(root == p or p in root.parents for p in approved_roots()):
        raise ValueError('Path is not in DEPENDIQ_APPROVED_ROOTS. Configure an approved root before scanning.')
    return root


def files(root: Path):
    count = 0
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith('.') and not (Path(directory) / d).is_symlink())
        for name in sorted(names):
            path = Path(directory) / name
            if path.is_symlink() or name.startswith('.'):
                continue
            count += 1
            if count > MAX_FILES:
                raise ValueError(f'Repository exceeds {MAX_FILES} files; narrow the approved repository.')
            yield path


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in files(root):
        if path.stat().st_size > MAX_BYTES:
            raise ValueError(f'File exceeds 2 MB scan limit: {path.relative_to(root)}')
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
    return digest.hexdigest()
