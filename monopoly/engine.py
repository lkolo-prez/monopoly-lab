"""
Silnik gry Monopoly: gracze, rzuty, czynsze, więzienie, aukcje,
budowa domów, hipoteki, handel i bankructwo.
"""
import random
from . import data


class Player:
    def __init__(self, index, name, strategy):
        self.index = index
        self.name = name
        self.strategy = strategy
        self.cash = 1500
        self.pos = 0
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_cards = 0
        self.bankrupt = False
        self.props = set()          # zbiór pozycji posiadanych pól
        self.doubles_streak = 0
        self.rent_collected = 0     # łączny czynsz zebrany (cel Landowner)

    def __repr__(self):
        return f"{self.name}({self.strategy.name})"


class Game:
    def __init__(self, players_spec, seed=None, logger=None, max_rounds=1000,
                 start_cash=1500, forced_auction=True, allow_trades=True,
                 allow_mortgage=True, goal=None, chest_variant="classic"):
        """players_spec: lista (nazwa, strategia).

        Warianty gry:
          start_cash      — kapitał startowy każdego gracza (np. 1500 lub 2000)
          forced_auction  — czy nieodkupione pole idzie na przymusową licytację
                            (True = zasada oficjalna; False = zostaje w banku)
          allow_trades    — czy dozwolone są wymiany między graczami
          allow_mortgage  — czy dozwolone jest zastawianie hipoteczne pól
        """
        self.rng = random.Random(seed)
        self.players = [Player(i, n, s) for i, (n, s) in enumerate(players_spec)]
        self.log = logger or (lambda *a, **k: None)
        self.max_rounds = max_rounds
        self.start_cash = start_cash
        self.forced_auction = forced_auction
        self.allow_trades = allow_trades
        self.allow_mortgage = allow_mortgage
        # Cel trybu Szybkiego (NEW Monopoly): np. {"type": "real_estate", "target": 7}
        # typy: real_estate, magnate, architect, hotel_manager, town_planner, landowner
        self.goal = goal
        self.goal_winner = None
        for p in self.players:
            p.cash = start_cash

        self.owner = [None] * 40          # indeks właściciela lub None
        self.houses = [0] * 40            # 0-4 domy, 5 = hotel
        self.mortgaged = [False] * 40
        self.bank_houses = data.BANK_HOUSES
        self.bank_hotels = data.BANK_HOTELS

        # potasowane talie
        self.chance = list(range(len(data.CHANCE_CARDS)))
        self.chest_cards = (data.CHEST_2021_CARDS if chest_variant == "2021"
                            else data.CHEST_CARDS)
        self.chest = list(range(len(self.chest_cards)))
        self.rng.shuffle(self.chance)
        self.rng.shuffle(self.chest)
        self.chance_i = 0
        self.chest_i = 0

        # mapa grupa -> pozycje
        self.group_pos = {}
        for pos, name, typ, group, *rest in data.BOARD:
            if typ == data.PROPERTY:
                self.group_pos.setdefault(group, []).append(pos)

        self.round = 0

    # ---------- pomocnicze ----------
    def sp(self, pos):
        """Zwraca krotkę pola planszy."""
        return data.BOARD[pos]

    def active_players(self):
        return [p for p in self.players if not p.bankrupt]

    def owns_full_group(self, player, group):
        pos_list = self.group_pos.get(group, [])
        return pos_list and all(self.owner[p] == player.index for p in pos_list)

    def group_has_houses(self, group):
        return any(self.houses[p] > 0 for p in self.group_pos.get(group, []))

    def count_type(self, player, positions):
        return sum(1 for p in positions if self.owner[p] == player.index)

    def num_railroads(self, player):
        return self.count_type(player, data.RAILROAD_POSITIONS)

    def num_utilities(self, player):
        return self.count_type(player, data.UTILITY_POSITIONS)

    # ---------- czynsz ----------
    def calc_rent(self, pos, dice_total, force_rail_double=False, force_util_10=False):
        _, name, typ, group, price, rents, hcost, mort = self.sp(pos)
        owner_idx = self.owner[pos]
        if owner_idx is None or self.mortgaged[pos]:
            return 0
        owner = self.players[owner_idx]

        if typ == data.PROPERTY:
            h = self.houses[pos]
            if h == 0:
                base = rents[0]
                if self.owns_full_group(owner, group):
                    base *= 2      # podwójny czynsz za komplet bez domów
                return base
            return rents[h]        # h=1..4 domy, 5 = hotel (rents[5])

        if typ == data.RAILROAD:
            n = self.num_railroads(owner)
            rent = data.RAILROAD_RENT.get(n, 0)
            return rent * 2 if force_rail_double else rent

        if typ == data.UTILITY:
            n = self.num_utilities(owner)
            mult = 10 if (force_util_10 or n == 2) else 4
            return mult * dice_total
        return 0

    # ---------- rzut kośćmi ----------
    def roll(self):
        a = self.rng.randint(1, 6)
        b = self.rng.randint(1, 6)
        return a, b

    # ---------- tura gracza ----------
    def take_turn(self, player):
        if player.bankrupt:
            return
        # faza zarządzania: handel, budowa, odhipotekowanie
        self.management_phase(player)

        player.doubles_streak = 0
        while True:
            if player.in_jail:
                moved = self.handle_jail(player)
                if not moved:
                    return           # został w więzieniu
                # po wyjściu z więzienia wykonuje ruch w handle_jail
                return
            a, b = self.roll()
            doubles = (a == b)
            if doubles:
                player.doubles_streak += 1
                if player.doubles_streak == 3:
                    self.log(f"  {player.name}: trzeci dublet -> więzienie!")
                    self.send_to_jail(player)
                    return
            total = a + b
            self.log(f"  {player.name} rzuca {a}+{b}={total}"
                     + (" (dublet)" if doubles else ""))
            self.advance(player, total)
            if player.bankrupt:
                return
            if player.in_jail:       # trafił do więzienia w trakcie ruchu
                return
            if not doubles:
                return
            # dublet -> kolejny rzut

    def advance(self, player, steps, dice_total=None):
        new = player.pos + steps
        if new >= 40:
            new -= 40
            player.cash += 200
            self.log(f"    {player.name} mija START, +200 (stan {player.cash})")
        player.pos = new
        self.resolve_landing(player, dice_total if dice_total is not None else steps)

    def move_to(self, player, pos, collect_go=True, dice_total=0):
        if collect_go and pos < player.pos:
            player.cash += 200
            self.log(f"    {player.name} mija START, +200")
        player.pos = pos
        self.resolve_landing(player, dice_total)

    # ---------- lądowanie ----------
    def resolve_landing(self, player, dice_total, force_rail_double=False,
                        force_util_10=False):
        pos, name, typ, group, price, rents, hcost, mort = self.sp(player.pos)
        self.log(f"    {player.name} ląduje: {name}")

        if typ in (data.GO, data.FREE, data.JAIL):
            return
        if typ == data.GOTO_JAIL:
            self.send_to_jail(player)
            return
        if typ == data.TAX:
            self.pay(player, price, creditor=None, reason=name)
            return
        if typ == data.CHANCE:
            self.draw_card(player, self.chance, data.CHANCE_CARDS, "chance")
            return
        if typ == data.CHEST:
            self.draw_card(player, self.chest, self.chest_cards, "chest")
            return

        # pole własnościowe (ulica, kolej, spółka)
        owner_idx = self.owner[pos]
        if owner_idx is None:
            self.offer_purchase(player, pos)
        elif owner_idx != player.index and not self.mortgaged[pos]:
            rent = self.calc_rent(pos, dice_total, force_rail_double, force_util_10)
            if rent > 0:
                owner = self.players[owner_idx]
                owner.rent_collected += rent
                self.log(f"    czynsz {rent} dla {owner.name}")
                self.pay(player, rent, creditor=owner, reason=f"czynsz {name}")

    # ---------- zakup / aukcja ----------
    def offer_purchase(self, player, pos):
        _, name, typ, group, price, *_ = self.sp(pos)
        if player.cash >= price and player.strategy.should_buy(self, player, pos):
            player.cash -= price
            self.owner[pos] = player.index
            player.props.add(pos)
            self.log(f"    {player.name} kupuje {name} za {price} (stan {player.cash})")
        elif self.forced_auction:
            self.auction(pos)
        else:
            self.log(f"    {name} pozostaje w banku (brak licytacji)")

    def auction(self, pos):
        _, name, typ, group, price, *_ = self.sp(pos)
        bids = []
        for p in self.active_players():
            val = min(p.strategy.auction_value(self, p, pos), p.cash)
            if val > 0:
                bids.append((val, p))
        if not bids:
            self.log(f"    aukcja {name}: brak chętnych, pole wraca do banku")
            return
        bids.sort(key=lambda x: x[0], reverse=True)
        winner_val, winner = bids[0]
        second = bids[1][0] if len(bids) > 1 else 0
        payperc = max(1, min(winner_val, second + 10))
        winner.cash -= payperc
        self.owner[pos] = winner.index
        winner.props.add(pos)
        self.log(f"    aukcja {name}: wygrywa {winner.name} za {payperc}")

    # ---------- płatności ----------
    def pay(self, player, amount, creditor=None, reason=""):
        if player.cash < amount:
            self.raise_cash(player, amount - player.cash)
        if player.cash >= amount:
            player.cash -= amount
            if creditor is not None:
                creditor.cash += amount
            if reason:
                self.log(f"    {player.name} płaci {amount} ({reason}), stan {player.cash}")
        else:
            self.declare_bankrupt(player, creditor)

    def collect(self, player, amount):
        player.cash += amount

    # ---------- więzienie ----------
    def send_to_jail(self, player):
        player.pos = data.POS_JAIL
        player.in_jail = True
        player.jail_turns = 0
        player.doubles_streak = 0

    def handle_jail(self, player):
        """Zwraca True jeśli gracz wyszedł i wykonał ruch, False jeśli został."""
        want_out = player.strategy.leave_jail(self, player)
        # karta wyjścia
        if want_out and player.get_out_cards > 0:
            player.get_out_cards -= 1
            player.in_jail = False
            player.jail_turns = 0
            self.log(f"  {player.name} używa karty wyjścia z więzienia")
            a, b = self.roll()
            self.advance(player, a + b, a + b)
            return True
        # próba dubletu
        a, b = self.roll()
        if a == b:
            player.in_jail = False
            player.jail_turns = 0
            self.log(f"  {player.name} wyrzuca dublet i wychodzi z więzienia")
            self.advance(player, a + b, a + b)
            return True
        player.jail_turns += 1
        if want_out or player.jail_turns >= 3:
            # zapłać kaucję 50 i wyjdź
            self.pay(player, 50, creditor=None, reason="kaucja")
            if player.bankrupt:
                return False
            player.in_jail = False
            player.jail_turns = 0
            self.log(f"  {player.name} płaci kaucję i wychodzi")
            self.advance(player, a + b, a + b)
            return True
        self.log(f"  {player.name} zostaje w więzieniu ({player.jail_turns}/3)")
        return False

    # ---------- karty ----------
    def draw_card(self, player, deck, cards, kind):
        idx = (self.chance_i if kind == "chance" else self.chest_i)
        card_id = deck[idx % len(deck)]
        if kind == "chance":
            self.chance_i += 1
        else:
            self.chest_i += 1
        desc, action, value = cards[card_id]
        self.log(f"    Karta: {desc}")
        self.apply_card(player, action, value)

    def apply_card(self, player, action, value):
        if action == "move_to":
            self.move_to(player, value, collect_go=True)
        elif action == "advance_to":
            self.move_to(player, value, collect_go=True)
        elif action == "move_back":
            player.pos = (player.pos - value) % 40
            self.resolve_landing(player, 0)
        elif action == "collect":
            self.collect(player, value)
        elif action == "pay":
            self.pay(player, value, creditor=None, reason="karta")
        elif action == "go_to_jail":
            self.send_to_jail(player)
        elif action == "get_out_of_jail":
            player.get_out_cards += 1
        elif action == "nearest_rail":
            pos = self._nearest(player.pos, data.RAILROAD_POSITIONS)
            self.move_to_special(player, pos, force_rail_double=True)
        elif action == "nearest_util":
            pos = self._nearest(player.pos, data.UTILITY_POSITIONS)
            self.move_to_special(player, pos, force_util_10=True)
        elif action == "pay_each":
            for other in self.active_players():
                if other is not player:
                    self.pay(player, value, creditor=other, reason="każdemu")
                    if player.bankrupt:
                        return
        elif action == "collect_each":
            for other in self.active_players():
                if other is not player:
                    self.pay(other, value, creditor=player, reason="urodziny")
        elif action == "repairs":
            per_house, per_hotel = value
            total = 0
            for pos in player.props:
                h = self.houses[pos]
                if h == 5:
                    total += per_hotel
                else:
                    total += per_house * h
            if total:
                self.pay(player, total, creditor=None, reason="remont")

    def move_to_special(self, player, pos, force_rail_double=False, force_util_10=False):
        if pos < player.pos:
            player.cash += 200
        player.pos = pos
        # dla spółki z karty potrzebny rzut
        dice_total = sum(self.roll()) if force_util_10 else 0
        owner_idx = self.owner[pos]
        if owner_idx is None:
            self.offer_purchase(player, pos)
        elif owner_idx != player.index and not self.mortgaged[pos]:
            rent = self.calc_rent(pos, dice_total, force_rail_double, force_util_10)
            if rent:
                owner = self.players[owner_idx]
                owner.rent_collected += rent
                self.log(f"    czynsz specjalny {rent} dla {owner.name}")
                self.pay(player, rent, creditor=owner, reason="czynsz karta")

    def _nearest(self, pos, targets):
        for step in range(1, 41):
            cand = (pos + step) % 40
            if cand in targets:
                return cand
        return targets[0]

    # ---------- zbieranie gotówki / bankructwo ----------
    def raise_cash(self, player, needed):
        """Sprzedaje domy i hipotekuje, aby zebrać `needed` gotówki."""
        # 1) sprzedaż domów (połowa ceny), 2) hipoteki bezdomnych pól
        while player.cash < needed and self._sell_one_house(player):
            pass
        if self.allow_mortgage:
            while player.cash < needed and self._mortgage_one(player):
                pass

    def _sell_one_house(self, player):
        # sprzedaj dom z grupy o największej liczbie domów (równomiernie)
        best = None
        best_h = 0
        for pos in player.props:
            h = self.houses[pos]
            if h > best_h:
                best_h = h
                best = pos
        if best is None or best_h == 0:
            return False
        _, name, typ, group, price, rents, hcost, mort = self.sp(best)
        self.houses[best] -= 1
        if self.houses[best] == 4:   # rozbiórka hotelu -> 4 domy (potrzeba domów)
            self.bank_hotels += 1
            self.bank_houses -= 4
        else:
            self.bank_houses += 1
        player.cash += hcost // 2
        return True

    def _mortgage_one(self, player):
        for pos in player.props:
            if not self.mortgaged[pos] and self.houses[pos] == 0:
                _, name, typ, group, price, rents, hcost, mort = self.sp(pos)
                self.mortgaged[pos] = True
                player.cash += mort
                return True
        return False

    def declare_bankrupt(self, player, creditor):
        self.log(f"  !! {player.name} BANKRUTUJE"
                 + (f" na rzecz {creditor.name}" if creditor else " (bank)"))
        # sprzedaj wszystkie domy do banku
        for pos in list(player.props):
            h = self.houses[pos]
            if h > 0:
                _, name, typ, group, price, rents, hcost, mort = self.sp(pos)
                if h == 5:
                    self.bank_hotels += 1
                else:
                    self.bank_houses += h
                self.houses[pos] = 0
                player.cash += hcost // 2 * (4 if h == 5 else h)
        if creditor is not None:
            creditor.cash += max(0, player.cash)
            for pos in list(player.props):
                self.owner[pos] = creditor.index
                creditor.props.add(pos)
            creditor.get_out_cards += player.get_out_cards
        else:
            for pos in list(player.props):
                self.owner[pos] = None
                self.mortgaged[pos] = False
        player.props.clear()
        player.cash = 0
        player.get_out_cards = 0
        player.bankrupt = True

    # ---------- faza zarządzania ----------
    def management_phase(self, player):
        self.try_trades(player)
        self.try_unmortgage(player)
        self.try_build(player)

    def try_unmortgage(self, player):
        # odhipotekuj jeśli komplet i dużo gotówki
        reserve = player.strategy.cash_reserve
        for group in self.group_pos:
            if not self.owns_full_group(player, group):
                continue
            for pos in self.group_pos[group]:
                if self.mortgaged[pos]:
                    _, name, typ, grp, price, rents, hcost, mort = self.sp(pos)
                    cost = int(mort * 1.1)
                    if player.cash - cost >= reserve + 100:
                        player.cash -= cost
                        self.mortgaged[pos] = False

    def try_build(self, player):
        reserve = player.strategy.cash_reserve
        max_h = player.strategy.max_houses
        while True:
            best = None
            best_prio = -1
            for group in self.group_pos:
                if not self.owns_full_group(player, group):
                    continue
                positions = self.group_pos[group]
                if any(self.mortgaged[p] for p in positions):
                    continue
                min_h = min(self.houses[p] for p in positions)
                if min_h >= max_h:
                    continue
                # równomierność: buduj na polu o najniższej liczbie domów
                target = min(positions, key=lambda p: self.houses[p])
                _, name, typ, grp, price, rents, hcost, mort = self.sp(target)
                # zasoby banku
                going_to_hotel = self.houses[target] == 4
                if going_to_hotel and self.bank_hotels <= 0:
                    continue
                if not going_to_hotel and self.bank_houses <= 0:
                    continue
                if player.cash - hcost < reserve:
                    continue
                prio = player.strategy.build_priority(group)
                if prio > best_prio:
                    best_prio = prio
                    best = (target, hcost, going_to_hotel)
            if best is None:
                return
            target, hcost, going_to_hotel = best
            player.cash -= hcost
            self.houses[target] += 1
            if going_to_hotel:
                self.bank_hotels -= 1
                self.bank_houses += 4   # zwraca 4 domy do banku
            else:
                self.bank_houses -= 1
            _, name, *_ = self.sp(target)
            self.log(f"    {player.name} buduje na {name} "
                     f"(domów: {self.houses[target]}, stan {player.cash})")

    # ---------- handel ----------
    def needs_one_for_group(self, player):
        """Zwraca listę (group, brakująca_pozycja, właściciel) gdzie graczowi brakuje 1 pola."""
        result = []
        for group, positions in self.group_pos.items():
            owned = [p for p in positions if self.owner[p] == player.index]
            missing = [p for p in positions if self.owner[p] != player.index]
            if len(owned) == len(positions) - 1 and len(missing) == 1:
                mpos = missing[0]
                mowner = self.owner[mpos]
                if mowner is not None and mowner != player.index:
                    result.append((group, mpos, self.players[mowner]))
        return result

    def try_trades(self, player):
        if not self.allow_trades or not player.strategy.trades:
            return
        my_needs = self.needs_one_for_group(player)
        for group, mpos, owner in my_needs:
            if owner.bankrupt or self.houses[mpos] > 0:
                continue
            # 1) wymiana korzystna dla obu (win-win)
            owner_needs = self.needs_one_for_group(owner)
            swapped = False
            for ogroup, opos, oowner in owner_needs:
                if ogroup == group:
                    continue   # ta sama grupa = zwykła zamiana, nikt nie zyskuje kompletu
                if oowner.index == player.index and self.houses[opos] == 0:
                    # player oddaje opos, dostaje mpos: obaj kończą komplet
                    if owner.strategy.trades:
                        self._execute_swap(player, mpos, owner, opos)
                        self.log(f"    WYMIANA: {player.name} <-> {owner.name} "
                                 f"({self.sp(mpos)[1]} za {self.sp(opos)[1]})")
                        swapped = True
                        break
            if swapped:
                continue
            # 2) zakup gotówkowy z premią (gdy sprzedający nie ma szans na ten komplet)
            _, name, typ, grp, price, *_ = self.sp(mpos)
            owner_in_group = self.count_type(owner, self.group_pos[group])
            seller_can_use = owner_in_group >= 1  # ma już coś w tej grupie
            premium = int(price * 2)
            seller_desperate = owner.cash < owner.strategy.cash_reserve
            if (not seller_can_use or seller_desperate) and \
               player.cash - premium >= player.strategy.cash_reserve and \
               owner.strategy.accepts_sale(self, owner, mpos, premium):
                player.cash -= premium
                owner.cash += premium
                self.owner[mpos] = player.index
                player.props.add(mpos)
                owner.props.discard(mpos)
                self.log(f"    ZAKUP: {player.name} kupuje {name} od {owner.name} "
                         f"za {premium}")

    def _execute_swap(self, p1, pos1, p2, pos2):
        self.owner[pos1] = p1.index
        p1.props.add(pos1)
        p2.props.discard(pos1)
        self.owner[pos2] = p2.index
        p2.props.add(pos2)
        p1.props.discard(pos2)

    # ---------- cele trybu Szybkiego (NEW Monopoly) ----------
    def full_groups(self, player):
        return [g for g in self.group_pos if self.owns_full_group(player, g)]

    def meets_goal(self, player):
        if self.goal is None or player.bankrupt:
            return False
        t = self.goal["type"]
        target = self.goal.get("target", 1)
        if t == "real_estate":                 # pierwszy z N nieruchomościami
            return len(player.props) >= target
        if t == "magnate":                      # pierwszy z N gotówki
            return player.cash >= target
        if t == "hotel_manager":                # pierwszy hotel
            return any(self.houses[p] == 5 for p in player.props)
        if t == "architect":                    # dom na każdym polu kompletu
            for g in self.full_groups(player):
                if all(self.houses[p] >= 1 for p in self.group_pos[g]):
                    return True
            return False
        if t == "town_planner":                 # N pełnych kompletów
            return len(self.full_groups(player)) >= target
        if t == "landowner":                    # N zebranego czynszu
            return player.rent_collected >= target
        return False

    def check_goal(self, acting):
        """Zwraca gracza, który osiągnął cel (priorytet: aktualnie grający)."""
        if self.goal is None:
            return None
        if self.meets_goal(acting):
            return acting
        for p in self.active_players():
            if self.meets_goal(p):
                return p
        return None

    # ---------- wartość netto ----------
    def net_worth(self, player):
        total = player.cash
        for pos in player.props:
            _, name, typ, group, price, rents, hcost, mort = self.sp(pos)
            total += mort if self.mortgaged[pos] else price
            total += (hcost // 2) * (self.houses[pos] if self.houses[pos] < 5
                                     else 4) if self.houses[pos] else 0
            if self.houses[pos] == 5:
                total += (hcost // 2) * 5
        return total

    # ---------- pętla główna ----------
    def play(self):
        order = list(self.players)
        while self.round < self.max_rounds:
            self.round += 1
            active = self.active_players()
            if len(active) <= 1:
                break
            self.log(f"--- Runda {self.round} ---")
            for player in order:
                if player.bankrupt:
                    continue
                if len(self.active_players()) <= 1:
                    break
                self.take_turn(player)
                w = self.check_goal(player)
                if w is not None:
                    self.goal_winner = w
                    self.log(f"*** {w.name} osiąga cel trybu Szybkiego! ***")
                    return self.result()
        return self.result()

    def result(self):
        active = self.active_players()
        if self.goal_winner is not None:
            winner = self.goal_winner
            ranked = sorted(self.players,
                            key=lambda p: (p is winner, not p.bankrupt, self.net_worth(p)),
                            reverse=True)
        else:
            ranked = sorted(self.players,
                            key=lambda p: (not p.bankrupt, self.net_worth(p)),
                            reverse=True)
            winner = ranked[0]
        return {
            "winner": winner,
            "winner_strategy": winner.strategy.name,
            "rounds": self.round,
            "finished": len(active) <= 1 or self.goal_winner is not None,
            "goal_reached": self.goal_winner is not None,
            "ranking": [(p.name, p.strategy.name, self.net_worth(p), p.bankrupt)
                        for p in ranked],
        }
