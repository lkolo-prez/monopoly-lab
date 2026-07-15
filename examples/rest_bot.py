#!/usr/bin/env python3
"""
Przykładowy zewnętrzny bot grający przez REST API (biblioteka standardowa).

Uruchom najpierw serwer:   python3 server.py
Potem tego bota:           python3 examples/rest_bot.py

Bot pokazuje, jak podjąć decyzje 'buy' i 'jail' na podstawie stanu gry.
Zamień logikę w decide() na własną strategię / model AI.
"""
import json
import urllib.request

BASE = "http://localhost:8777"


def post(path, payload):
    req = urllib.request.Request(BASE + path,
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


def decide(request):
    """Twoja logika bota. Zwraca słownik decyzji dla danego żądania."""
    t = request["type"]
    if t == "buy":
        # prosta zasada: kup, jeśli po zakupie zostanie >= 150$ rezerwy,
        # albo pole domyka kolor (silnik i tak liczy to w metrykach)
        keep = request["cash"] - request["price"]
        good_group = request["group"] in ("orange", "red", "lightblue", "rail")
        return {"buy": keep >= (100 if good_group else 250)}
    if t == "jail":
        return {"leave": True}   # wychodzimy jak najszybciej
    if t == "auction":
        # licytuj do ceny bazowej dla dobrych grup, inaczej pas
        good = request["group"] in ("orange", "red", "rail", "lightblue")
        return {"bid": request["price"] if good else 0}
    if t == "sell":
        # sprzedaj swoje pole tylko za hojną ofertę (>= 1.8x ceny bazowej)
        return {"accept": request["offer"] >= request.get("price", 1e9) * 1.8}
    return {}


def main():
    resp = post("/game/new", {"opponents": ["kolejowy", "pomczerw", "monopolista"]})
    gid = resp["game_id"]
    print(f"Gra {gid} rozpoczęta.")
    steps = 0
    while "request" in resp:
        req = resp["request"]
        decision = decide(req)
        if req["type"] == "buy":
            s = req["state"]["me"]
            print(f"  [buy] {req['field']} ({req['price']}$) cash={req['cash']} "
                  f"-> {'KUP' if decision.get('buy') else 'PAS'}")
        resp = post(f"/game/{gid}/action", decision)
        steps += 1
        if steps > 2000:
            break
    if "game_over" in resp:
        r = resp["game_over"]
        print(f"\nKONIEC: zwycięzca {r['winner']} [{r['winner_strategy']}], "
              f"{r['rounds']} rund.")
        for row in r["ranking"]:
            print(f"  {row['name']:<16} majątek {row['net_worth']:>6} "
                  f"{'BANKRUT' if row['bankrupt'] else ''}")


if __name__ == "__main__":
    main()
