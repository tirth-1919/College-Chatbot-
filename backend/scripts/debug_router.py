import sys, asyncio
sys.path.insert(0, ".")
from backend.app.core.config import settings
settings.AI_FREE_ONLY_MODE = False
from backend.app.ai.router import AIRouter
from backend.app.ai.credential_registry import credential_registry

class FakeResponse:
    content = "ok"
    input_tokens = 1; output_tokens = 1; total_tokens = 2
    latency_ms = 1.0; model_name = "fake"; provider_name = "fake"; raw_headers = {}

class StubAdapter:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key; self.DEFAULT_MODEL = "m"
    async def generate_response(self, model_name, **kw):
        print("ATTEMPT:", self.api_key, model_name)
        return FakeResponse()
    async def health_check(self, m=None): return True

AIRouter._adapter_for = lambda self, n, b=None, k=None: StubAdapter(api_key=k)

class FakeQuery:
    def __init__(self, items): self.items = items
    def join(self, *a): return self
    def filter(self, *a): return self
    def order_by(self, *a): return self
    def all(self): return self.items

class FakeProvider:
    provider_name = "gemini"; is_enabled = True; base_url = None; api_key_env = "GEMINI_API_KEY"

class FakeModel:
    provider = FakeProvider(); model_identifier = "gemini-3.7-flash"; is_enabled = True
    health_status = "HEALTHY"; consecutive_failures = 0
    requests_total = 0; requests_success = 0; requests_failed = 0
    rate_limit_429_count = 0; avg_latency_ms = 0.0; p95_latency_ms = 0.0
    supports_vision = False; id = "fake-model"; cooldown_until = None

class FakeDB:
    added = []
    def query(self, m): return FakeQuery([FakeModel()])
    def add(self, o): FakeDB.added.append(o)
    def commit(self): pass

r = AIRouter()
import traceback
try:
    res = asyncio.run(r.generate_response("hi", "", db=FakeDB()))
    print("RESULT:", res[:80])
except Exception:
    traceback.print_exc()
for l in FakeDB.added:
    print("LOG:", l.provider_name, l.error_type)
