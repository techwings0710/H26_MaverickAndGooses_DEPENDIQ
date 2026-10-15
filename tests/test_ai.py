import json
import httpx
import pytest
from ai.gemma_client import GemmaClient, GemmaError
from ai.schemas import Recommendation
from backend.models import Dependency

# Synthetic model interface fixtures, never represented as genuine inference.
VALID={'proposed_replacement':'example>=2','technical_reasoning':'Resolve the observed contradiction.', 'migration_steps':['Align manifests'], 'suggested_tests':['Run original tests'], 'potential_compatibility_gaps':['API may differ'], 'uncertainties':['Release not checked'], 'confidence':'low','verified':False,'classification':'AI-SUGGESTED'}


def handler(content=json.dumps(VALID), calls=None):
    def respond(request):
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':'gemma4:e2b','digest':'fixture'}]})
        payload=json.loads(request.content)
        assert payload['format']['properties']['verified']['const'] is False
        if calls is not None:calls.append(payload)
        return httpx.Response(200,json={'model':'gemma4:e2b','done':True,'message':{'content':content}})
    return httpx.MockTransport(respond)


def test_valid_response():
    c=GemmaClient(handler()); r=c.recommend(Dependency(name='example'))
    assert r.classification=='AI-SUGGESTED' and not r.verified
    assert c.info['digest']=='fixture'


def test_invalid_json_retries():
    calls=[]; c=GemmaClient(handler('bad json',calls))
    with pytest.raises(GemmaError,match='two attempts'):c.recommend(Dependency(name='example'))
    assert len(calls)==2


def test_forbids_fake_verification():
    with pytest.raises(ValueError):Recommendation.model_validate({**VALID,'verified':True})


def test_unavailable():
    def unavailable(request):raise httpx.ConnectError('offline',request=request)
    with pytest.raises(GemmaError,match='unavailable'):GemmaClient(httpx.MockTransport(unavailable)).available()


def test_model_not_installed():
    with pytest.raises(GemmaError,match='not installed'):
        GemmaClient(httpx.MockTransport(lambda r:httpx.Response(200,json={'models':[]}))).available()


def test_timeout():
    def timeout(request):
        if request.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':'gemma4:e2b'}]})
        raise httpx.ReadTimeout('timeout',request=request)
    with pytest.raises(GemmaError,match='timed out'):GemmaClient(httpx.MockTransport(timeout)).recommend(Dependency(name='a'))


def test_cloud_forbidden(monkeypatch):
    monkeypatch.setenv('GEMMA_MODEL','gemma4:31b-cloud')
    with pytest.raises(GemmaError):GemmaClient()
    monkeypatch.setenv('GEMMA_MODEL','gemma3:4b')
    with pytest.raises(GemmaError):GemmaClient()
    monkeypatch.setenv('GEMMA_MODEL','gemma4:e2b');monkeypatch.setenv('OLLAMA_BASE_URL','https://example.com')
    with pytest.raises(GemmaError):GemmaClient()
