"""
Dane planszy klasycznego Monopoly (edycja standardowa, 40 pól).
Wszystkie ceny, czynsze, koszty domów i hipotek zgodne z oficjalnymi zasadami.
Nazwy pól po polsku (odpowiedniki), z zachowaniem oryginalnych grup kolorów.
"""

# Typy pól
GO, PROPERTY, RAILROAD, UTILITY, TAX, CHANCE, CHEST, JAIL, FREE, GOTO_JAIL = (
    "GO", "PROPERTY", "RAILROAD", "UTILITY", "TAX", "CHANCE", "CHEST",
    "JAIL", "FREE_PARKING", "GO_TO_JAIL",
)

# Grupy kolorów i liczba pól w grupie
GROUP_SIZE = {
    "brown": 2, "lightblue": 3, "pink": 3, "orange": 3, "red": 3,
    "yellow": 3, "green": 3, "darkblue": 2,
}

# Każde pole: (pozycja, nazwa, typ, grupa, cena, [czynsze], koszt_domu, hipoteka)
# czynsze dla PROPERTY: [bazowy, 1dom, 2domy, 3domy, 4domy, hotel]
BOARD = [
    (0,  "START",                GO,       None,        0,   None, 0,   0),
    (1,  "Ulica Konopacka",       PROPERTY, "brown",     60,  [2, 10, 30, 90, 160, 250], 50, 30),
    (2,  "Kasa Społeczna",        CHEST,    None,        0,   None, 0,   0),
    (3,  "Ulica Stalowa",         PROPERTY, "brown",     60,  [4, 20, 60, 180, 320, 450], 50, 30),
    (4,  "Podatek dochodowy",     TAX,      None,        200, None, 0,   0),
    (5,  "Dworzec Zachodni",      RAILROAD, "rail",      200, None, 0,   100),
    (6,  "Ulica Radzymińska",     PROPERTY, "lightblue", 100, [6, 30, 90, 270, 400, 550], 50, 50),
    (7,  "Szansa",                CHANCE,   None,        0,   None, 0,   0),
    (8,  "Ulica Jagiellońska",    PROPERTY, "lightblue", 100, [6, 30, 90, 270, 400, 550], 50, 50),
    (9,  "Ulica Targowa",         PROPERTY, "lightblue", 120, [8, 40, 100, 300, 450, 600], 50, 60),
    (10, "Więzienie / Odwiedziny", JAIL,    None,        0,   None, 0,   0),
    (11, "Plac Bankowy",          PROPERTY, "pink",      140, [10, 50, 150, 450, 625, 750], 100, 70),
    (12, "Elektrownia",           UTILITY,  "util",      150, None, 0,   75),
    (13, "Ulica Wspólna",         PROPERTY, "pink",      140, [10, 50, 150, 450, 625, 750], 100, 70),
    (14, "Ulica Nowogrodzka",     PROPERTY, "pink",      160, [12, 60, 180, 500, 700, 900], 100, 80),
    (15, "Dworzec Główny",        RAILROAD, "rail",      200, None, 0,   100),
    (16, "Plac Zbawiciela",       PROPERTY, "orange",    180, [14, 70, 200, 550, 750, 950], 100, 90),
    (17, "Kasa Społeczna",        CHEST,    None,        0,   None, 0,   0),
    (18, "Ulica Marszałkowska",   PROPERTY, "orange",    180, [14, 70, 200, 550, 750, 950], 100, 90),
    (19, "Aleje Jerozolimskie",   PROPERTY, "orange",    200, [16, 80, 220, 600, 800, 1000], 100, 100),
    (20, "Bezpłatny parking",     FREE,     None,        0,   None, 0,   0),
    (21, "Ulica Świętokrzyska",   PROPERTY, "red",       220, [18, 90, 250, 700, 875, 1050], 150, 110),
    (22, "Szansa",                CHANCE,   None,        0,   None, 0,   0),
    (23, "Ulica Chmielna",        PROPERTY, "red",       220, [18, 90, 250, 700, 875, 1050], 150, 110),
    (24, "Nowy Świat",            PROPERTY, "red",       240, [20, 100, 300, 750, 925, 1100], 150, 120),
    (25, "Dworzec Wschodni",      RAILROAD, "rail",      200, None, 0,   100),
    (26, "Ulica Piękna",          PROPERTY, "yellow",    260, [22, 110, 330, 800, 975, 1150], 150, 130),
    (27, "Ulica Koszykowa",       PROPERTY, "yellow",    260, [22, 110, 330, 800, 975, 1150], 150, 130),
    (28, "Wodociągi",             UTILITY,  "util",      150, None, 0,   75),
    (29, "Ulica Mokotowska",      PROPERTY, "yellow",    280, [24, 120, 360, 850, 1025, 1200], 150, 140),
    (30, "Idź do więzienia",      GOTO_JAIL, None,       0,   None, 0,   0),
    (31, "Plac Trzech Krzyży",    PROPERTY, "green",     300, [26, 130, 390, 900, 1100, 1275], 200, 150),
    (32, "Aleje Ujazdowskie",     PROPERTY, "green",     300, [26, 130, 390, 900, 1100, 1275], 200, 150),
    (33, "Kasa Społeczna",        CHEST,    None,        0,   None, 0,   0),
    (34, "Ulica Foksal",          PROPERTY, "green",     320, [28, 150, 450, 1000, 1200, 1400], 200, 160),
    (35, "Dworzec Centralny",     RAILROAD, "rail",      200, None, 0,   100),
    (36, "Szansa",                CHANCE,   None,        0,   None, 0,   0),
    (37, "Plac Konstytucji",      PROPERTY, "darkblue",  350, [35, 175, 500, 1100, 1300, 1500], 200, 175),
    (38, "Podatek od luksusu",    TAX,      None,        100, None, 0,   0),
    (39, "Krakowskie Przedmieście", PROPERTY, "darkblue", 400, [50, 200, 600, 1400, 1700, 2000], 200, 200),
]

