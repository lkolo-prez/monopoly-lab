"""
Agent HYBRYDOWY — recepta z pracy Purdue ("Learning Monopoly Gameplay: A Hybrid
Model-Free Deep RL"): tania, stała polityka dla częstych/prostych decyzji + kosztowne
przeszukiwanie dla rzadkich/złożonych. Rozwiązuje problem skośnego rozkładu akcji.

Tutaj:
  • baza = wytrenowany ewolucyjnie CHAMPION (szybka polityka: budowa, aukcje, więzienie,
    większość zakupów),
  • dla decyzji KLUCZOWYCH o zakupie (domknięcie monopolu lub cenne pole przy napiętej
    gotówce) uruchamiamy przeszukiwanie Monte Carlo (dogrywki) i wybieramy lepszy wariant.

To „hierarchiczne" podejście: najpierw rozstrzygamy, CZY decyzja jest kluczowa (tanio),
a dopiero potem — jeśli tak — płacimy za głębsze przeszukanie.
"""
from .evolve import EvolvedStrategy, load_champion, default_genome
from .search import clone_game, rollout, _auction_excluding
from .strategies import ALL_STRATEGIES
from . import data


class HybridAgent(EvolvedStrategy):
    name = "Hybrid"

    def __init__(self, sims=18, cap=90):
        super().__init__(load_champion() or default_genome())
        self.sims = sims
        self.cap = cap

    def _key(self, game, pos):
        t = game.sp(pos)[2]
        if t == data.RAILROAD:
            return "rail"
        if t == data.UTILITY:
            return "util"
        return game.sp(pos)[3]

    def _pivotal(self, game, me, pos):
        """Czy decyzja jest złożona/kluczowa (warta przeszukania)?"""
        if self._completes_group(game, me, pos):
            return True
        gv = self.group_value.get(self._key(game, pos), self.default_value)
        price = game.sp(pos)[4]
        # cenne pole, którego zakup naprawdę napina płynność
        return gv >= 2.3 and (me.cash - price) < self.cash_reserve * 1.6

    def should_buy(self, game, me, pos):
        price = game.sp(pos)[4]
        if me.cash < price:
            return False
        if not self._pivotal(game, me, pos):
            return super().should_buy(game, me, pos)     # szybka polityka championa
        # przeszukiwanie MCTS tylko dla decyzji kluczowej
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


ALL_STRATEGIES.setdefault("hybrid", HybridAgent)
