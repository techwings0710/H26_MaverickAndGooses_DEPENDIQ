import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ai.gemma_client import GemmaClient, GemmaError
from .models import ScanRequest, ScanResult, VerifyRequest, CapsuleRequest, Verification
from .paths import PROJECT, approved_roots
from .scanner import scan
from .verifier import verify

app = FastAPI(title='DEPENDIQ', version='1.0.0', description='Local dependency evidence and migration intelligence')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
LOCK = RLock()
SESSIONS = {}
VERIFICATIONS = {}


def save(snapshot):
    # Local persistence is deliberate; contains repository evidence, no credentials.
    directory = PROJECT / '.dependiq'
    directory.mkdir(mode=0o700, exist_ok=True)
    target = directory / (snapshot.scan_id + '.json')
    tmp = target.with_suffix('.tmp')
    with LOCK:
        tmp.write_text(json.dumps({'scan': snapshot.model_dump(), 'verification': VERIFICATIONS.get(snapshot.scan_id)}, indent=2))
        tmp.replace(target)
        SESSIONS[snapshot.scan_id] = snapshot.model_copy(deep=True)
        while len(SESSIONS) > 100:
            key = next(iter(SESSIONS))
            del SESSIONS[key]
            VERIFICATIONS.pop(key, None)


def session(scan_id):
    with LOCK:
        if scan_id not in SESSIONS:
            raise HTTPException(404, 'Scan session not found. Rescan after a backend restart.')
        return SESSIONS[scan_id].model_copy(deep=True)


@app.get('/api/health')
def health():
    try:
        client = GemmaClient()
        model = client.available()
        ai = {'status': 'ready', **model}
    except (GemmaError, ValueError) as exc:
        ai = {'status': 'unavailable', 'reason': str(exc), 'model': os.getenv('GEMMA_MODEL', 'gemma4:e2b')}
    return {'status': 'ok', 'version': '1.0.0', 'approved_roots': list(map(str, approved_roots())), 'ai': ai,
            'execution_enabled': os.getenv('DEPENDIQ_ENABLE_EXECUTION') == '1'}


@app.post('/api/scan', response_model=ScanResult)
def scan_repository(request: ScanRequest):
    try:
        result = scan(request.repository_path)
        save(result)
        return result
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post('/api/analyze', response_model=ScanResult)
def analyze(request: ScanResult):
    # Keep shared contract (entire scan response), but accept no client-forged observations.
    result = session(request.scan_id)
    flagged = [d for d in result.dependencies if d.risk_level != 'low']
    if not flagged:
        result.ai_status = 'no_flagged_dependencies'
        save(result)
        return result
    try:
        client = GemmaClient()
        client.available()
    except (GemmaError, ValueError) as exc:
        result.ai_status = 'unavailable'
        for dependency in flagged:
            dependency.ai_error = str(exc)
        save(result)
        return result
    for dep in flagged[:12]:
        try:
            dep.ai_recommendation = client.recommend(dep).model_dump()
            dep.ai_error = None
        except (GemmaError, ValueError) as exc:
            dep.ai_error = str(exc)
    for dep in flagged[12:]:
        dep.ai_error = 'Per-request budget: at most 12 flagged dependencies. Narrow the repository for further analysis.'
    result.model_info = client.info
    result.ai_status = 'completed' if all(d.ai_recommendation and not d.ai_error for d in flagged) else 'partial' if any(d.ai_recommendation for d in flagged) else 'unavailable'
    save(result)
    return result


@app.post('/api/verify', response_model=Verification)
def verify_repository(request: VerifyRequest):
    snapshot = session(request.scan_id)
    try:
        result = verify(request, snapshot)
        with LOCK:
            VERIFICATIONS[snapshot.scan_id] = result.model_dump()
            save(snapshot)
        return result
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post('/api/capsule')
def capsule(request: CapsuleRequest):
    snapshot = session(request.scan_id)
    with LOCK:
        verification = VERIFICATIONS.get(request.scan_id)
    payload = {'schema_version': '1.0.0', 'kind': 'Dependency Exit Capsule',
               'generation': {'generated_at': datetime.now(timezone.utc).isoformat(), 'generator': 'DEPENDIQ 1.0.0'},
               'evidence_legend': {'OBSERVED': 'Deterministic repository observations; see scope limitations.', 'AI-SUGGESTED': 'Unverified local model recommendations.', 'EXECUTION-VERIFIED': 'Actually attempted commands with recorded outcomes; failure is not compatibility.'},
               'scan': snapshot.model_dump(), 'verification': verification,
               'open_concerns': snapshot.scan_errors + ['No security advisory or live package registry lookup was performed.'] + ([] if snapshot.ai_status == 'completed' else ['AI analysis is incomplete or unavailable.']) + ([] if verification and verification['migration']['tests_completed'] else ['Migration runtime compatibility remains unverified.']),
               'limitations': snapshot.limitations}
    return JSONResponse(payload, headers={'Content-Disposition': f'attachment; filename="dependiq-{request.scan_id[:8]}.json"'})