# Pozycje pól specjalnych (do kart Szansa/Kasa)
POS_GO = 0
POS_JAIL = 10
POS_GOTO_JAIL = 30
RAILROAD_POSITIONS = [5, 15, 25, 35]
UTILITY_POSITIONS = [12, 28]

# Rzuty czynszu za koleje wg liczby posiadanych
RAILROAD_RENT = {1: 25, 2: 50, 3: 100, 4: 200}

# Limity banku (mechanika niedoboru domów jest realnym elementem strategii)
BANK_HOUSES = 32
BANK_HOTELS = 12


# --- Karty ---
# Każda karta to (opis, akcja, wartość). Akcje obsługiwane w engine.py
CHANCE_CARDS = [
    ("Idź na START", "move_to", POS_GO),
    ("Jedź na Krakowskie Przedmieście", "move_to", 39),
    ("Jedź na Nowy Świat (jeśli miniesz START, odbierz 200)", "advance_to", 24),
    ("Jedź na Plac Bankowy (jeśli miniesz START, odbierz 200)", "advance_to", 11),
    ("Jedź na najbliższy dworzec, zapłać podwójny czynsz", "nearest_rail", 0),
    ("Jedź na najbliższy dworzec, zapłać podwójny czynsz", "nearest_rail", 0),
    ("Jedź na najbliższą spółkę (zapłać 10x oczka lub kup)", "nearest_util", 0),
    ("Bank wypłaca ci dywidendę 50", "collect", 50),
    ("Wyjdź za darmo z więzienia", "get_out_of_jail", 0),
    ("Cofnij się o 3 pola", "move_back", 3),
    ("Idź do więzienia", "go_to_jail", 0),
    ("Remont: zapłać 25 za dom i 100 za hotel", "repairs", (25, 100)),
    ("Mandat za prędkość: zapłać 15", "pay", 15),
    ("Podróż na Dworzec Zachodni (miniesz START -> 200)", "advance_to", 5),
    ("Wybrano cię prezesem — zapłać każdemu graczowi 50", "pay_each", 50),
    ("Pożyczka budowlana dojrzała — odbierz 150", "collect", 150),
]

CHEST_CARDS = [
    ("Idź na START", "move_to", POS_GO),
    ("Błąd banku na twoją korzyść — odbierz 200", "collect", 200),
    ("Opłata za lekarza — zapłać 50", "pay", 50),
    ("Ze sprzedaży akcji zyskujesz 50", "collect", 50),
    ("Wyjdź za darmo z więzienia", "get_out_of_jail", 0),
    ("Idź do więzienia", "go_to_jail", 0),
    ("Fundusz świąteczny dojrzał — odbierz 100", "collect", 100),
    ("Zwrot podatku — odbierz 20", "collect", 20),
    ("Twoje urodziny — odbierz po 10 od każdego gracza", "collect_each", 10),
    ("Polisa na życie dojrzała — odbierz 100", "collect", 100),
    ("Opłata szpitalna — zapłać 100", "pay", 100),
    ("Opłata za szkołę — zapłać 50", "pay", 50),
    ("Honorarium za konsultacje — odbierz 25", "collect", 25),
    ("Naprawa ulic: 40 za dom, 115 za hotel", "repairs", (40, 115)),
    ("Druga nagroda w konkursie piękności — odbierz 10", "collect", 10),
    ("Otrzymujesz spadek — odbierz 100", "collect", 100),
]

# Nowa Kasa Społeczna 2021 (karty głosowane przez fanów) — wariant opcjonalny.
CHEST_2021_CARDS = [
    ("Wieczory z sąsiadem — same historie! Odbierz 100", "collect", 100),
    ("Sprzątasz miejskie ścieżki — odbierz 50", "collect", 50),
    ("Oddajesz krew — były darmowe ciastka! Odbierz 10", "collect", 10),
    ("Kupujesz ciastka z kiermaszu — zapłać 50", "pay", 50),
    ("Ratujesz szczeniaka — wyjdź za darmo z więzienia", "get_out_of_jail", 0),
    ("Organizujesz imprezę sąsiedzką — odbierz po 10 od każdego", "collect_each", 10),
    ("Głośna muzyka w nocy — idź do więzienia", "go_to_jail", 0),
    ("Pomagasz sąsiadce z zakupami — dostajesz obiad! Odbierz 20", "collect", 20),
    ("Budujesz plac zabaw przy szkole — odbierz 100", "collect", 100),
    ("Grasz z dziećmi w szpitalu — odbierz 100", "collect", 100),
    ("Kiermasz myjni — zapomniałeś zamknąć okna! Zapłać 100", "pay", 100),
    ("Kończysz bieg na cel charytatywny — idź na START (odbierz 200)", "move_to", POS_GO),
    ("Pomagasz sąsiadom po burzy — odbierz 200", "collect", 200),
    ("Darowizna dla schroniska — zapłać 50", "pay", 50),
    ("Projekt remontowy: 40 za dom, 115 za hotel", "repairs", (40, 115)),
    ("Kiermasz wypieków dla szkoły — odbierz 25", "collect", 25),
]
