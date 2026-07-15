"""
Uczenie ze wzmocnieniem (Reinforcement Learning) dla decyzji ZAKUPU w Monopoly.

Metoda: REINFORCE (policy gradient) z nagrodą terminalną (+1 za wygraną, 0 za przegraną)
i baseline (redukcja wariancji). Polityka to sigmoida z liniowej kombinacji cech stanu:
    P(kup) = sigmoid(w · cechy)
Agent gra self-play przeciw istniejącym botom; po każdej grze aktualizujemy wagi w kierunku
zwiększającym prawdopodobieństwo wygranej. To dokładnie podejście "Model-Free RL" z analizy.
"""
import math
import random
from . import data
from .strategies import Strategy, ALL_STRATEGIES

# Przybliżone częstości lądowań (z Monte Carlo) — jedna z cech wartości pola.
LANDING = [0.0] * 40
_freq = {0: 2.9, 5: 2.50, 15: 2.55, 25: 2.55, 35: 2.30,
         6: 2.30, 8: 2.28, 9: 2.30, 11: 2.29, 13: 2.30, 14: 2.36,
         16: 2.46, 18: 2.55, 19: 2.30, 21: 2.24, 23: 2.24, 24: 2.62,
         26: 2.30, 27: 2.28, 29: 2.20, 31: 2.24, 32: 2.20, 34: 2.10,
         37: 2.05, 39: 2.10, 1: 2.00, 3: 2.02, 12: 2.64, 28: 2.35}
for i in range(40):
    LANDING[i] = _freq.get(i, 2.2) / 2.6   # wyśrodkowane ~1.0

NF = 12   # liczba cech


def features(game, player, pos):
    """Wektor cech dla decyzji o zakupie pola `pos`."""
    _, name, typ, group, price, rents, hcost, mort = game.sp(pos)
    cash = player.cash
    completes = advances = tier = is_rail = is_util = 0.0
    if typ == data.PROPERTY:
        positions = game.group_pos[group]
        owned = sum(1 for p in positions if game.owner[p] == player.index)
        completes = 1.0 if owned == len(positions) - 1 else 0.0
        advances = 1.0 if owned >= 1 else 0.0
        tier = rents[3] / 1400.0
    elif typ == data.RAILROAD:
        is_rail = 1.0
        advances = game.num_railroads(player) / 4.0
        tier = 0.35
    elif typ == data.UTILITY:
        is_util = 1.0
        tier = 0.15
    active = game.active_players()
    total_cash = sum(p.cash for p in active) or 1
    afford = min(cash / max(price, 1), 3.0) / 3.0
    share = cash / total_cash
    phase = min(game.round, 50) / 50.0
    buffer = max(-1.0, min(1.0, (cash - price) / 1500.0))
    return [1.0, afford, completes, advances, tier, is_rail, is_util,
            LANDING[pos], share, phase, buffer, len(active) / 6.0]


def sigmoid(z):
    if z < -35:
        return 0.0
    if z > 35:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


class RLBuyStrategy(Strategy):
    """Strategia z wyuczoną polityką zakupu; reszta decyzji jak 'zrównoważony'."""
    name = "RL-ekspert"
    cash_reserve = 100
    max_houses = 4
    trades = True
    default_value = 1
    group_value = {"orange": 3, "red": 3, "lightblue": 2, "pink": 2, "rail": 2,
                   "yellow": 2, "green": 2, "darkblue": 2, "brown": 1, "util": 1}

    def __init__(self, weights, training=False, eps=0.0):
        self.w = weights
        self.training = training
        self.eps = eps
        self.episode = []

    def should_buy(self, game, player, pos):
        price = game.sp(pos)[4]
        if player.cash < price:
            return False
        f = features(game, player, pos)
        p = sigmoid(sum(wi * fi for wi, fi in zip(self.w, f)))
        if self.training:
            a = 1 if random.random() < p else 0
            if random.random() < self.eps:
                a = 1 - a
            self.episode.append((f, a, p))
            return bool(a)
        return p >= 0.5


