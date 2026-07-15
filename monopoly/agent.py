"""
API AGENTA — czysty interfejs do pisania własnych botów Monopoly.

Framework (silnik) steruje przebiegiem gry i wywołuje metody Twojego agenta, gdy
trzeba podjąć decyzję — dokładnie jak w Monopyly / MonopolySimulator. Wystarczy
odziedziczyć po `Agent` i nadpisać wybrane metody; reszta ma sensowne domyślne.

Punkty decyzyjne (hooki), które możesz nadpisać:
    should_buy(game, me, pos) -> bool          # kupić pole, na którym stoję?
    auction_value(game, me, pos) -> int        # ile maksymalnie licytować?
    build_priority(group) -> liczba            # priorytet budowy grupy (wyżej = pierwsze)
    leave_jail(game, me) -> bool               # wyjść z więzienia (zapłacić/kartą)?
    accepts_sale(game, me, pos, price) -> bool # przyjąć ofertę kupna mojego pola?

Parametry sterujące (atrybuty klasy lub instancji):
    cash_reserve   — bufor gotówki utrzymywany przed zakupami/budową
    max_houses     — do ilu domów budować (5 = do hoteli)
    trades         — czy agent w ogóle handluje
    group_value    — słownik grupa->waga (0..3); default_value dla brakujących

Zarejestruj własnego agenta funkcją register_agent("klucz", KlasaAgenta), a stanie
się dostępny wszędzie (symulacje, turnieje, laboratorium) jak wbudowane strategie.
"""
import queue
from .strategies import Strategy, ALL_STRATEGIES
from . import data


class Agent(Strategy):
    """Bazowa klasa agenta. Odziedzicz i nadpisz wybrane hooki (patrz nagłówek modułu)."""
    name = "Agent"
    cash_reserve = 150
    max_houses = 5
    trades = True
    default_value = 1
    group_value = {"orange": 2, "red": 2, "lightblue": 2, "pink": 2, "rail": 2,
                   "yellow": 2, "green": 2, "darkblue": 2, "brown": 1, "util": 1}


def register_agent(key, cls):
    """Dodaje agenta do globalnego rejestru (dostępny w run_sim/run_matrix/tournament)."""
    ALL_STRATEGIES[key] = cls
    return cls


def play_match(agents, seed=None, max_rounds=250, **cfg):
    """Rozgrywa jedną grę zadanymi instancjami agentów. Zwraca wynik silnika."""
    from .engine import Game
    spec = [(getattr(a, "name", f"A{i}"), a) for i, a in enumerate(agents)]
    return Game(spec, seed=seed, max_rounds=max_rounds, **cfg).play()


# ----------------------------------------------------------------------------
# Przykładowe agenty konfigurowalne (jak w opisywanych frameworkach)
# ----------------------------------------------------------------------------
class ThresholdAgent(Agent):
    """Konfigurowalny agent: rezerwa gotówki, limit ceny zakupu, unikane grupy.

    Przykład: ThresholdAgent(reserve=300, price_cap=200, avoid={"util","darkblue"})
    kupuje tylko tanie pola, omija spółki i granatowe, trzyma 300$ rezerwy.
    """
    name = "Threshold"

    def __init__(self, reserve=200, price_cap=None, avoid=None, max_houses=4,
                 focus=None):
        self.cash_reserve = reserve
        self.max_houses = max_houses
        self.price_cap = price_cap
        self.avoid = set(avoid or [])
        self.trades = True
        self.default_value = 1
        gv = dict(Agent.group_value)
        for g in self.avoid:
            gv[g] = 0
        for g in (focus or []):
            gv[g] = 3
        self.group_value = gv

    def should_buy(self, game, me, pos):
        price = game.sp(pos)[4]
        key = self._key(game, pos)
        if key in self.avoid:
            return self._completes_group(game, me, pos) and me.cash - price >= self.cash_reserve
        if self.price_cap is not None and price > self.price_cap:
            return False
        return super().should_buy(game, me, pos)

    def _key(self, game, pos):
        typ = game.sp(pos)[2]
        if typ == data.RAILROAD:
            return "rail"
        if typ == data.UTILITY:
            return "util"
        return game.sp(pos)[3]


