"""_get deve reter em 429/5xx e voltar a 200, e desistir com BubbleAPIError se persistir.

Rodar: PYTHONPATH=src python tests/test_retry.py
"""
import httpx

from bubble_cli import api
from bubble_cli.api import BubbleAPIError, BubbleClient
from bubble_cli.config import Config


def _client(responses):
    """BubbleClient cujo transporte devolve a sequência dada de status codes."""
    seq = iter(responses)

    def handler(request):
        return httpx.Response(next(seq), json={"response": {"remaining": 0, "count": 0}})

    c = BubbleClient(Config(app_id="x", api_key="k"))
    c._client = httpx.Client(base_url="https://x.bubbleapps.io/api/1.1", transport=httpx.MockTransport(handler))
    return c


def test_retries_then_succeeds():
    c = _client([429, 503, 200])
    assert c.count("Thing") == 0  # não levanta; consumiu 3 respostas


def test_gives_up_after_max():
    c = _client([429] * (api.MAX_RETRIES + 1))
    try:
        c.count("Thing")
        assert False, "deveria ter levantado"
    except BubbleAPIError as e:
        assert "429" in str(e)


# time.sleep vira no-op no import para não esperar de verdade (rodando via pytest ou direto).
api.time.sleep = lambda *_: None

if __name__ == "__main__":
    test_retries_then_succeeds()
    test_gives_up_after_max()
    print("OK: retry em 429/5xx e desistência após MAX_RETRIES")
