"""
Agent LLM grający w Monopoly przez LOKALNE LM Studio (wszystko zostaje lokalnie).

LM Studio wystawia API zgodne z OpenAI pod http://localhost:1234/v1. Ten agent
opisuje decyzję (zakup / wyjście z więzienia) jako prompt, prosi lokalny model
o odpowiedź w formacie JSON i parsuje ją — jak eksperymentalne środowiska typu T54,
gdzie LLM jest agentem ekonomicznym. Żadne dane nie opuszczają Twojego komputera.

Uruchomienie:
  1. W LM Studio wczytaj model i włącz „Local Server” (domyślnie port 1234).
  2. python3 examples/llm_demo.py       # LLM gra jedną partię przeciw botom

Gdy serwer LLM jest niedostępny, agent używa rozsądnej heurystyki (fallback),
więc nic się nie wywala.
"""
import json
import re
import urllib.request
import urllib.error

from .agent import Agent
from . import data


class LLMAgent(Agent):
    name = "LLM"

    def __init__(self, base="http://localhost:1234/v1", model="local-model",
                 temperature=0.2, timeout=30.0, fallback=True, verbose=False):
        self.base = base.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.fallback = fallback
        self.verbose = verbose
        self.cash_reserve = 120
        self.max_houses = 4
        self.trades = True
        self.default_value = 1
        self.group_value = dict(Agent.group_value)
        self._warned = False

    # ---- komunikacja z lokalnym LM Studio ----
    def check_connection(self):
        try:
            req = urllib.request.Request(self.base + "/models")
            with urllib.request.urlopen(req, timeout=5) as r:
                json.loads(r.read().decode("utf-8"))
            return True
        except Exception:
            return False

    def _chat(self, system, user):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": self.temperature,
            "max_tokens": 200,
        }
        req = urllib.request.Request(
            self.base + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        return d["choices"][0]["message"]["content"]

    @staticmethod
    def _extract_json(text):
        """Wyłuskuje pierwszy obiekt JSON z odpowiedzi modelu."""
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None

    def _decide(self, system, user, fallback_value):
        try:
            raw = self._chat(system, user)
            if self.verbose:
                print("  [LLM]", raw.strip()[:120])
            obj = self._extract_json(raw)
            if obj is not None:
                return obj
        except Exception as e:
            if not self._warned:
                print(f"  [LLM] brak połączenia z LM Studio ({e}); używam heurystyki.")
                self._warned = True
        return fallback_value

    # ---- hooki decyzyjne ----
    SYSTEM = ("Jesteś ekspertem strategiem Monopoly. Grasz, by wygrać: kupuj pola o wysokim "
              "ROI (pomarańczowe, czerwone, koleje), pilnuj płynności, dąż do monopoli. "
              "Odpowiadaj WYŁĄCZNIE zwartym obiektem JSON, bez komentarza.")

    def should_buy(self, game, me, pos):
        _, name, typ, group, price, rents, hcost, mort = game.sp(pos)
        if me.cash < price:
            return False
        completes = self._completes_group(game, me, pos)
        heuristic = super().should_buy(game, me, pos)
        user = (f"Stoję na polu '{name}' (grupa: {group or typ}, cena {price}). "
                f"Mam {me.cash} gotówki. Czy zakup domyka mój kolor: {completes}. "
                f"Runda {game.round}. Kupić? Odpowiedz JSON: "
                f'{{"buy": true|false, "reason": "krótko"}}')
        obj = self._decide(self.SYSTEM, user, {"buy": heuristic})
        return bool(obj.get("buy", heuristic))

    def leave_jail(self, game, me):
        default = super().leave_jail(game, me)
        user = (f"Jestem w więzieniu. Mam {me.cash} gotówki, kart wyjścia: {me.get_out_cards}. "
                f"Runda {game.round}. W późnej grze z zabudowanymi polami rywali warto zostać. "
                f'Wyjść? JSON: {{"leave": true|false}}')
        obj = self._decide(self.SYSTEM, user, {"leave": default})
        return bool(obj.get("leave", default))
