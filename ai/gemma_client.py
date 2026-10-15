import os
from urllib.parse import urlparse
import httpx
from pydantic import ValidationError
from .prompts import messages
from .schemas import Recommendation


class GemmaError(RuntimeError):
    pass


class GemmaClient:
    def __init__(self, transport=None):
        self.base = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/')
        url = urlparse(self.base)
        if url.scheme != 'http' or url.hostname not in ('localhost', '127.0.0.1', '::1') or url.username or url.password:
            raise GemmaError('Ollama must use a local HTTP loopback endpoint; cloud inference is disabled.')
        self.model = os.getenv('GEMMA_MODEL', 'gemma4:e2b')
        if not self.model.startswith('gemma4:') or 'cloud' in self.model.lower():
            raise GemmaError('GEMMA_MODEL must be an exact local gemma4:<tag> identifier; no substitution is permitted.')
        self.timeout = min(max(float(os.getenv('GEMMA_TIMEOUT', '120')), 1), 300)
        self.transport = transport
        self.info = {'model': self.model, 'access_method': 'Ollama local HTTP', 'live_inference': False,
                     'source': 'https://ollama.com/library/gemma4', 'license': 'Apache-2.0 (Gemma 4 model card)',
                     'model_card': 'https://ai.google.dev/gemma/docs/core/model_card_4'}

    def available(self):
        try:
            with httpx.Client(base_url=self.base, timeout=3, transport=self.transport, trust_env=False) as client:
                response = client.get('/api/tags')
                response.raise_for_status()
                models = response.json().get('models', [])
                match = next((m for m in models if m.get('name') == self.model or m.get('model') == self.model), None)
                if not match:
                    raise GemmaError(f'{self.model} is not installed. Run ollama list, then pull the intended local Gemma 4 tag.')
                self.info.update({'digest': match.get('digest'), 'details': match.get('details', {})})
                return self.info
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise GemmaError(f'Ollama unavailable at {self.base}: {type(exc).__name__}. Start ollama serve and check ollama list.') from exc

    def recommend(self, dependency):
        self.available()
        conversation = messages(dependency)
        for attempt in range(2):
            try:
                with httpx.Client(base_url=self.base, timeout=self.timeout, transport=self.transport, trust_env=False) as client:
                    response = client.post('/api/chat', json={'model': self.model, 'messages': conversation,
                        'stream': False, 'format': Recommendation.model_json_schema(), 'think': False,
                        'options': {'temperature': 0.2, 'num_predict': 1800, 'num_ctx': 8192}, 'keep_alive': '5m'})
                    response.raise_for_status()
                    body = response.json()
                    if body.get('done') is False:
                        raise GemmaError('Ollama returned an incomplete generation.')
                    parsed = Recommendation.model_validate_json(body['message']['content'])
                    self.info.update({'live_inference': True, 'response_model': body.get('model'), 'eval_count': body.get('eval_count')})
                    return parsed
            except (ValidationError, ValueError, KeyError, TypeError) as exc:
                if attempt == 1:
                    raise GemmaError(f'Gemma returned invalid structured JSON after two attempts ({type(exc).__name__}).') from exc
                conversation.append({'role': 'user', 'content': 'The previous response failed schema validation. Return only complete JSON matching the supplied schema, with verified=false.'})
            except httpx.TimeoutException as exc:
                raise GemmaError(f'Local inference timed out after {self.timeout:g}s. Use a smaller Gemma 4 tag or increase GEMMA_TIMEOUT (maximum 300).') from exc
            except httpx.HTTPError as exc:
                raise GemmaError(f'Ollama inference failed ({type(exc).__name__}); inspect server logs, model availability and free RAM.') from exc
