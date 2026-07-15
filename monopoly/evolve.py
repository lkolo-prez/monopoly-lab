"""
Ewolucyjny trener self-play (Cross-Entropy Method) — "trenuje własny model Monopoly".

Optymalizuje pełny wektor parametrów strategii (wagi 10 grup + rezerwa gotówki +
poziom budowy + próg siedzenia w więzieniu), maksymalizując win-rate przeciw
STAŁEMU, silnemu panelowi botów. To bezpośrednio wypracowuje najlepszy "schemat" gry.

CEM: utrzymujemy rozkład (średnia + odchylenie) nad genomem; co pokolenie losujemy
populację, oceniamy, zostawiamy elitę i przesuwamy rozkład ku niej. Zapisuje
mistrza do evolved_champion.json (wznawialne — kolejny start kontynuuje trening).
"""
import os
import json
import math
import random

from .strategies import Strategy, ALL_STRATEGIES

KEYS = ["brown", "lightblue", "pink", "orange", "red", "yellow",
        "green", "darkblue", "rail", "util"]
DIM = len(KEYS) + 3   # +rezerwa, +max_houses, +jail_threshold
CHAMPION_FILE = os.path.join(os.path.dirname(__file__), "evolved_champion.json")

# panel treningowy (dla starej, jednopanelowej metryki fitness)
PANEL = ["kolejowy", "monopolista", "pomczerw"]

# wielopanelowe, wielo-osobowe konfiguracje treningowe (anty-przeuczenie).
# Każda: (lista przeciwników, liczba graczy). Champion mierzony przewagą nad bazą.
CONFIGS = [
    (["kolejowy", "monopolista", "pomczerw"], 4),
    (["luksusowy", "agresor", "ekonom"], 4),
    (["kolejowy", "luksusowy", "monopolista", "pomczerw"], 5),
    (["rl", "agresor", "kolejowy", "ekonom", "luksusowy"], 6),
]


class EvolvedStrategy(Strategy):
    """Strategia zdekodowana z genomu (ciągły wektor parametrów)."""
    name = "Champion"

    def __init__(self, genome=None):
        if genome is None:
            genome = load_champion() or default_genome()
        self.genome = list(genome)
        self.group_value = {k: max(0.0, min(3.0, genome[i]))
                            for i, k in enumerate(KEYS)}
        self.cash_reserve = int(max(0, min(600, genome[len(KEYS)])))
        self.max_houses = int(max(3, min(5, round(genome[len(KEYS) + 1]))))
        self.jail_thr = genome[len(KEYS) + 2]
        self.trades = True
        self.default_value = 1

    def leave_jail(self, game, player):
        if game.round < self.jail_thr:
            return True
        danger = any(game.houses[p] > 0 and game.owner[p] not in (None, player.index)
                     for p in range(40))
        return not danger


def default_genome():
    # warm-start z silnej strategii "kolejowej" (koleje + pomarańcze)
    gv = {"rail": 3, "util": 2, "orange": 3, "red": 2, "lightblue": 2,
          "pink": 2, "yellow": 1, "green": 1, "darkblue": 1, "brown": 1}
    return [gv[k] for k in KEYS] + [100, 5, 15]


def make_strategy(genome):
    return EvolvedStrategy(genome)


def fitness(genome, games, players=4, seed=0, max_rounds=200):
    """Win-rate genomu przeciw panelowi (naprzemienne pozycje)."""
    from .engine import Game
    rng = random.Random(seed)
    wins = 0
    for g in range(games):
        champ = EvolvedStrategy(genome)
        panel = [ALL_STRATEGIES[PANEL[i % len(PANEL)]]()
                 for i in range(players - 1)]
        seat = g % players
        spec, oi = [], 0
        for i in range(players):
            if i == seat:
                spec.append(("Champ", champ))
            else:
                spec.append((f"P{i}", panel[oi])); oi += 1
        res = Game(spec, seed=rng.randrange(1 << 30), max_rounds=max_rounds).play()
        if res["winner"].strategy is champ:
            wins += 1
    return 100.0 * wins / games


