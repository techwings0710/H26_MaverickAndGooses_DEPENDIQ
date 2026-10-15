from pathlib import Path
import pytest
from backend.scanner import scan
from backend.constraints import compatible
from backend.paths import approve


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv('DEPENDIQ_APPROVED_ROOTS', str(tmp_path))
    return tmp_path


def test_real_manifest_and_aliases(repo):
    (repo / 'requirements.txt').write_text('Pydantic==1.10.13\npython_dateutil\n-r requirements-dev.txt\n')
    (repo / 'requirements-dev.txt').write_text('pytest>=8\n')
    (repo / 'pyproject.toml').write_text('[project]\ndependencies=["pydantic>=2"]\n')
    (repo / 'app.py').write_text('from pydantic import BaseModel as M\nfrom dateutil import parser\nclass A(M): pass\nparser.parse("today")\n')
    result = scan(str(repo))
    deps = {d.name:d for d in result.dependencies}
    assert deps['pydantic'].risk_level == 'high'
    assert deps['pydantic'].declared_versions[0].file in ('requirements.txt','pyproject.toml')
    assert any(u.line == 3 and u.symbol == 'pydantic.BaseModel' for u in deps['pydantic'].usage_locations)
    assert any(u.line == 4 for u in deps['python-dateutil'].usage_locations)
    assert deps['python-dateutil'].risk_level == 'medium'
    assert len(deps['pytest'].declared_versions) == 1
    assert not result.scan_errors


@pytest.mark.parametrize('constraints,status', [
    (['==1.10.13','>=2'],'conflict'), (['>=2','<2'],'conflict'),
    (['>=1','<2'],'compatible'), (['~=1.4','>=2'],'conflict'),
    (['==1.*','>=2'],'conflict'), (['==1.2','!=1.2'],'conflict'),
    (['>=1','<=1','!=1'],'conflict'), (['>=1,<2','!=1.*'],'unknown'),
    (['==1.0','==1.0+local'],'compatible'), (['>=1.0rc1','<1.0'],'unknown'),
    (['>=1; python_version>"3"'],'invalid'),
])
def test_constraint_reasoning(constraints,status):
    if status=='invalid':
        with pytest.raises(Exception): compatible(constraints)
    else:
        assert compatible(constraints)[0] == status


def test_invalid_files_and_empty(repo):
    assert scan(str(repo)).dependencies == []
    (repo/'requirements.txt').write_text('not a valid requirement!!!\n--index-url https://invalid.local\n')
    (repo/'pyproject.toml').write_text('[broken')
    (repo/'bad.py').write_text('def broken(')
    s=scan(str(repo))
    assert len(s.scan_errors) == 4


def test_paths_and_symlinks(repo,tmp_path):
    with pytest.raises(ValueError): approve('relative')
    with pytest.raises(ValueError): approve('/does-not-exist')
    with pytest.raises(ValueError): approve(str(repo.parent))
    (repo/'requirements.txt').symlink_to('/etc/passwd')
    assert scan(str(repo)).dependencies == []


def test_markers_optional_groups_and_cycles(repo):
    (repo/'requirements.txt').write_text('-r requirements-dev.txt\nthing==1; python_version<"2"\n')
    (repo/'requirements-dev.txt').write_text('-r requirements.txt\n')
    (repo/'pyproject.toml').write_text('[project]\ndependencies=["thing>=2"]\n[project.optional-dependencies]\nold=["thing==1"]\n')
    s=scan(str(repo)); assert s.dependencies[0].risk_level=='low'
    assert any('Cyclic' in e for e in s.scan_errors)


def test_large_file_is_explicit_error(repo):
    (repo/'large.bin').write_bytes(b'x'*2_000_001)
    with pytest.raises(ValueError,match='2 MB'): scan(str(repo))
