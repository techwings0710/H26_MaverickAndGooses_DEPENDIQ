import ast
import importlib.metadata
import json
from pathlib import Path
from .models import Usage
from packaging.utils import canonicalize_name

# Import aliases, not a package risk list. Provenance is exposed for every match.
ALIASES = {'python-dateutil': ['dateutil'], 'pyyaml': ['yaml'], 'beautifulsoup4': ['bs4'], 'pillow': ['PIL'], 'scikit-learn': ['sklearn'], 'opencv-python': ['cv2']}


def trace(root: Path, paths: list[Path], names: list[str]):
    mapping = {n: {n.replace('-', '_'): 'distribution-name heuristic; mapping unconfirmed'} for n in names}
    for n in names:
        for alias in ALIASES.get(n, []):
            mapping[n][alias] = 'documented distribution/import alias'
    for module, distributions in importlib.metadata.packages_distributions().items():
        for dist in distributions:
            n = canonicalize_name(dist)
            if n in mapping:
                mapping[n][module] = 'local installed distribution metadata (not target environment)'
    override = root / 'dependiq-import-map.json'
    errors = []
    if override in paths:
        try:
            data = json.loads(override.read_text())
            for name, modules in data.items():
                normalized = canonicalize_name(name)
                if normalized in mapping and isinstance(modules, list):
                    for module in modules:
                        if isinstance(module, str) and module.isidentifier():
                            mapping[normalized][module] = 'repository-provided dependiq-import-map.json'
        except (ValueError, OSError, AttributeError) as exc:
            errors.append(f'dependiq-import-map.json: {exc}')
    found = {n: [] for n in names}
    for path in paths:
        if path.suffix != '.py':
            continue
        rel = str(path.relative_to(root))
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=rel)
        except (SyntaxError, UnicodeError, OSError) as exc:
            errors.append(f'{rel}: {exc}')
            continue
        lines, bindings = source.splitlines(), {}
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.Import):
                imported = [(a.name.split('.')[0], a.asname or a.name.split('.')[0], a.name) for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                imported = [(node.module.split('.')[0], a.asname or a.name, node.module + '.' + a.name) for a in node.names]
            for module, binding, symbol in imported:
                for name in names:
                    if module in mapping[name]:
                        bindings[binding] = (name, symbol, mapping[name][module])
                        found[name].append(Usage(file=rel, line=node.lineno, symbol=symbol, kind='import', snippet=lines[node.lineno - 1].strip()[:300], mapping=mapping[name][module]))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in bindings:
                name, symbol, origin = bindings[node.id]
                found[name].append(Usage(file=rel, line=node.lineno, symbol=symbol, kind='test reference' if 'test' in path.parts or path.name.startswith('test_') else 'usage', snippet=lines[node.lineno - 1].strip()[:300], mapping=origin + '; AST alias match, scope/shadowing not resolved'))
    return found, errors