class NoRailsAgent(ThresholdAgent):
    """Nigdy nie kupuje dworców — do testu hipotezy 'koleje są przereklamowane'."""
    name = "NoRails"

    def __init__(self):
        super().__init__(reserve=150, avoid={"rail", "util"})


class Cheapskate(ThresholdAgent):
    """Kupuje wyłącznie tanie pola (<= 160$) — strategia niskiego kapitału."""
    name = "Cheapskate"

    def __init__(self):
        super().__init__(reserve=100, price_cap=160, max_houses=4,
                         focus=["brown", "lightblue"])


# ----------------------------------------------------------------------------
# Agent zewnętrzny — decyzje dostarczane przez kolejki (pod serwer REST)
# ----------------------------------------------------------------------------
class ExternalAgent(Agent):
    """Agent, którego decyzje podejmuje zewnętrzny klient (np. bot przez REST API).

    Silnik, wywołując hook decyzyjny, wstawia 'żądanie' do req_q i BLOKUJE się na
    resp_q, czekając na decyzję z zewnątrz. Serwer czyta req_q i zwraca odpowiedź
    do resp_q. Obsługiwane zewnętrznie: zakup (buy) i wyjście z więzienia (jail);
    aukcje/budowa/handel działają automatycznie (można rozszerzyć analogicznie).
    """
    name = "External"

    def __init__(self, timeout=30.0):
        self.req_q = queue.Queue()
        self.resp_q = queue.Queue()
        self.timeout = timeout
        self.cash_reserve = 100
        self.max_houses = 5
        self.trades = True
        self.default_value = 1
        self.group_value = dict(Agent.group_value)

    def _ask(self, kind, ctx):
        self.req_q.put({"type": kind, **ctx})
        return self.resp_q.get(timeout=self.timeout)

    def should_buy(self, game, me, pos):
        s = game.sp(pos)
        if me.cash < s[4]:
            return False
        ans = self._ask("buy", {"pos": pos, "field": s[1], "price": s[4],
                                 "cash": me.cash, "group": self._grp(game, pos),
                                 "state": self._snapshot(game, me)})
        return bool(ans.get("buy") if isinstance(ans, dict) else ans)

    def leave_jail(self, game, me):
        ans = self._ask("jail", {"cash": me.cash, "cards": me.get_out_cards,
                                  "state": self._snapshot(game, me)})
        return bool(ans.get("leave") if isinstance(ans, dict) else ans)

    def auction_value(self, game, me, pos):
        """Ile bot chce maksymalnie licytować za pole na aukcji."""
        s = game.sp(pos)
        ans = self._ask("auction", {"pos": pos, "field": s[1], "price": s[4],
                                     "cash": me.cash, "group": self._grp(game, pos),
                                     "state": self._snapshot(game, me)})
        if isinstance(ans, dict):
            return max(0, min(int(ans.get("bid", 0)), me.cash))
        return max(0, min(int(ans or 0), me.cash))

    def accepts_sale(self, game, me, pos, price):
        """Czy bot przyjmuje ofertę odkupienia SWOJEGO pola za `price`."""
        s = game.sp(pos)
        ans = self._ask("sell", {"pos": pos, "field": s[1], "offer": price,
                                  "price": s[4], "cash": me.cash,
                                  "group": self._grp(game, pos),
                                  "state": self._snapshot(game, me)})
        return bool(ans.get("accept") if isinstance(ans, dict) else ans)

    def _snapshot(self, game, me):
        return {
            "round": game.round,
            "me": {"cash": me.cash, "pos": me.pos, "in_jail": me.in_jail,
                   "props": sorted(me.props)},
            "players": [{"name": p.name, "cash": p.cash, "props": len(p.props),
                         "bankrupt": p.bankrupt} for p in game.players],
            "owner": list(game.owner), "houses": list(game.houses),
        }

    def _grp(self, game, pos):
        typ = game.sp(pos)[2]
        if typ == data.RAILROAD:
            return "rail"
        if typ == data.UTILITY:
            return "util"
        return game.sp(pos)[3]
