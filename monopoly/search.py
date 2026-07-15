"""
Agent oparty na przeszukiwaniu Monte Carlo (rollouts) — najsilniejszy bot.

Dla decyzji o zakupie agent KLONUJE bieżący stan gry i rozgrywa wiele szybkich
dogrywek dla obu wariantów (kup / nie kupuj), a następnie wybiera ten, który
daje wyższy odsetek wygranych. To rdzeń metody MCTS (symulacja + wybór akcji).
Wersja bazowa jest 1-plythowa (płaskie Monte Carlo na akcję); parametr `depth=2`
włącza płytkie rozgałęzienie drzewa decyzyjnego na kolejną decyzję zakupu.

Uwaga: agent jest kosztowny obliczeniowo (wiele pełnych dogrywek na decyzję),
dlatego nadaje się do pojedynków i małych turniejów, nie do symulacji 10k gier.
"""
import random
from .agent import Agent
from .strategies import ALL_STRATEGIES, OrangeRed
from . import data
from .engine import Game, Player

_ROLLOUT_POLICY = OrangeRed   # tania, przyzwoita polityka do dogrywek


def clone_game(game):
    """Płytki-głęboki klon stanu gry, gotowy do niezależnej dogrywki."""
    g = Game.__new__(Game)
    g.rng = random.Random()
    g.players = []
    for p in game.players:
        q = Player.__new__(Player)
        q.__dict__.update(p.__dict__)
        q.props = set(p.props)
        g.players.append(q)
    g.log = lambda *a, **k: None
    g.max_rounds = game.max_rounds
    g.start_cash = game.start_cash
    g.forced_auction = game.forced_auction
    g.allow_trades = game.allow_trades
    g.allow_mortgage = game.allow_mortgage
    g.goal = game.goal
    g.goal_winner = game.goal_winner
    g.owner = game.owner[:]
    g.houses = game.houses[:]
    g.mortgaged = game.mortgaged[:]
    g.bank_houses = game.bank_houses
    g.bank_hotels = game.bank_hotels
    g.chance = game.chance[:]
    g.chest = game.chest[:]
    g.chance_i = game.chance_i
    g.chest_i = game.chest_i
    g.group_pos = game.group_pos
    g.round = game.round
    return g


def _set_rollout_policies(g):
    pol = _ROLLOUT_POLICY()
    for p in g.players:
        p.strategy = pol


def rollout(g, cap=90):
    """Rozgrywa klon do końca tanimi politykami; zwraca index zwycięzcy."""
    _set_rollout_policies(g)
    while len(g.active_players()) > 1 and g.round < cap:
        g.round += 1
        for p in g.players:
            if p.bankrupt:
                continue
            if len(g.active_players()) <= 1:
                break
            g.take_turn(p)
            if g.goal:
                w = g.check_goal(p)
                if w is not None:
                    return w.index
    act = g.active_players()
    if len(act) <= 1:
        return act[0].index if act else -1
    return max(act, key=lambda p: g.net_worth(p)).index


def _auction_excluding(g, pos, exclude_idx):
    """Symuluje aukcję wśród pozostałych graczy (proponujący spasował)."""
    bids = []
    for p in g.active_players():
        if p.index == exclude_idx:
            continue
        val = min(p.strategy.auction_value(g, p, pos), p.cash)
        if val > 0:
            bids.append((val, p.index))
    if not bids:
        return
    bids.sort(reverse=True)
    win_val, win_idx = bids[0]
    second = bids[1][0] if len(bids) > 1 else 0
    price = max(1, min(win_val, second + 10))
    g.players[win_idx].cash -= price
    g.owner[pos] = win_idx
    g.players[win_idx].props.add(pos)


class MCTSAgent(Agent):
    """Agent Monte Carlo: wybiera zakup przez dogrywki. Parametr sims = liczba
    dogrywek na wariant, cap = maks. długość dogrywki."""
    name = "MCTS"

    def __init__(self, sims=14, cap=90):
        self.sims = sims
        self.cap = cap
        self.cash_reserve = 80
        self.max_houses = 4
        self.trades = True
        self.default_value = 1
        self.group_value = dict(Agent.group_value)

    def should_buy(self, game, me, pos):
        price = game.sp(pos)[4]
        if me.cash < price:
            return False
        my = me.index
        wins_buy = wins_pass = 0
        for _ in range(self.sims):
            g = clone_game(game)
            g.players[my].cash -= price
            g.owner[pos] = my
            g.players[my].props.add(pos)
            if rollout(g, self.cap) == my:
                wins_buy += 1
        for _ in range(self.sims):
            g = clone_game(game)
            if g.forced_auction:
                _auction_excluding(g, pos, my)
            if rollout(g, self.cap) == my:
                wins_pass += 1
        return wins_buy >= wins_pass


ALL_STRATEGIES.setdefault("mcts", MCTSAgent)
