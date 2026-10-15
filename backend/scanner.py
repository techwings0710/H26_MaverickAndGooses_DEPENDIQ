import itertools
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from packaging.requirements import Requirement, InvalidRequirement
from packaging.utils import canonicalize_name
from .constraints import compatible
from .models import Declaration, Dependency, Evidence, ScanResult
from .paths import approve, files, fingerprint
from .usage import trace


def scan(repository_path: str) -> ScanResult:
    root = approve(repository_path)
    before = fingerprint(root)
    paths = list(files(root))
    dependencies, errors, manifests, seen = {}, [], set(), set()

    def add(raw, path, line, group='runtime'):
        try:
            req = Requirement(raw)
        except InvalidRequirement as exc:
            errors.append(f'{path.relative_to(root)}:{line}: invalid/unsupported requirement {raw!r}: {exc}')
            return
        name = canonicalize_name(req.name)
        marker = str(req.marker or '')
        try:
            active = req.marker.evaluate() if req.marker and 'extra' not in marker else (None if req.marker else True)
        except Exception:
            active = None
        dep = dependencies.setdefault(name, Dependency(name=name))
        dep.declared_versions.append(Declaration(file=str(path.relative_to(root)), line=line, constraint=str(req.specifier), marker=marker, group=group, active=active, url=req.url))
        dep.evidence.append(Evidence(type='declaration', file=str(path.relative_to(root)), line=line, detail=raw))

    def requirements(path, stack=()):
        if path in stack:
            errors.append(f'Cyclic requirements include: {path.relative_to(root)}')
            return
        if path in seen:
            return
        if path not in paths:
            errors.append(f'Missing, excluded, or unsafe requirements include: {path.name}')
            return
        seen.add(path)
        manifests.add(str(path.relative_to(root)))
        for i, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            value = re.split(r'\s+#', raw.strip(), maxsplit=1)[0].strip()
            if not value or value.startswith('#'):
                continue
            if value.startswith(('-r ', '--requirement ')):
                child = (path.parent / value.split(maxsplit=1)[1]).resolve()
                if child.is_relative_to(root):
                    requirements(child, (*stack, path))
                else:
                    errors.append(f'{path.name}:{i}: include escapes approved root')
            elif value.startswith('-') or value.endswith('\\'):
                errors.append(f'{path.name}:{i}: pip directive/continuation unsupported; not executed: {value}')
            else:
                add(value, path, i, 'dev' if 'dev' in path.name or 'test' in path.name else 'runtime')

    for path in paths:
        try:
            if path.suffix in ('.txt', '.in') and path.name.startswith('requirements'):
                requirements(path)
            elif path.name == 'pyproject.toml':
                manifests.add(str(path.relative_to(root)))
                text = path.read_text(encoding='utf-8')
                data = tomllib.loads(text)
                project = data.get('project', {})
                groups = [('runtime', project.get('dependencies', []))]
                groups += [('optional:' + k, v) for k, v in project.get('optional-dependencies', {}).items()]
                groups += [('dev:' + k, v) for k, v in data.get('dependency-groups', {}).items()]
                for group, values in groups:
                    if not isinstance(values, list):
                        errors.append(f'{path.name}: {group} dependencies must be an array')
                        continue
                    used_lines = set()
                    for value in values:
                        if not isinstance(value, str):
                            errors.append(f'{path.name}: dependency-group includes are unsupported: {value}')
                            continue
                        # Locate literal declaration text; line 1 is never invented as evidence.
                        candidates = [i for i, line in enumerate(text.splitlines(), 1) if value in line and i not in used_lines]
                        line = candidates[0] if candidates else 0
                        used_lines.add(line)
                        add(value, path, line, group)
                if project.get('dynamic') or data.get('tool', {}).get('poetry'):
                    errors.append(f'{path.name}: dynamic/Poetry metadata not resolved; only PEP 621/735 arrays parsed')
            elif path.name in ('setup.py', 'setup.cfg', 'Pipfile', 'poetry.lock', 'uv.lock'):
                errors.append(f'{path.relative_to(root)}: unsupported manifest/lockfile; not evaluated')
        except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
            errors.append(f'{path.relative_to(root)}: {exc}')
    usage, usage_errors = trace(root, paths, list(dependencies))
    errors.extend(usage_errors)
    for name, dep in dependencies.items():
        dep.usage_locations = usage[name]
        active = [d for d in dep.declared_versions if d.active is True and not d.group.startswith('optional:')]
        constraints = [d.constraint for d in active if not d.url]
        state, explanation = compatible(constraints)
        if state == 'conflict':
            dep.risk_level = 'high'
            dep.risk_indicators.append('Conflicting version constraints')
            dep.evidence.append(Evidence(type='manifest_conflict', file=', '.join(sorted({d.file for d in active})), detail=explanation + ' Runtime and development declarations are compared together; alternative installers may resolve different environments.'))
        elif state == 'unknown':
            dep.risk_level = 'unknown'
            dep.uncertainties.append(explanation)
        for d in dep.declared_versions:
            if not d.constraint and not d.url:
                if dep.risk_level == 'low':
                    dep.risk_level = 'medium'
                if 'Unbounded dependency declaration' not in dep.risk_indicators:
                    dep.risk_indicators.append('Unbounded dependency declaration')
                dep.evidence.append(Evidence(type='reproducibility', file=d.file, line=d.line, detail='No declared version boundary. A lockfile may mitigate this; no vulnerability or abandonment claim is made.'))
            if d.url:
                dep.uncertainties.append('Direct URL requirement: version compatibility and provenance are not resolved.')
            if d.marker or d.group.startswith('optional:'):
                dep.uncertainties.append(f'{d.file}: marker {d.marker or "none"}, group {d.group}; optional groups excluded from combined conflict proof.')
        if not dep.usage_locations:
            dep.uncertainties.append('No mapped AST imports found. This does not prove the package is unused; dynamic imports and plugins are not resolved.')
    after = fingerprint(root)
    if before != after:
        raise ValueError('Repository changed during scan. Retry with a stable checkout.')
    return ScanResult(scan_id=str(uuid4()), repository=root.name, repository_path=str(root), fingerprint=after,
                      generated_at=datetime.now(timezone.utc).isoformat(), dependencies=sorted(dependencies.values(), key=lambda d: ({'high': 0, 'medium': 1, 'unknown': 2, 'low': 3}[d.risk_level], d.name)),
                      scan_errors=errors, python_files=sum(p.suffix == '.py' for p in paths),
                      test_files=[str(p.relative_to(root)) for p in paths if p.suffix == '.py' and (p.name.startswith('test_') or p.name.endswith('_test.py'))],
                      manifests=sorted(manifests), limitations=['Offline manifest analysis is not a vulnerability, release freshness, or transitive dependency audit.', 'Markers evaluated against the backend Python environment; optional extras are not assumed active.', 'AST alias matches are approximate: shadowing, scope, dynamic imports, and configuration semantics need human review.', 'TOML line locations use literal matching; line 0 means a declaration could not be located exactly.'])