def train(episodes=8000, n_players=4, lr=0.08, eval_every=1000, eval_games=400,
          seed=0, verbose=True):
    """Trening REINFORCE. Zwraca wyuczone wagi i krzywą uczenia."""
    rng = random.Random(seed)
    w = [0.0] * NF
    baseline = 0.7   # ~ średnia gęstej nagrody (0.6*1.0 + 0.4*(1/n))
    opp_keys = [k for k in ALL_STRATEGIES if k != "ostrozny"]  # różnorodni przeciwnicy
    curve = []

    for ep in range(1, episodes + 1):
        eps = max(0.02, 0.30 * (1 - ep / episodes))
        cur_lr = lr * (1 - 0.6 * ep / episodes)
        rl = RLBuyStrategy(w, training=True, eps=eps)
        # losowy skład i pozycja RL
        opps = [ALL_STRATEGIES[rng.choice(opp_keys)]() for _ in range(n_players - 1)]
        seat = rng.randrange(n_players)
        spec = []
        oi = 0
        for i in range(n_players):
            if i == seat:
                spec.append(("RL", rl))
            else:
                spec.append((f"O{i}", opps[oi])); oi += 1
        from .engine import Game
        game = Game(spec, seed=rng.randrange(1 << 30), max_rounds=250)
        res = game.play()
        # gęsta nagroda: udział w końcowym majątku (skorelowany z wygraną, gradient co grę)
        rl_player = next(p for p in game.players if p.strategy is rl)
        nets = {p.index: max(0, game.net_worth(p)) for p in game.players}
        total = sum(nets.values()) or 1
        share = nets[rl_player.index] / total
        win = 1.0 if res["winner"].strategy is rl else 0.0
        # premiuje zarówno akumulację majątku (share*n ~1.0 średnio), jak i zwycięstwo
        reward = 0.6 * share * n_players + 0.4 * win
        R = reward - baseline
        baseline += 0.01 * (reward - baseline)
        if rl.episode:
            scale = cur_lr * R / math.sqrt(len(rl.episode) + 1)
            for (f, a, p) in rl.episode:
                coef = (a - p) * scale
                for i in range(NF):
                    w[i] += coef * f[i]
            for i in range(NF):        # lekka regularyzacja L2 (hamuje ucieczkę biasu)
                w[i] -= cur_lr * 0.002 * w[i]

        if verbose and ep % eval_every == 0:
            wr = evaluate_policy(w, n_players, eval_games, rng.randrange(1 << 30))
            curve.append((ep, wr))
            base = 100.0 / n_players
            print(f"  epizod {ep:>6}: win-rate RL = {wr:5.1f}%  (baza {base:.1f}%)  "
                  f"[{'ucząc się' if wr>base else '...'}]")
    return w, curve


FIXED_PANEL = ["kolejowy", "monopolista", "agresor", "pomczerw", "luksusowy"]


import os
import json as _json

_TRAINED_W = None


def _trained_weights():
    global _TRAINED_W
    if _TRAINED_W is None:
        p = os.path.join(os.path.dirname(__file__), "rl_policy.json")
        with open(p) as f:
            _TRAINED_W = _json.load(f)["weights"]
    return _TRAINED_W


class RLExpert(RLBuyStrategy):
    """Wytrenowana polityka RL (greedy) jako gotowa strategia 'rl'."""
    name = "RL-ekspert"

    def __init__(self):
        super().__init__(_trained_weights(), training=False)


# rejestracja w globalnym rejestrze strategii
ALL_STRATEGIES.setdefault("rl", RLExpert)


def evaluate_policy(w, n_players, games, seed):
    """Greedy win-rate wyuczonej polityki vs STAŁY, silny panel (czysty pomiar)."""
    from .engine import Game
    rng = random.Random(seed)
    wins = 0
    for g in range(games):
        rl = RLBuyStrategy(w, training=False)
        panel = [ALL_STRATEGIES[FIXED_PANEL[i % len(FIXED_PANEL)]]()
                 for i in range(n_players - 1)]
        seat = g % n_players
        spec = []
        oi = 0
        for i in range(n_players):
            if i == seat:
                spec.append(("RL", rl))
            else:
                spec.append((f"O{i}", panel[oi])); oi += 1
        game = Game(spec, seed=rng.randrange(1 << 30), max_rounds=250)
        res = game.play()
        if res["winner"].strategy is rl:
            wins += 1
    return 100.0 * wins / games
