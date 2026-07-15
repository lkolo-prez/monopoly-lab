# 🎩 Monopoly Lab — symulator, silnik AI i wytrenowany model

> 🌐 **Demo na żywo (GitHub Pages):** https://lkolo-prez.github.io/monopoly-lab/ &nbsp;·&nbsp;
> 🎮 [Monopoly Lab](https://lkolo-prez.github.io/monopoly-lab/monopoly-web/index.html) &nbsp;·&nbsp;
> 📊 [Statystyki](https://lkolo-prez.github.io/monopoly-lab/monopoly-web/stats.html)

Kompletny silnik Monopoly w czystym Pythonie (bez zależności zewnętrznych), który:

1. **implementuje pełne klasyczne zasady** (plansza 40 pól, karty Szansa/Kasa,
   więzienie, aukcje, budowa domów/hoteli, hipoteki, handel, bankructwo),
2. zawiera **5 różnych strategii AI**,
3. rozgrywa **tysiące gier w błyskawicznym tempie** i porównuje skuteczność,
4. potrafi pokazać **pełny przebieg pojedynczej gry tura po turze**,
5. dostarcza **matematyczną analizę planszy** (Monte Carlo) uzasadniającą,
   które pola są najlepsze.

---

## 📁 Struktura projektu

```
monopoly-symualcje/
├── monopoly/
│   ├── data.py         # plansza, ceny, czynsze, karty (dane)
│   ├── engine.py       # silnik gry (Game, Player, wszystkie mechaniki)
│   └── strategies.py   # 5 strategii AI
├── run_game.py         # pełny przebieg JEDNEJ gry, tura po turze
├── run_sim.py          # masowa symulacja (tysiące gier) + ranking strategii
├── run_matrix.py       # MATRYCA wariantów: 2-6 graczy × kapitał × mechaniki
├── run_modes.py        # tryby SZYBKIE z NEW Monopoly (najlepsza strategia/cel)
└── analyze_board.py    # analiza Monte Carlo: dlaczego dane pola są najlepsze
```

> 🎮 **Grasz w NEW MONOPOLY (Ubisoft, PS5)?** Zobacz [NEW_MONOPOLY_PS5.md](NEW_MONOPOLY_PS5.md)
> — plan zdobycia platyny (100%) i najlepsze strategie dopasowane do trybów tej gry.

> 🖥️ **Chcesz grać i analizować w przeglądarce?** Otwórz [monopoly-web/index.html](monopoly-web/index.html)
> — grywalne Monopoly z **paskiem oceny na żywo (Monte Carlo)**, wykresem przewagi, adnotacjami
> ruchów (`!!`/`?`/`??`) i botami o różnych strategiach. Analiza jak w szachach. Zobacz [monopoly-web/README.md](monopoly-web/README.md).

---

## 🚀 Jak uruchomić

```bash
# 1) Pełny, szybki przebieg jednej gry (log tura po turze)
python3 run_game.py                       # domyślna gra 4-osobowa
python3 run_game.py 42                     # z ziarnem 42 (powtarzalna)
python3 run_game.py 42 agresor pomczerw ostrozny kolejowy

# 2) Masowa symulacja i porównanie strategii
python3 run_sim.py                         # 5000 gier
python3 run_sim.py 20000                    # 20000 gier
python3 run_sim.py 5000 agresor pomczerw    # pojedynek dwóch strategii

# 3) MATRYCA wariantów: 2-6 graczy, kapitał 1500/2000, mechaniki on/off
python3 run_matrix.py                      # pełna matryca, 1500 gier/konfig
python3 run_matrix.py 500                   # szybciej
python3 run_matrix.py 3000 A                # tylko studium graczy × kapitał
python3 run_matrix.py 3000 B                # tylko studium wariantów zasad

# 4) Tryby SZYBKIE z NEW Monopoly (najlepsza strategia pod każdy cel)
python3 run_modes.py                       # 4 graczy, 2000 gier/cel
python3 run_modes.py 2000 6                 # 6 graczy

# 5) Analiza planszy (matematyczne uzasadnienie strategii)
python3 analyze_board.py                   # 3 mln rzutów Monte Carlo

# 6) Turniej strategii — macierz H2H, ranking, Elo, eksport CSV
python3 tournament.py                       # wszystkie strategie, 400 gier/parę
python3 tournament.py 800 agresor kolejowy rl

# 7) Trening bota RL (uczenie ze wzmocnieniem)
python3 train_rl.py 12000                    # REINFORCE self-play -> rl_policy.json

# 8) Serwer REST — podłącz własnego bota (dowolny język)
python3 server.py                            # http://localhost:8777
python3 examples/rest_bot.py                 # przykładowy bot-klient (buy/jail/auction/sell)

# 9) Trening własnego modelu (ewolucja self-play, CEM) — wznawialny „bez końca"
python3 train_evolve.py 30                    # -> monopoly/evolved_champion.json ("champion")

# 10) Agent LLM przez LOKALNE LM Studio (wszystko lokalnie)
python3 examples/llm_demo.py                  # LLM decyduje (fallback gdy LM Studio offline)
```

## 🏆 Wytrenowany model „champion" i zaawansowani agenci

- **`champion`** — model wytrenowany **ewolucyjnie (CEM self-play)**, optymalizujący pełny wektor
  parametrów. W symulatorze Pythona **dominuje (~49% win-rate** w stawce 8 strategii, baza 25%).
  Trening jest **wznawialny** — każdy `python3 train_evolve.py` doskonali model dalej.
- **`mcts`** (`monopoly/search.py`) — agent Monte Carlo (dogrywki + wybór akcji); ~50% vs kolejowy 1v1.
- **`llm`** (`monopoly/llm_agent.py`) — decyzje podejmuje **lokalny model w LM Studio**
  (OpenAI API na `localhost:1234`); wszystko zostaje lokalnie, z fallbackiem heurystycznym.
- **Ważny wniosek:** model championa **nie transferuje między silnikami** (Python ≠ JS) — optima są
  zależne od implementacji. Dlatego przeglądarka ma osobnego, natywnie wytrenowanego championa.

## 🔌 Podłącz własnego bota (API agenta)

Jak w Monopyly / MonopolySimulator — framework wywołuje metody Twojego agenta.
Odziedzicz po `Agent` i nadpisz wybrane hooki:

```python
from monopoly.agent import Agent, register_agent, play_match

class MojBot(Agent):
    name = "MojBot"
    cash_reserve = 250
    group_value = {"orange": 3, "red": 3, "rail": 3, "util": 0}  # co cenię
    def should_buy(self, game, me, pos):          # kupić to pole?
        return me.cash - game.sp(pos)[4] >= self.cash_reserve
    def leave_jail(self, game, me):               # wychodzić z więzienia?
        return game.round < 20

register_agent("mojbot", MojBot)                  # dostępny w sim/turniejach/lab
res = play_match([MojBot(), *[c() for c in ...]], seed=1)
```

Gotowe przykłady: `ThresholdAgent(reserve, price_cap, avoid, focus)`, `NoRailsAgent`,
`Cheapskate` (w [monopoly/agent.py](monopoly/agent.py)). Bota w innym języku podłączysz
przez **serwer REST** (`server.py`) — patrz [examples/rest_bot.py](examples/rest_bot.py).

Dostępne klucze strategii: `agresor`, `pomczerw`, `ostrozny`, `kolejowy`,
`monopolista`, `ekonom`, `luksusowy`.

---

## 🧠 Strategie AI

| Klucz         | Nazwa                  | Idea                                                        |
|---------------|------------------------|------------------------------------------------------------|
| `agresor`     | Agresor                | Kupuje wszystko, mała rezerwa (50), buduje do hoteli        |
| `pomczerw`    | Pomarańczowo-czerwony  | Priorytet: pomarańczowe, czerwone, jasnoniebieskie         |
| `ostrozny`    | Ostrożny               | Duża rezerwa (400), buduje max 3 domy (najlepszy ROI), siedzi w więzieniu |
| `kolejowy`    | Kolejowy               | Priorytet: koleje + pomarańczowe (stały dochód bez budowy) |
| `monopolista` | Monopolista            | Agresywny handel, zbiera pełne komplety, buduje do 4 domów  |
| `ekonom`      | Ekonom                 | Tanie komplety: brąz, jasnoniebieskie, koleje — szybkie, tanie monopole |
| `luksusowy`   | Luksusowy              | Drogie, wysokoczynszowe: zielone i granatowe — gra na późną eksplozję czynszu |

Każda strategia steruje: decyzją zakupu, licytacją na aukcji, priorytetem budowy,
progami gotówki, chęcią wychodzenia z więzienia oraz akceptacją transakcji.

### Warianty gry (konfiguracja silnika)

Klasa `Game` przyjmuje parametry wariantów — testowane masowo przez `run_matrix.py`:

| Parametr          | Domyślnie | Znaczenie                                                    |
|-------------------|-----------|--------------------------------------------------------------|
| `start_cash`      | 1500      | Kapitał startowy (badane 1500 **i** 2000)                    |
| `forced_auction`  | True      | Przymusowa licytacja nieodkupionego pola (zasada oficjalna)  |
| `allow_trades`    | True      | Czy dozwolone są wymiany między graczami                     |
| `allow_mortgage`  | True      | Czy dozwolone jest zastawianie hipoteczne                    |
| liczba graczy     | —         | 2 do 6 (dowolna długość listy graczy)                        |

---

## 📊 Kluczowe wnioski — matematyka planszy

Analiza Monte Carlo (`analyze_board.py`, 3 mln rzutów) potwierdza kanoniczne
prawdy Monopoly:

**Najczęściej odwiedzane pola:**
1. 🔒 **Więzienie (~22%)** — magnes planszy (pole „idź do więzienia”, karty,
   3 dublety). Dlatego pola **6–9 oczek za więzieniem są kluczowe**.
2. Grupa **pomarańczowa** (Marszałkowska, Plac Zbawiciela, Aleje Jerozolimskie)
3. Grupa **czerwona** (Nowy Świat, Chmielna, Świętokrzyska)
4. **Koleje** (Wschodni, Zachodni) — bardzo wysoka frekwencja

**Ranking ROI (zwrot z inwestycji na jeden obieg planszy):**

| Miejsce | Grupa          | Dlaczego                                             |
|--------:|----------------|------------------------------------------------------|
| 🥇 1    | Pomarańczowa   | Wysoka frekwencja + umiarkowany koszt = najlepszy ROI |
| 🥈 2    | Jasnoniebieska | Bardzo tania, świetny zwrot, szybko postawisz hotele  |
| 🥉 3    | Różowa         | Solidna, tanie domy, częste lądowania                 |
| 4       | Czerwona       | Wysoka frekwencja, wyższy koszt                       |
| ...     | Granatowa      | Najwyższy czynsz, ale rzadkie lądowania i drogie domy |

---

## 🥇 Wyniki masowej symulacji (10 000 gier, 5 strategii)

Baza losowa = 20% wygranych na strategię. 69% gier kończy się nokautem
(bankructwem wszystkich rywali), średnio po ~156 rundach.

| Strategia               | % wygranych | Śr. majątek | % bankructw |
|-------------------------|------------:|------------:|------------:|
| 🥇 **Kolejowy**         |   **30.1%** |        7475 |       55.1% |
| 🥈 Monopolista          |       21.4% |        6088 |       51.6% |
| 🥉 Pomarańczowo-czerwony|       17.9% |        5623 |       54.4% |
| Ostrożny                |       16.5% |        5218 |       55.5% |
| Agresor                 |       14.0% |        5536 |       60.7% |

**Kluczowy wniosek (i ciekawa niuansja):**
- Czysta **matematyka ROI** wskazuje grupę **pomarańczową** jako najlepszą
  inwestycję (najszybszy zwrot na jeden obieg planszy).
- Ale w **pełnej, długiej rozgrywce na wyniszczenie** wygrywa **Kolejowy** —
  bo koleje dają **stały dochód niezależny od budowy** (odporny na niedobór
  domów w banku) i kumulują się przez setki rund. Strategia „koleje + pomarańczowe”
  jest bardziej zdywersyfikowana niż samo „pomarańczowo-czerwone”.
- **Agresor** (kup wszystko, minimalna rezerwa) bankrutuje najczęściej (60.7%) —
  brak płynności zabija.

**Kontekst decyduje (ważne!):**
- W **pojedynku 1 na 1** i w krótkich, agresywnych grach **wygrywa
  pomarańczowo-czerwony** (54% vs koleje 46%, średnio 26 rund) — bo hotele na
  pomarańczowych szybko nokautują pojedynczego rywala, zanim koleje zdążą się skumulować.
- W **grze wieloosobowej na wyniszczenie** przewagę bierze Kolejowy — dłuższy
  horyzont premiuje stały dochód.

Wniosek praktyczny: **buduj pomarańczowe dla ROI i szybkiego nokautu, ale zbieraj
wszystkie 4 koleje jako kręgosłup dochodu** w dłuższych grach. Zawsze pilnuj rezerwy gotówki.

---

## 🧪 MATRYCA WARIANTÓW (22 500 gier, 7 strategii)

Wyniki z `run_matrix.py` (pełny surowy raport: `wyniki_matryca.txt`).

### Studium A — najlepsza strategia wg liczby graczy i kapitału

| Graczy | Kapitał 1500      | Kapitał 2000    |
|:------:|-------------------|-----------------|
| **2**  | Luksusowy (72%!)  | Ostrożny        |
| **3**  | Luksusowy         | Ostrożny        |
| **4**  | Monopolista       | Kolejowy        |
| **5**  | Monopolista       | Kolejowy        |
| **6**  | Kolejowy          | Kolejowy        |

**Wnioski:**
- **Mało graczy (2–3): rządzą drogie czynsze i cierpliwość.** Luksusowy
  (zielone/granatowe) miażdży w pojedynku (72% przy 1500!). Przy kapitale 2000
  wygrywa Ostrożny — więcej gotówki = przetrwanie i przeczekanie rywala.
- **Dużo graczy (5–6): rządzą koleje.** Długie gry na wyniszczenie premiują
  stały dochód niezależny od budowy. Kolejowy przy 6 graczach: ~30% (baza 16.7%).
- **Środek (4 graczy): rządzi handel.** Monopolista (agresywne wymiany) buduje
  komplety najszybciej.
- **Więcej gotówki (2000) przesuwa przewagę ku strategiom stabilnym**
  (Ostrożny, Kolejowy) kosztem agresywnego handlu — gry trwają dłużej,
  bufor gotówki mniej boli agresorów, ale cierpliwi przeczekują.
- **Agresor (kup wszystko, zero rezerwy) jest niemal zawsze najgorszy** —
  w 2 graczy przy 1500 wygrywa tylko 26% (baza 50%). Brak płynności = śmierć.

### Studium B — wpływ mechanik (4 graczy, kapitał 1500)

| Wariant                    | Zwycięzca      | Śr. długość | % nokautów |
|----------------------------|----------------|:-----------:|:----------:|
| Wszystko włączone (baza)   | Monopolista    | 75 rund     | 91%        |
| **Bez handlu (wymian)**    | **Kolejowy**   | **205 rund**| **57%**    |
| Bez przymusowych licytacji | Ostrożny       | 90 rund     | 88%        |
| Bez hipotek                | Monopolista    | 74 rund     | 91%        |
| Bez handlu i hipotek       | Kolejowy       | 203 rundy   | 58%        |

**Wnioski — która mechanika ile znaczy:**
- 🔑 **Handel to najważniejsza mechanika w grze.** Wyłączenie wymian niemal
  **potraja długość gry** (75 → 205 rund) i całkowicie zmienia zwycięzcę:
  bez handlu monopole kolorów prawie się nie tworzą, więc wygrywają **koleje**
  (dochód bez monopolu). Strategie oparte na wymianie (Monopolista, Pomarańczowy)
  się załamują. **Bez handlu Monopoly grzęźnie.**
- ⚖️ **Przymusowe licytacje mają umiarkowany wpływ.** Ich brak wydłuża gry
  (własność zostaje w banku), sprzyja cierpliwym (Ostrożny na szczyt) i ratuje
  Agresora, który nie przepłaca już na aukcjach (15.8% → 21%).
- 🏦 **Hipoteki prawie nie zmieniają, KTO wygrywa** (Monopolista tak czy siak),
  choć nieco poprawiają przeżywalność. To narzędzie płynności, nie strategii.

---

## 🏆 PLAN NAJLEPSZYCH STRATEGII (praktyczny)

**Faza 1 — Wczesna gra (rundy 1–10): kupuj agresywnie.**
- Kupuj **każdą** nieruchomość, na którą wejdziesz. Nierozegrana ziemia to
  stracona przewaga — nawet jeśli nie zbudujesz kompletu, to karta przetargowa.
- Priorytet: **pomarańczowe, czerwone, jasnoniebieskie** oraz **koleje**.
- Nie zostawiaj gotówki bezczynnie — ziemia > gotówka na tym etapie.

**Faza 2 — Środek gry (rundy 10–25): buduj monopole przez handel.**
- Monopoli prawie nigdy nie zdobędziesz samym lądowaniem — **handluj**.
- Dąż do wymian typu „wygrana–wygrana”: oddaj kartę, która daje przeciwnikowi
  komplet, tylko jeśli sam dostajesz komplet (najlepiej lepszy).
- **Nigdy nie oddawaj pomarańczowych/czerwonych** rywalowi bez desperackiej ceny.

**Faza 3 — Rozbudowa: zasada trzech domów.**
- Buduj **do 3 domów na każdej działce, zanim postawisz czwarty gdziekolwiek**.
  Największy skok czynszu jest z 2 → 3 domy. To najszybciej zwracająca się faza.
- **Niedobór domów (32 w banku)**: świadomie trzymaj po 3–4 domy na wielu
  działkach, by zablokować rywalom możliwość budowy hoteli. To realna broń.

**Faza 4 — Końcówka: kontroluj płynność.**
- Trzymaj rezerwę gotówki na czynsze rywali; hipotekuj peryferyjne pola,
  a nie te generujące dochód.
- W późnej grze **siedzenie w więzieniu bywa opłacalne** — nie płacisz czynszów,
  a wciąż pobierasz swoje. Wychodź tylko, gdy masz komplety do rozbudowy.

**Czego unikać:**
- Spółki (Elektrownia/Wodociągi) — słaby dochód, kupuj tylko jako karty przetargowe.
- Granatowe (Konstytucji/Krakowskie Przedm.) — spektakularny czynsz, ale rzadko
  ktoś tam ląduje i domy są najdroższe. Pułapka „prestiżu”.
- Trzymanie gotówki „na zapas” we wczesnej grze.

---

## 🔬 Jak silnik odwzorowuje realizm

- Pełne tabele czynszów, podwójny czynsz za komplet bez domów.
- Koleje: 25/50/100/200 wg liczby posiadanych; spółki 4× lub 10× oczka.
- Karty przemieszczające pionek (najbliższa kolej z podwójnym czynszem itd.).
- Reguła 3 dubletów → więzienie, wychodzenie przez dublet/kaucję/kartę.
- Aukcje przy rezygnacji z zakupu.
- Równomierna budowa w grupie, limit 32 domów / 12 hoteli w banku.
- Hipoteki i sprzedaż domów przy zbieraniu gotówki; kaskadowe bankructwo
  z przejęciem majątku przez wierzyciela.
- Silnik handlu (wymiany win-win + zakupy gotówkowe rozbitych pojedynczych pól).

Wyniki masowej symulacji zapisują się w `wyniki_10k.txt`.
 