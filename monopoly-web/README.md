# 🎩 Monopoly Lab — lokalne laboratorium analityczne Monopoly

Kompletne, wielozakładkowe narzędzie w przeglądarce: nie tylko grywalne Monopoly z analizą
„jak w szachach", ale **pełna analiza funkcjonalna gry** — symulacje, wizualizacje, wnioski.
Działa w 100% lokalnie (JavaScript), bez internetu i bez serwera.

**🔗 Wersja online (udostępnialna):** https://claude.ai/code/artifact/64b350cd-d449-49eb-8a77-e1c7e6b7f7c0

## ▶ Jak uruchomić lokalnie
```bash
open index.html          # macOS (albo dwuklik w Finderze)
```

## 🗂️ Pięć zakładek

### 🎮 Gra & Analiza
Grasz przeciw botom (lub obserwujesz same boty) z **oceną pozycji na żywo**:
- **Pasek oceny (Monte Carlo)** — realne szanse każdego gracza, setki dogrywek z bieżącego stanu.
- **Wykres przewagi** w czasie · **adnotacje ruchów** (`!!` / `?` / `??`) · rekomendacja silnika.
- **Metryki ryzyka**: bufor płynności, udział w rynku, bliskość kompletów, dworce/spółki, postęp celu.
- **🧭 Plan silnika (2-ply)** — „domknij komplet A (+X%) → potem B (+Y%) → broń się przed Z".
- **🕵️ Wywiad** — auto-detekcja strategii przeciwników i ich zagrożeń.
- **🤝 Handel** oceniany silnikiem (przyjmie / odrzuci / **kontra** z żądaniem dopłaty — *side-payment*).
- **📋 Analiza po grze** (Game Review) — celność decyzji, największe błędy, punkty zwrotne.
- **Tryby Szybkie NEW Monopoly**: Real Estate Agent, Magnate, Architect, Hotel Manager, Town Planner, Landowner.

### 🗺️ Analiza planszy
- **Heatmapa planszy** (Monte Carlo liczony na żywo): przełączasz między częstotliwością lądowań,
  czynszem hotelowym i ROI grupy. Widać, że Więzienie (~22%) to magnes, a pomarańczowe/czerwone są najgorętsze.
- Wykresy: **Top 12 pól** i **ROI grup** (model Markowa).

### 🧪 Laboratorium symulacji
- Wybierasz strategie, liczbę graczy (2–6), kapitał, cel i liczbę gier (do 6000).
- Silnik rozgrywa je **w przeglądarce** i pokazuje: **win-rate**, **odsetek bankructw**,
  **histogram długości gier** i odsetek gier w „paradoksie nieskończonej gry".

### ♟️ Strategie
- **Macierz priorytetów** — jak każdy z 9 botów wycenia każdą grupę (0–3), rezerwa, poziom budowy.
- Profile strategii, w tym **RL (self-play)** wyuczony w Pythonie.

### 📚 Wiedza
Zwięzła, oparta na źródłach analiza: łańcuch Markowa, ROI grup, zasady które decydują,
wyniki 22 500+ symulacji, uczciwy wynik eksperymentu RL i jak działa silnik oceny.

## 🗂️ Pliki
- `index.html` — całe „Monopoly Lab" (otwórz to lokalnie).
- `engine.core.js` — silnik gry + AI (9 strategii) + ewaluator Monte Carlo + `landingFrequency` + `batchSim`
  (działa też w Node — testy headless przez stub DOM).
- `artifact.html` — wersja jednoplikowa (silnik wklejony inline) do publikacji online.

## 🧪 Bot RL
Strategia „RL (self-play)" ma politykę zakupu wyuczoną w Pythonie (`train_rl.py`, REINFORCE, 12 000 gier).
Uczciwy wynik: osiąga **parytet** z najlepszymi botami ręcznymi, ale **bije naiwnego Agresora 55:45** —
nauczyła się dyscypliny płynności. Zgodne z literaturą: model-free RL na samej decyzji zakupu plateauuje.
