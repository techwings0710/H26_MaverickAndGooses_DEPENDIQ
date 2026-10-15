import json
import subprocess
import sys
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import VerifyRequest
from backend.scanner import scan
from backend.verifier import verify, run_command, rewrite, RUNNER


@pytest.fixture
def repo(tmp_path,monkeypatch):
    monkeypatch.setenv('DEPENDIQ_APPROVED_ROOTS',str(tmp_path))
    monkeypatch.setenv('DEPENDIQ_ENABLE_EXECUTION','0')
    (tmp_path/'requirements.txt').write_text('example==1\n')
    (tmp_path/'pyproject.toml').write_text('[project]\ndependencies=["example>=2"]\n')
    (tmp_path/'app.py').write_text('import example\n')
    return tmp_path


def test_api_validation_and_capsule(repo,monkeypatch):
    client=TestClient(app)
    assert client.post('/api/scan',json={}).status_code==422
    assert client.post('/api/scan',json={'repository_path':'/etc'}).status_code==400
    result=client.post('/api/scan',json={'repository_path':str(repo)}); assert result.status_code==200
    s=result.json(); assert s['dependencies'][0]['risk_level']=='high'
    def unavailable(self):raise __import__('ai.gemma_client',fromlist=['GemmaError']).GemmaError('fixture offline')
    monkeypatch.setattr('ai.gemma_client.GemmaClient.available',unavailable)
    assert client.get('/api/health').json()['ai']['status']=='unavailable'
    fake={**s,'dependencies':[]}
    ai=client.post('/api/analyze',json=fake).json()
    assert ai['dependencies'] and ai['ai_status']=='unavailable'
    v=client.post('/api/verify',json={'scan_id':s['scan_id'],'dependency_name':'example','proposed_version':'2'}).json()
    assert v['baseline']['status']=='NOT RUN'
    assert v['static_comparison']['baseline']['conflicts']==['example']
    assert v['static_comparison']['migration']['conflicts']==[]
    assert (repo/'requirements.txt').read_text()=='example==1\n'
    out=client.post('/api/capsule',json={'scan_id':s['scan_id']})
    assert 'attachment' in out.headers['content-disposition']
    cap=out.json();assert cap['schema_version']=='1.0.0'
    assert cap['verification']['migration']['tests_completed'] is False
    assert cap['scan']['dependencies'][0]['evidence'][0]['classification']=='OBSERVED'
    assert client.post('/api/capsule',json={'scan_id':'fake'}).status_code==404
    (repo/'app.py').write_text('changed = True')
    assert client.post('/api/verify',json={'scan_id':s['scan_id'],'dependency_name':'example','proposed_version':'2'}).status_code==400


def test_invalid_scenario(repo):
    s=scan(str(repo))
    with pytest.raises(ValueError):verify(VerifyRequest(scan_id=s.scan_id,dependency_name='other',proposed_version='2'),s)
    with pytest.raises(ValueError):verify(VerifyRequest(scan_id=s.scan_id,dependency_name='example',proposed_version='$(bad)'),s)


def test_subprocess_errors_and_timeout():
    r=run_command(['/does/not/exist']); assert r.status=='NOT RUN' and r.exit_code is None
    r=run_command([sys.executable,'-c','import time; time.sleep(1)'],timeout=.02)
    assert r.status=='TIMEOUT' and r.tests_completed is False
    r=run_command([sys.executable,'-c','print("actual evidence")'])
    assert r.exit_code==0 and 'actual evidence' in r.output


def test_runner_compiles():
    compile(RUNNER,'fixed-runner','exec')


def test_docker_hardening(monkeypatch,tmp_path):
    import backend.verifier as mod
    commands=[]
    from backend.models import Outcome
    monkeypatch.setattr(mod,'run_command',lambda cmd,timeout=120: (commands.append(cmd) or Outcome(status='FAILED',exit_code=1)))
    mod.execute(tmp_path,'dependiq:fixture')
    cmd=commands[0]
    assert '--network=none' in cmd and '--read-only' in cmd and '--pull=never' in cmd
    assert '--cap-drop=ALL' in cmd and '--user=65534:65534' in cmd
    assert not any('docker.sock' in p for p in cmd)


def test_rewrite_preserves_other_packages_and_markers(repo):
    p=repo/'requirements.txt'
    p.write_text('example==1; python_version >= "3"\nexample-tools==1\n# example==1 comment\n')
    rewrite(repo,'example','2')
    assert p.read_text()=='example==2; python_version >= "3"\nexample-tools==1\n# example==1 comment\n'
