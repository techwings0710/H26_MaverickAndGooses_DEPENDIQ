"""No repository code runs on the host. Execution requires explicit Docker opt-in."""
import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4
from packaging.utils import canonicalize_name
from packaging.version import Version
from .models import Outcome, Verification
from .paths import files, approve, fingerprint
from .scanner import scan


def run_command(command, timeout=120):
    start = time.monotonic()
    # A regular file avoids pipe deadlocks and bounded reads avoid retaining giant logs.
    with tempfile.TemporaryFile() as log:
        try:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, shell=False,
                                    env={'PATH': os.environ.get('PATH', ''), 'HOME': os.environ.get('HOME', '/tmp')})
            log.seek(0)
            output = log.read(16000).decode('utf-8', errors='replace')
            return Outcome(status='PASSED' if result.returncode == 0 else 'FAILED', classification='EXECUTION-VERIFIED', commands=[command], exit_code=result.returncode, output=output, duration_seconds=round(time.monotonic() - start, 3))
        except subprocess.TimeoutExpired:
            log.seek(0)
            return Outcome(status='TIMEOUT', classification='EXECUTION-VERIFIED', commands=[command], output=log.read(16000).decode('utf-8', errors='replace'), reason=f'Exceeded {timeout}s; container cleanup requested.', duration_seconds=round(time.monotonic() - start, 3))
        except OSError as exc:
            return Outcome(commands=[command], reason=f'{type(exc).__name__}: {exc}')


def rewrite(root, dependency, version):
    """Update only observed PEP 508 literal declarations in disposable copies."""
    changed = []
    pattern = re.compile(r'(?i)(?<![\w.-])' + re.escape(dependency).replace(r'\-', '[-_.]') + r'(\[[^\]]+\])?\s*(?:[~<>=!][^\s\"\'\];#]*)?')
    for path in files(root):
        if path.name != 'pyproject.toml' and not (path.name.startswith('requirements') and path.suffix in ('.txt', '.in')):
            continue
        text = path.read_text()
        updated = pattern.sub(lambda m: dependency + (m.group(1) or '') + '==' + version, text)
        if updated != text:
            path.write_text(updated)
            changed.append(str(path.relative_to(root)))
    return changed


def static_check(root):
    errors = []
    count = 0
    for path in files(root):
        if path.suffix == '.py':
            count += 1
            try:
                ast.parse(path.read_text(), filename=str(path.relative_to(root)))
            except (SyntaxError, UnicodeError) as exc:
                errors.append(str(exc))
    result = scan(str(root))
    return {'classification': 'OBSERVED', 'check': 'AST parse and manifest constraint analysis; no project code executed',
            'python_files': count, 'syntax_errors': errors, 'conflicts': [d.name for d in result.dependencies if d.risk_level == 'high'], 'scan_errors': result.scan_errors}


def execute(root, image):
    container = 'dependiq-' + uuid4().hex
    command = ['docker', 'run', '--name', container, '--rm', '--pull=never', '--network=none', '--read-only',
               '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=128', '--cpus=1', '--memory=1g',
               '--user=65534:65534', '--tmpfs=/tmp:rw,nosuid,size=256m', '--mount', f'type=bind,src={root},dst=/repo,readonly',
               '--workdir=/repo', '--env=PYTHONPATH=/repo', '--env=PYTHONDONTWRITEBYTECODE=1', image,
               'python', '-c', RUNNER]
    result = run_command(command)
    if result.status == 'TIMEOUT':
        run_command(['docker', 'rm', '-f', container], timeout=10)
    match = re.search(r'DEPENDIQ_RESULT=(\{.*\})', result.output)
    if match:
        body = json.loads(match.group(1))
        result.python_version = body['python_version']
        result.installation_problem = body['installation_problem']
        result.tests_completed = body['tests_completed']
        result.passed, result.failed, result.skipped = body['passed'], body['failed'], body['skipped']
    elif result.exit_code == 0:
        result.status = 'INCOMPLETE'
        result.reason = 'No structured test completion evidence in captured output.'
    return result


# Fixed runner: no model/user shell strings, no index/network or source distribution builds.
# Image must supply a Python interpreter, pytest, and a compatible offline wheelhouse.
RUNNER = '''import sys, subprocess, json, pathlib, tempfile, os
env = dict(os.environ, PYTHONPATH='/repo', PYTHONDONTWRITEBYTECODE='1')
reqs = [p for p in ('requirements.txt','requirements-dev.txt') if pathlib.Path(p).is_file()]
install = [sys.executable, '-m', 'pip', 'install', '--no-index', '--only-binary=:all:', '--find-links=/wheels', '--target=/tmp/deps']
for p in reqs: install += ['-r', p]
if not reqs:
    data = __import__('tomllib').loads(pathlib.Path('pyproject.toml').read_text()) if pathlib.Path('pyproject.toml').exists() else {}
    install += data.get('project',{}).get('dependencies',[])
print('INSTALL_COMMAND='+json.dumps(install), flush=True)
rc = subprocess.call(install, env=env) if len(install) > 10 else 0
report = '/tmp/result.json'
env['PYTHONPATH'] = '/tmp/deps:/repo'
env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
plugin = "import json\\ndef pytest_sessionfinish(session, exitstatus):\\n r=session.config.pluginmanager.get_plugin('terminalreporter')\\n stats=r.stats\\n json.dump({'passed':len(stats.get('passed',[])),'failed':len(stats.get('failed',[]))+len(stats.get('error',[])),'skipped':len(stats.get('skipped',[])),'completed':exitstatus in (0,1)},open('/tmp/result.json','w'))\\n"
pathlib.Path('/tmp/dependiq_report.py').write_text(plugin)
env['PYTHONPATH'] += ':/tmp'
command=[sys.executable,'-m','pytest','-q','-p','dependiq_report','-p','no:cacheprovider','--override-ini=addopts=']
print('TEST_COMMAND='+json.dumps(command), flush=True)
test_rc = subprocess.call(command, env=env) if rc==0 else None
stats = json.loads(pathlib.Path(report).read_text()) if pathlib.Path(report).exists() else {}
print('DEPENDIQ_RESULT='+json.dumps({'python_version':sys.version,'installation_problem':rc!=0,'tests_completed':stats.get('completed',False),'passed':stats.get('passed'),'failed':stats.get('failed'),'skipped':stats.get('skipped')}), flush=True)
sys.exit(rc if rc else (test_rc if test_rc is not None else 1))
'''