def fitness_multi(genome, games_per, seed=0, max_rounds=200):
    """Średnia przewaga nad bazą (pkt%) po wszystkich CONFIGS — odporna metryka."""
    from .engine import Game
    total = 0.0
    for ci, (panel_keys, players) in enumerate(CONFIGS):
        rng = random.Random(seed * 131 + ci * 17)
        wins = 0
        for g in range(games_per):
            champ = EvolvedStrategy(genome)
            panel = [ALL_STRATEGIES[panel_keys[i % len(panel_keys)]]()
                     for i in range(players - 1)]
            seat = g % players
            spec, oi = [], 0
            for i in range(players):
                if i == seat:
                    spec.append(("Champ", champ))
                else:
                    spec.append((f"P{i}", panel[oi])); oi += 1
            res = Game(spec, seed=rng.randrange(1 << 30), max_rounds=max_rounds).play()
            if res["winner"].strategy is champ:
                wins += 1
        total += (100.0 * wins / games_per) - (100.0 / players)   # przewaga nad bazą
    return total / len(CONFIGS)


def _sample(mean, std, rng):
    return [mean[i] + std[i] * rng.gauss(0, 1) for i in range(DIM)]


def cem(generations=20, pop=24, elite_frac=0.30, games=180, players=4,
        seed=0, resume=True, log=print):
    rng = random.Random(seed)
    if resume and os.path.exists(CHAMPION_FILE):
        data = json.load(open(CHAMPION_FILE))
        mean = data.get("mean", data["genome"])
        best_genome, best_fit = data["genome"], -1   # metryka = przewaga, re-ewaluuj
        log("Wznawiam z zapisanego mistrza (warm-start genomu).")
    else:
        mean = default_genome()
        best_genome, best_fit = list(mean), -1
    std = [0.8] * len(KEYS) + [120.0, 0.8, 8.0]
    n_elite = max(2, int(pop * elite_frac))
    curve = []

    for gen in range(1, generations + 1):
        pop_genomes = [list(mean)] + [_sample(mean, std, rng) for _ in range(pop - 1)]
        scored = []
        for gi, genome in enumerate(pop_genomes):
            f = fitness_multi(genome, games, seed=seed * 1000 + gen * 37 + gi)
            scored.append((f, genome))
        scored.sort(key=lambda x: x[0], reverse=True)
        elite = [g for _, g in scored[:n_elite]]
        mean = [sum(g[i] for g in elite) / n_elite for i in range(DIM)]
        std = [max(_floor(i), _std([g[i] for g in elite], mean[i]))
               for i in range(DIM)]
        # stabilna re-ewaluacja lidera (więcej gier -> mniej szumu w best)
        lead_fit = fitness_multi(scored[0][1], games * 3,
                                 seed=seed * 7 + gen)
        avg_fit = sum(f for f, _ in scored) / len(scored)
        if lead_fit > best_fit:
            best_fit, best_genome = lead_fit, list(scored[0][1])
            _save(best_genome, mean, best_fit)
        curve.append((gen, best_fit, avg_fit))
        log(f"  pok. {gen:>3}: lider +{scored[0][0]:4.1f}  re-eval +{lead_fit:4.1f}  "
            f"best +{best_fit:4.1f} pkt% nad bazą  śr. +{avg_fit:4.1f}")
    _save(best_genome, mean, best_fit)
    return best_genome, best_fit, curve


def _floor(i):
    # minimalne odchylenie, by nie zamrozić eksploracji
    return 0.15 if i < len(KEYS) else (25.0 if i == len(KEYS) else (0.25 if i == len(KEYS) + 1 else 2.0))


def _std(vals, m):
    return math.sqrt(sum((v - m) ** 2 for v in vals) / max(1, len(vals)))


def _save(genome, mean, fit):
    json.dump({"genome": genome, "mean": mean, "fitness": fit,
               "keys": KEYS, "layout": "gv[10]+reserve+max_houses+jail_thr"},
              open(CHAMPION_FILE, "w"), indent=2)


def load_champion():
    if os.path.exists(CHAMPION_FILE):
        return json.load(open(CHAMPION_FILE))["genome"]
    return None


# rejestracja mistrza jako strategii "champion" (jeśli wytrenowany)
if os.path.exists(CHAMPION_FILE):
    ALL_STRATEGIES.setdefault("champion", EvolvedStrategy)
