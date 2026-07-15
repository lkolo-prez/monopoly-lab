"""
Strategie AI dla graczy Monopoly.

group_value: jak bardzo strategia pożąda danej grupy (0..3)
  3 = priorytet, 2 = chcę, 1 = kupię gdy dużo gotówki, 0 = tylko dla kompletu

Wnioski z analizy prawdopodobieństw pól (najczęściej odwiedzane po wyjściu
z więzienia): pomarańczowe i czerwone są statystycznie najlepsze, jasnoniebieskie
mają świetny zwrot z inwestycji, koleje dają wczesny dochód, spółki są słabe.
"""
from . import data


def group_key(game, pos):
    typ = game.sp(pos)[2]
    if typ == data.RAILROAD:
        return "rail"
    if typ == data.UTILITY:
        return "util"
    return game.sp(pos)[3]


class Strategy:
    name = "Bazowa"
    cash_reserve = 150
    max_houses = 5          # 5 = do hoteli
    trades = True
    group_value = {}
    default_value = 1

    def gv(self, key):
        return self.group_value.get(key, self.default_value)

    def _completes_group(self, game, player, pos):
        group = game.sp(pos)[3]
        if group in (None, "rail", "util"):
            return False
        positions = game.group_pos.get(group, [])
        owned = sum(1 for p in positions if game.owner[p] == player.index)
        return owned == len(positions) - 1

    def should_buy(self, game, player, pos):
        price = game.sp(pos)[4]
        key = group_key(game, pos)
        val = self.gv(key)
        completes = self._completes_group(game, player, pos)
        if completes:
            val = 3
        if val >= 3:
            return player.cash - price >= min(self.cash_reserve, 50)
        if val >= 2:
            return player.cash - price >= self.cash_reserve
        if val >= 1:
            return player.cash - price >= self.cash_reserve + 150
        # val 0: kupuj tylko dla natychmiastowego kompletu
        return completes and player.cash - price >= self.cash_reserve

    def auction_value(self, game, player, pos):
        price = game.sp(pos)[4]
        key = group_key(game, pos)
        val = self.gv(key)
        if self._completes_group(game, player, pos):
            val = 3
        if val >= 3:
            bid = int(price * 1.3)
        elif val >= 2:
            bid = price
        elif val >= 1:
            bid = int(price * 0.6)
        else:
            bid = int(price * 0.3)
        # nie schodź poniżej rezerwy
        return min(bid, max(0, player.cash - self.cash_reserve // 2))

    def build_priority(self, group):
        return self.group_value.get(group, self.default_value)

    def leave_jail(self, game, player):
        # późna gra z zabudowanymi monopolami: zostań w więzieniu (obrona)
        danger = any(
            game.houses[p] > 0 and game.owner[p] not in (None, player.index)
            for p in range(40)
        )
        if game.round < 15 or not danger:
            return True
        return False

    def accepts_sale(self, game, player, pos, price):
        # warunki wstępne sprawdza silnik; tu tylko rozsądny próg ceny
        base = game.sp(pos)[4]
        return price >= base or player.cash < self.cash_reserve


class AggressiveBuyer(Strategy):
    name = "Agresor"
    cash_reserve = 50
    max_houses = 5
    default_value = 2
    group_value = {"orange": 3, "red": 3, "lightblue": 2, "rail": 2,
                   "pink": 2, "yellow": 2, "green": 2, "darkblue": 2,
                   "brown": 1, "util": 1}


class OrangeRed(Strategy):
    name = "Pomaranczowo-czerwony"
    cash_reserve = 150
    max_houses = 5
    default_value = 1
    group_value = {"orange": 3, "red": 3, "lightblue": 3, "pink": 2,
                   "rail": 2, "yellow": 1, "green": 1, "darkblue": 1,
                   "brown": 1, "util": 0}


class Conservative(Strategy):
    name = "Ostrozny"
    cash_reserve = 400
    max_houses = 3          # zatrzymuje się na 3 domach (najlepszy ROI)
    default_value = 1
    group_value = {"orange": 2, "red": 2, "lightblue": 2, "pink": 2,
                   "yellow": 2, "green": 2, "rail": 1, "darkblue": 1,
                   "brown": 1, "util": 0}

    def leave_jail(self, game, player):
        # ostrożny lubi siedzieć w więzieniu w środku/końcu gry
        if game.round < 12:
            return True
        danger = any(game.houses[p] > 0 and game.owner[p] not in (None, player.index)
                     for p in range(40))
        return not danger


class RailBaron(Strategy):
    name = "Kolejowy"
    cash_reserve = 100
    max_houses = 5
    default_value = 1
    group_value = {"rail": 3, "util": 2, "orange": 3, "red": 2,
                   "lightblue": 2, "pink": 2, "yellow": 1, "green": 1,
                   "darkblue": 1, "brown": 1}


class Monopolist(Strategy):
    name = "Monopolista"
    cash_reserve = 200
    max_houses = 4
    default_value = 2
    group_value = {"orange": 3, "red": 3, "pink": 3, "lightblue": 2,
                   "yellow": 2, "green": 2, "darkblue": 2, "rail": 2,
                   "brown": 1, "util": 0}


class Ekonom(Strategy):
    """Tanie komplety: brąz, jasnoniebieskie, koleje — szybkie, tanie monopole."""
    name = "Ekonom"
    cash_reserve = 100
    max_houses = 4
    default_value = 1
    group_value = {"brown": 3, "lightblue": 3, "rail": 3, "pink": 2,
                   "orange": 2, "util": 1, "red": 1, "yellow": 1,
                   "green": 0, "darkblue": 0}


class Luksusowy(Strategy):
    """Drogie, wysokoczynszowe: zielone i granatowe — gra na późną eksplozję czynszu."""
    name = "Luksusowy"
    cash_reserve = 300
    max_houses = 5
    default_value = 1
    group_value = {"green": 3, "darkblue": 3, "yellow": 2, "red": 2,
                   "orange": 2, "rail": 1, "pink": 1, "lightblue": 1,
                   "brown": 0, "util": 0}


ALL_STRATEGIES = {
    "agresor": AggressiveBuyer,
    "pomczerw": OrangeRed,
    "ostrozny": Conservative,
    "kolejowy": RailBaron,
    "monopolista": Monopolist,
    "ekonom": Ekonom,
    "luksusowy": Luksusowy,
}

# Rejestracja wytrenowanych modeli ("rl", "champion") — import kołowy bezpieczny,
# bo Strategy i ALL_STRATEGIES są już zdefiniowane powyżej.
try:
    from . import rl as _rl_register  # noqa: F401
except Exception:
    pass
try:
    from . import evolve as _evolve_register  # noqa: F401  (rejestruje "champion")
except Exception:
    pass
