#!/usr/bin/env python3
"""
Serwer REST — podłącz własnego bota (dowolny język) do silnika Monopoly.

Bez zależności zewnętrznych (tylko biblioteka standardowa). Uruchom:
    python3 server.py                 # start na http://localhost:8777

Endpointy:
  GET  /                      — strona informacyjna
  GET  /board/landing         — częstotliwości lądowań (Monte Carlo)
  POST /simulate              — masowa symulacja strategii -> win-rate
       body: {"strategies":["agresor","kolejowy"], "games":1000, "players":4, "start_cash":1500}
  POST /game/new              — nowa gra z Twoim botem (seat 0) + wbudowane boty
       body: {"opponents":["kolejowy","pomczerw"], "max_rounds":250}
       -> {"game_id": "...", "request": {...}}  (pierwsza decyzja do podjęcia)
  POST /game/<id>/action      — prześlij decyzję, dostań kolejne żądanie lub wynik
       body dla żądania typu "buy":  {"buy": true|false}
       body dla żądania typu "jail": {"leave": true|false}
       -> {"request": {...}}  lub  {"game_over": {...}}

Pętla klienta: /game/new -> czytaj 'request' -> POST /action z decyzją ->
czytaj kolejny 'request' -> ... aż dostaniesz 'game_over'.
Przykładowy klient: examples/rest_bot.py
"""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from monopoly.engine import Game
from monopoly.strategies import ALL_STRATEGIES
from monopoly.agent import ExternalAgent
import monopoly.agent  # noqa (rejestracja agentów)

GAMES = {}   # game_id -> {"agent": ExternalAgent, "thread": Thread, "result": dict|None}


def serialize_result(res):
    return {
        "winner": res["winner"].name,
        "winner_strategy": res["winner_strategy"],
        "rounds": res["rounds"],
        "finished": res["finished"],
        "ranking": [{"name": n, "strategy": s, "net_worth": w, "bankrupt": b}
                    for (n, s, w, b) in res["ranking"]],
    }


def start_external_game(opponents, max_rounds):
    gid = uuid.uuid4().hex[:10]
    ext = ExternalAgent()
    spec = [("TwójBot", ext)]
    for i, k in enumerate(opponents):
        cls = ALL_STRATEGIES.get(k)
        if cls is None:
            raise ValueError(f"nieznana strategia: {k}")
        spec.append((f"{k}-{i}", cls()))
    game = Game(spec, seed=None, max_rounds=max_rounds)

    def run():
        res = game.play()
        GAMES[gid]["result"] = serialize_result(res)
        ext.req_q.put({"type": "game_over"})

    th = threading.Thread(target=run, daemon=True)
    GAMES[gid] = {"agent": ext, "thread": th, "result": None}
    th.start()
    req = ext.req_q.get(timeout=30)
    return gid, _wrap(gid, req)


def _wrap(gid, req):
    if req.get("type") == "game_over":
        return {"game_id": gid, "game_over": GAMES[gid]["result"]}
    return {"game_id": gid, "request": req}


def submit_action(gid, decision):
    g = GAMES.get(gid)
    if g is None:
        return {"error": "nieznane game_id"}
    ext = g["agent"]
    ext.resp_q.put(decision)
    req = ext.req_q.get(timeout=30)
    return _wrap(gid, req)


def landing_frequency(steps=300000):
    from analyze_board import monte_carlo
    land = monte_carlo(steps)
    tot = sum(land) or 1
    from monopoly import data
    return [{"pos": i, "name": data.BOARD[i][1], "group": data.BOARD[i][3],
             "freq_pct": round(100 * land[i] / tot, 3)} for i in range(40)]


def simulate(strategies, games, players, start_cash):
    from collections import defaultdict
    wins = defaultdict(int)
    played = defaultdict(int)
    R = len(strategies)
    for g in range(games):
        seats = [strategies[(g + i) % R] for i in range(players)]
        spec = [(f"{k}#{i}", ALL_STRATEGIES[k]()) for i, k in enumerate(seats)]
        res = Game(spec, seed=g, max_rounds=250).play()
        for k in seats:
            played[k] += 1
        wins[res["winner_strategy"]] += 1
    name2key = {ALL_STRATEGIES[k]().name: k for k in set(strategies)}
    out = {}
    for k in set(strategies):
        w = wins.get(ALL_STRATEGIES[k]().name, 0)
        out[k] = {"win_pct": round(100 * w / max(1, played[k]), 1),
                  "games_played": played[k]}
    return {"games": games, "players": players, "results": out}


INFO_HTML = """<!doctype html><meta charset=utf-8><title>Monopoly REST</title>
<body style="font:15px system-ui;max-width:720px;margin:40px auto;color:#222">
<h1>🎩 Monopoly — serwer REST</h1>
<p>Podłącz własnego bota. Zobacz nagłówek <code>server.py</code> po listę endpointów.</p>
<ul>
<li><b>POST /game/new</b> — nowa gra z Twoim botem</li>
<li><b>POST /game/&lt;id&gt;/action</b> — decyzja bota</li>
<li><b>POST /simulate</b> — masowa symulacja</li>
<li><b>GET /board/landing</b> — częstotliwości lądowań</li>
</ul>
<p>Przykładowy klient: <code>python3 examples/rest_bot.py</code></p></body>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = (obj if isinstance(obj, (bytes, str)) else json.dumps(obj, ensure_ascii=False)).encode("utf-8") \
            if not isinstance(obj, bytes) else obj
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8" if isinstance(obj, str)
                         else "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

    def do_GET(self):
        try:
            if self.path == "/" or self.path.startswith("/index"):
                return self._send(INFO_HTML)
            if self.path.startswith("/board/landing"):
                return self._send({"landing": landing_frequency()})
            return self._send({"error": "nieznany endpoint"}, 404)
        except Exception as e:
            return self._send({"error": str(e)}, 500)

    def do_POST(self):
        try:
            body = self._body()
            if self.path == "/simulate":
                return self._send(simulate(
                    body.get("strategies", ["agresor", "kolejowy", "pomczerw", "monopolista"]),
                    int(body.get("games", 1000)), int(body.get("players", 4)),
                    int(body.get("start_cash", 1500))))
            if self.path == "/game/new":
                gid, resp = start_external_game(
                    body.get("opponents", ["kolejowy", "pomczerw", "monopolista"]),
                    int(body.get("max_rounds", 250)))
                return self._send(resp)
            if self.path.startswith("/game/") and self.path.endswith("/action"):
                gid = self.path.split("/")[2]
                return self._send(submit_action(gid, body))
            return self._send({"error": "nieznany endpoint"}, 404)
        except Exception as e:
            return self._send({"error": str(e)}, 500)

    def log_message(self, *a):
        pass   # cisza


def main(port=8777):
    srv = ThreadingHTTPServer(("localhost", port), Handler)
    print(f"Monopoly REST na http://localhost:{port}  (Ctrl+C aby zatrzymać)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nZatrzymano.")


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8777)