def verify(request, snapshot):
    root = approve(snapshot.repository_path)
    if fingerprint(root) != snapshot.fingerprint:
        raise ValueError('Repository changed since scan. Rescan before verification.')
    name = canonicalize_name(request.dependency_name)
    if name not in {d.name for d in snapshot.dependencies}:
        raise ValueError('Select a dependency from the current scan.')
    version = str(Version(request.proposed_version))
    baseline = Outcome(reason='Execution disabled. Enable DEPENDIQ_ENABLE_EXECUTION=1, inspect/trust the repository, and prepare Docker with offline wheels.')
    migration = baseline.model_copy(deep=True)
    # Only copy scanned, size-bounded regular files; omit secrets and symlinks.
    with tempfile.TemporaryDirectory(prefix='dependiq-') as temp:
        base, target = Path(temp) / 'baseline', Path(temp) / 'migration'
        for dest in (base, target):
            dest.mkdir()
            for path in files(root):
                if path.name.lower().endswith(('.pem', '.key', '.p12')):
                    continue
                out = dest / path.relative_to(root)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, out)
        changed = rewrite(target, name, version)
        # Copies are internal trusted paths for deterministic parsing only.
        previous = os.environ.get('DEPENDIQ_APPROVED_ROOTS')
        # Avoid global environment mutation: scanner accepts an internal approval explicitly below.
        static = {'baseline': static_syntax_and_constraints(base), 'migration': static_syntax_and_constraints(target),
                  'changed_files': changed, 'classification': 'OBSERVED'}
        reason = None
        if not request.trusted_repository:
            reason = 'Repository trust has not been explicitly acknowledged. Static checks only.'
        elif os.getenv('DEPENDIQ_ENABLE_EXECUTION') != '1':
            reason = baseline.reason
        elif not shutil.which('docker'):
            reason = 'Docker executable is unavailable. No project tests executed on host.'
        elif not changed:
            reason = 'No supported literal declarations changed; migration execution is not meaningful.'
        else:
            image = os.getenv('DEPENDIQ_VERIFY_IMAGE', 'dependiq-verifier:local')
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._/:@-]{0,200}', image):
                raise ValueError('Invalid configured Docker image name.')
            inspect = run_command(['docker', 'image', 'inspect', image], timeout=10)
            if inspect.exit_code != 0:
                reason = 'Offline verification image unavailable or Docker daemon stopped. Build docs/verification.Dockerfile first.'
            else:
                baseline, migration = execute(base, image), execute(target, image)
                static['image_id'] = json.loads(inspect.output)[0].get('Id')
        if reason:
            baseline = Outcome(reason=reason)
            migration = Outcome(reason=reason)
    status = 'NOT RUN' if baseline.status == 'NOT RUN' else ('COMPLETED' if baseline.tests_completed and migration.tests_completed else 'INCOMPLETE')
    return Verification(scan_id=snapshot.scan_id, dependency_name=name, proposed_version=version,
                        verification_status=status, baseline=baseline, migration=migration, static_comparison=static,
                        compatibility_gaps=['Static conflict resolution does not establish runtime API compatibility.'] + ([] if migration.tests_completed else ['Migration tests have not completed.']),
                        limitations=['Containers reduce risk but are not a guarantee against malicious code; run only inspected repositories.', 'Original source is unchanged. Only same-package exact-version manifest migration is supported.', 'Offline wheels and a locally prepared container image are required; plugins are disabled, so plugin-dependent suites need a reviewed custom image.'])


def static_syntax_and_constraints(root):
    # Child process runs only OUR parser with a temporary allowlist, never target code.
    # Use pure parsing here instead to avoid subprocess/global env changes.
    syntax_errors, constraints = [], {}
    from packaging.requirements import Requirement
    from .constraints import compatible
    import tomllib
    for path in files(root):
        try:
            if path.suffix == '.py':
                ast.parse(path.read_text(), filename=str(path.relative_to(root)))
            values = []
            if path.name == 'pyproject.toml':
                values = tomllib.loads(path.read_text()).get('project', {}).get('dependencies', [])
            elif path.name.startswith('requirements') and path.suffix in ('.txt', '.in'):
                values = [v.strip() for v in path.read_text().splitlines() if v.strip() and not v.lstrip().startswith(('#', '-'))]
            for value in values:
                req = Requirement(value)
                if not req.marker or req.marker.evaluate():
                    constraints.setdefault(canonicalize_name(req.name), []).append(str(req.specifier))
        except (ValueError, SyntaxError, UnicodeError) as exc:
            syntax_errors.append(f'{path.relative_to(root)}: {exc}')
    return {'classification': 'OBSERVED', 'check': 'AST syntax + manifest constraint checks; project tests not executed',
            'errors': syntax_errors, 'conflicts': [n for n, c in constraints.items() if compatible(c)[0] == 'conflict']}
