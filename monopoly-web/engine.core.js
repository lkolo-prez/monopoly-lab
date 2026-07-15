/* ============================================================================
   Monopoly Engine Core — działa w przeglądarce (global M) i w Node (module.exports)
   Zawiera: dane planszy, silnik gry, polityki AI (strategie + poziomy trudności)
   oraz ewaluator Monte Carlo (prawdopodobieństwo wygranej z danej pozycji).
   ============================================================================ */
(function (root) {
  "use strict";

  // ---------- RNG (Mulberry32, deterministyczny dla dogrywek) ----------
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const liveRng = Math.random;

  // ---------- Plansza (40 pól) ----------
  const P = "prop", R = "rail", U = "util", GO = "go", TAX = "tax",
        CH = "chance", CC = "chest", JAIL = "jail", FP = "free", G2J = "gotojail";

  // [i, nazwa, typ, grupa, cena, [czynsze], koszt_domu, hipoteka]
  const BOARD = [
    [0,"START",GO,null,0,null,0,0],
    [1,"Ul. Konopacka",P,"brown",60,[2,10,30,90,160,250],50,30],
    [2,"Kasa Społeczna",CC,null,0,null,0,0],
    [3,"Ul. Stalowa",P,"brown",60,[4,20,60,180,320,450],50,30],
    [4,"Podatek dochodowy",TAX,null,200,null,0,0],
    [5,"Dworzec Zachodni",R,"rail",200,null,0,100],
    [6,"Ul. Radzymińska",P,"lightblue",100,[6,30,90,270,400,550],50,50],
    [7,"Szansa",CH,null,0,null,0,0],
    [8,"Ul. Jagiellońska",P,"lightblue",100,[6,30,90,270,400,550],50,50],
    [9,"Ul. Targowa",P,"lightblue",120,[8,40,100,300,450,600],50,60],
    [10,"Więzienie",JAIL,null,0,null,0,0],
    [11,"Plac Bankowy",P,"pink",140,[10,50,150,450,625,750],100,70],
    [12,"Elektrownia",U,"util",150,null,0,75],
    [13,"Ul. Wspólna",P,"pink",140,[10,50,150,450,625,750],100,70],
    [14,"Ul. Nowogrodzka",P,"pink",160,[12,60,180,500,700,900],100,80],
    [15,"Dworzec Główny",R,"rail",200,null,0,100],
    [16,"Plac Zbawiciela",P,"orange",180,[14,70,200,550,750,950],100,90],
    [17,"Kasa Społeczna",CC,null,0,null,0,0],
    [18,"Ul. Marszałkowska",P,"orange",180,[14,70,200,550,750,950],100,90],
    [19,"Al. Jerozolimskie",P,"orange",200,[16,80,220,600,800,1000],100,100],
    [20,"Bezpłatny parking",FP,null,0,null,0,0],
    [21,"Ul. Świętokrzyska",P,"red",220,[18,90,250,700,875,1050],150,110],
    [22,"Szansa",CH,null,0,null,0,0],
    [23,"Ul. Chmielna",P,"red",220,[18,90,250,700,875,1050],150,110],
    [24,"Nowy Świat",P,"red",240,[20,100,300,750,925,1100],150,120],
    [25,"Dworzec Wschodni",R,"rail",200,null,0,100],
    [26,"Ul. Piękna",P,"yellow",260,[22,110,330,800,975,1150],150,130],
    [27,"Ul. Koszykowa",P,"yellow",260,[22,110,330,800,975,1150],150,130],
    [28,"Wodociągi",U,"util",150,null,0,75],
    [29,"Ul. Mokotowska",P,"yellow",280,[24,120,360,850,1025,1200],150,140],
    [30,"Idź do więzienia",G2J,null,0,null,0,0],
    [31,"Pl. Trzech Krzyży",P,"green",300,[26,130,390,900,1100,1275],200,150],
    [32,"Al. Ujazdowskie",P,"green",300,[26,130,390,900,1100,1275],200,150],
    [33,"Kasa Społeczna",CC,null,0,null,0,0],
    [34,"Ul. Foksal",P,"green",320,[28,150,450,1000,1200,1400],200,160],
    [35,"Dworzec Centralny",R,"rail",200,null,0,100],
    [36,"Szansa",CH,null,0,null,0,0],
    [37,"Pl. Konstytucji",P,"darkblue",350,[35,175,500,1100,1300,1500],200,175],
    [38,"Podatek od luksusu",TAX,null,100,null,0,0],
    [39,"Krak. Przedmieście",P,"darkblue",400,[50,200,600,1400,1700,2000],200,200],
  ];
  const RAILS = [5,15,25,35], UTILS = [12,28];
  const RAIL_RENT = {1:25,2:50,3:100,4:200};
  const GROUPS = {};
  BOARD.forEach(s => { if (s[2] === P) (GROUPS[s[3]] = GROUPS[s[3]] || []).push(s[0]); });
  const GROUP_COLORS = {
    brown:"#7b5a3a", lightblue:"#a9d6ea", pink:"#d6338b", orange:"#e8892b",
    red:"#d62828", yellow:"#f4d03f", green:"#2a9d4a", darkblue:"#2d4bd8",
  };

  // ---------- Karty (opis, akcja, wartość) ----------
  const CHANCE = [
    ["Idź na START","move",0],["Jedź na Krak. Przedmieście","move",39],
    ["Jedź na Nowy Świat","advance",24],["Jedź na Plac Bankowy","advance",11],
    ["Najbliższy dworzec, podwójny czynsz","nrail",0],
    ["Najbliższy dworzec, podwójny czynsz","nrail",0],
    ["Najbliższa spółka (10x lub kup)","nutil",0],
    ["Dywidenda +50","get",50],["Wyjście z więzienia","getout",0],
    ["Cofnij o 3","back",3],["Idź do więzienia","tojail",0],
    ["Remont: 25/dom, 100/hotel","repair",[25,100]],["Mandat -15","pay",15],
    ["Podróż na Dworzec Zachodni","advance",5],
    ["Prezes — zapłać każdemu 50","payeach",50],["Pożyczka +150","get",150],
  ];
  const CHEST = [
    ["Idź na START","move",0],["Błąd banku +200","get",200],
    ["Lekarz -50","pay",50],["Sprzedaż akcji +50","get",50],
    ["Wyjście z więzienia","getout",0],["Idź do więzienia","tojail",0],
    ["Fundusz +100","get",100],["Zwrot podatku +20","get",20],
    ["Urodziny +10 od każdego","geteach",10],["Polisa +100","get",100],
    ["Szpital -100","pay",100],["Szkoła -50","pay",50],
    ["Konsultacje +25","get",25],["Naprawa ulic 40/115","repair",[40,115]],
    ["Konkurs +10","get",10],["Spadek +100","get",100],
  ];
  // Nowa Kasa Społeczna 2021 (karty głosowane przez fanów) — wariant opcjonalny
  const CHEST_2021 = [
    ["Wieczory z sąsiadem — same historie! Odbierz 100","get",100],
    ["Sprzątasz miejskie ścieżki. Odbierz 50","get",50],
    ["Oddajesz krew — były darmowe ciastka! Odbierz 10","get",10],
    ["Kupujesz ciastka z kiermaszu. Zapłać 50","pay",50],
    ["Ratujesz szczeniaka — i sam czujesz się uratowany! Wyjście z więzienia","getout",0],
    ["Organizujesz imprezę sąsiedzką. Odbierz po 10 od każdego","geteach",10],
    ["Głośna muzyka w nocy? Sąsiedzi niezadowoleni. Idź do więzienia","tojail",0],
    ["Pomagasz sąsiadce z zakupami — dostajesz obiad! Odbierz 20","get",20],
    ["Budujesz plac zabaw przy szkole — testujesz zjeżdżalnię! Odbierz 100","get",100],
    ["Grasz z dziećmi w szpitalu dziecięcym. Odbierz 100","get",100],
    ["Kiermasz myjni — zapomniałeś zamknąć okna! Zapłać 100","pay",100],
    ["Kończysz bieg i zbierasz na szpital! Idź na START, odbierz 200","move",0],
    ["Pomagasz sąsiadom sprzątać ogrody po burzy. Odbierz 200","get",200],
    ["Darowizna dla schroniska. Zapłać 50","pay",50],
    ["Projekt remontowy: 40 za dom, 115 za hotel","repair",[40,115]],
    ["Kiermasz wypieków dla szkoły. Odbierz 25","get",25],
  ];

  // ---------- Strategie AI (jak w symulatorze Pythona) ----------
  const STRATS = {
    balanced:{name:"Zrównoważony",reserve:150,maxH:5,trades:true,def:1,
      gv:{orange:3,red:3,lightblue:2,pink:2,rail:2,yellow:2,green:2,darkblue:2,brown:1,util:1}},
    agresor:{name:"Agresor",reserve:50,maxH:5,trades:true,def:2,
      gv:{orange:3,red:3,lightblue:2,rail:2,pink:2,yellow:2,green:2,darkblue:2,brown:1,util:1}},
    pomczerw:{name:"Pomarańczowo-czerwony",reserve:150,maxH:5,trades:true,def:1,
      gv:{orange:3,red:3,lightblue:3,pink:2,rail:2,yellow:1,green:1,darkblue:1,brown:1,util:0}},
    ostrozny:{name:"Ostrożny",reserve:400,maxH:3,trades:true,def:1,
      gv:{orange:2,red:2,lightblue:2,pink:2,yellow:2,green:2,rail:1,darkblue:1,brown:1,util:0}},
    kolejowy:{name:"Kolejowy",reserve:100,maxH:5,trades:true,def:1,
      gv:{rail:3,util:2,orange:3,red:2,lightblue:2,pink:2,yellow:1,green:1,darkblue:1,brown:1}},
    monopolista:{name:"Monopolista",reserve:200,maxH:4,trades:true,def:2,
      gv:{orange:3,red:3,pink:3,lightblue:2,yellow:2,green:2,darkblue:2,rail:2,brown:1,util:0}},
    ekonom:{name:"Ekonom",reserve:100,maxH:4,trades:true,def:1,
      gv:{brown:3,lightblue:3,rail:3,pink:2,orange:2,util:1,red:1,yellow:1,green:0,darkblue:0}},
    luksusowy:{name:"Luksusowy",reserve:300,maxH:5,trades:true,def:1,
      gv:{green:3,darkblue:3,yellow:2,red:2,orange:2,rail:1,pink:1,lightblue:1,brown:0,util:0}},
    rl:{name:"RL (self-play)",reserve:100,maxH:4,trades:true,def:1,
      gv:{orange:3,red:3,lightblue:2,pink:2,rail:2,yellow:2,green:2,darkblue:2,brown:1,util:1}},
    // Model wytrenowany ewolucyjnie (CEM self-play, wielopanelowy) NATYWNIE dla tego silnika.
    // Schemat: czerwone + granatowe + koleje + spółki + jasnoniebieskie na maks, umiarkowana rezerwa.
    champion:{name:"Champion (evolved)",reserve:85,maxH:5,trades:true,def:1,
      gv:{brown:2.38,lightblue:3.00,pink:2.12,orange:1.98,red:3.00,yellow:1.44,
          green:1.12,darkblue:3.00,rail:3.00,util:3.00}},
  };
  const DIFF = { latwy:0.45, sredni:0.15, trudny:0.0, ekspert:0.0 };

  // Polityka zakupu wyuczona przez RL (REINFORCE, 12k epizodów self-play w Pythonie).
  // Cechy: bias, afford, completes, advances, tier, is_rail, is_util, landing, cash_share, phase, buffer, n_players
  const RL_WEIGHTS = [1.2385,1.4039,-0.3621,-0.2555,0.3775,0.1194,-0.3544,1.0449,0.2192,-0.2848,1.3441,1.1048];
  const RL_LAND=(function(){ const f={0:2.9,5:2.50,15:2.55,25:2.55,35:2.30,6:2.30,8:2.28,9:2.30,11:2.29,13:2.30,14:2.36,16:2.46,18:2.55,19:2.30,21:2.24,23:2.24,24:2.62,26:2.30,27:2.28,29:2.20,31:2.24,32:2.20,34:2.10,37:2.05,39:2.10,1:2.00,3:2.02,12:2.64,28:2.35}; const a=[]; for(let i=0;i<40;i++)a.push((f[i]||2.2)/2.6); return a; })();
  function rlFeatures(st,pid,pos){
    const s=BOARD[pos], typ=s[2], group=s[3], price=s[4], p=st.players[pid], cash=p.cash;
    let completes=0,advances=0,tier=0,isRail=0,isUtil=0;
    if(typ===P){ const arr=GROUPS[group], owned=countIn(st,pid,arr);
      completes=owned===arr.length-1?1:0; advances=owned>=1?1:0; tier=s[5][3]/1400; }
    else if(typ===R){ isRail=1; advances=numRails(st,pid)/4; tier=0.35; }
    else if(typ===U){ isUtil=1; tier=0.15; }
    const act=active(st), totalCash=act.reduce((a,q)=>a+q.cash,0)||1;
    return [1, Math.min(cash/Math.max(price,1),3)/3, completes, advances, tier, isRail, isUtil,
            RL_LAND[pos], cash/totalCash, Math.min(st.round,50)/50,
            Math.max(-1,Math.min(1,(cash-price)/1500)), act.length/6];
  }

  function groupKey(pos){ const t=BOARD[pos][2]; return t===R?"rail":t===U?"util":BOARD[pos][3]; }
  function gv(strat,pos){ const s=STRATS[strat]||STRATS.balanced; const k=groupKey(pos); return (k in s.gv)?s.gv[k]:s.def; }

  // ---------- Stan gry ----------
  function newGame(playersSpec, opts) {
    opts = opts || {};
    const st = {
      players: playersSpec.map((p, i) => ({
        id:i, name:p.name, cash:opts.startCash||1500, pos:0, jail:false, jailTurns:0,
        cards:0, bankrupt:false, isHuman:!!p.isHuman, rentCollected:0,
        strat:p.strat||"balanced", diff:p.diff||"sredni",
      })),
      owner:new Array(40).fill(-1), houses:new Array(40).fill(0), mort:new Array(40).fill(false),
      bankHouses:32, bankHotels:12,
      chance:shuffle(range(16), opts.seed?mulberry32(opts.seed):liveRng), chancePtr:0,
      chest:shuffle(range(16), opts.seed?mulberry32(opts.seed+7):liveRng), chestPtr:0,
      turn:0, round:0, forcedAuction:opts.forcedAuction!==false, allowTrades:opts.allowTrades!==false,
      log:[], done:false, winner:-1,
      humanId: playersSpec.findIndex(p=>p.isHuman),
      goal: opts.goal||null,   // {type,target} tryb Szybki NEW Monopoly
      chestCards: (opts.chestVariant==="2021") ? CHEST_2021 : CHEST,
      goSalary: (opts.goSalary!=null) ? opts.goSalary : 200,   // pensja za przejście START
      freeParking: !!opts.freeParkingJackpot,                  // pula na Bezpłatnym parkingu
      pot: 0,
    };
    return st;
  }
  function range(n){ const a=[]; for(let i=0;i<n;i++)a.push(i); return a; }
  function shuffle(a, rnd){ for(let i=a.length-1;i>0;i--){ const j=Math.floor(rnd()*(i+1)); [a[i],a[j]]=[a[j],a[i]]; } return a; }

  function clone(st){
    return {
      players: st.players.map(p=>({...p})),
      owner: st.owner.slice(), houses: st.houses.slice(), mort: st.mort.slice(),
      bankHouses:st.bankHouses, bankHotels:st.bankHotels,
      chance:st.chance.slice(), chancePtr:st.chancePtr, chest:st.chest.slice(), chestPtr:st.chestPtr,
      turn:st.turn, round:st.round, forcedAuction:st.forcedAuction, allowTrades:st.allowTrades,
      log:[], done:st.done, winner:st.winner, humanId:st.humanId, goal:st.goal,
      chestCards:st.chestCards, goSalary:st.goSalary, freeParking:st.freeParking, pot:st.pot,
    };
  }

  // ---------- Zapytania ----------
  const active = st => st.players.filter(p=>!p.bankrupt);
  const propsOf = (st,pid) => { const a=[]; for(let i=0;i<40;i++) if(st.owner[i]===pid) a.push(i); return a; };
  function ownsFullGroup(st,pid,group){ const g=GROUPS[group]; return g && g.every(pos=>st.owner[pos]===pid); }
  function fullGroups(st,pid){ return Object.keys(GROUPS).filter(g=>ownsFullGroup(st,pid,g)); }
  function countIn(st,pid,arr){ let n=0; for(const pos of arr) if(st.owner[pos]===pid)n++; return n; }
  const numRails = (st,pid)=>countIn(st,pid,RAILS);
  const numUtils = (st,pid)=>countIn(st,pid,UTILS);

  function rentOf(st,pos,dice,opts){
    opts=opts||{}; const s=BOARD[pos]; const o=st.owner[pos];
    if(o<0||st.mort[pos]) return 0;
    if(s[2]===P){ const h=st.houses[pos];
      if(h===0){ let b=s[5][0]; if(ownsFullGroup(st,o,s[3])) b*=2; return b; } return s[5][h]; }
    if(s[2]===R){ let r=RAIL_RENT[numRails(st,o)]||0; return opts.railDouble?r*2:r; }
    if(s[2]===U){ const m=(opts.util10||numUtils(st,o)===2)?10:4; return m*dice; }
    return 0;
  }
  function netWorth(st,pid){
    const p=st.players[pid]; if(p.bankrupt) return 0; let t=p.cash;
    for(const pos of propsOf(st,pid)){ const s=BOARD[pos];
      t += st.mort[pos]? s[7] : s[4];
      if(st.houses[pos]>0) t += Math.floor(s[6]/2)*st.houses[pos];
    }
    return t;
  }

  // ---------- Gotówka / bankructwo ----------
  function raiseCash(st,pid,need){
    const p=st.players[pid];
    while(p.cash<need){ if(!sellHouse(st,pid)) break; }
    while(p.cash<need){ if(!mortgageOne(st,pid)) break; }
  }
  function sellHouse(st,pid){
    let best=-1,bh=0; for(const pos of propsOf(st,pid)){ if(st.houses[pos]>bh){bh=st.houses[pos];best=pos;} }
    if(best<0||bh===0) return false; const s=BOARD[best];
    if(st.houses[best]===5){ st.bankHotels++; st.bankHouses-=4; } else st.bankHouses++;
    st.houses[best]--; st.players[pid].cash += Math.floor(s[6]/2); return true;
  }
  function mortgageOne(st,pid){
    for(const pos of propsOf(st,pid)){ if(!st.mort[pos]&&st.houses[pos]===0){ st.mort[pos]=true; st.players[pid].cash+=BOARD[pos][7]; return true; } }
    return false;
  }
  function pay(st,pid,amount,creditor){
    const p=st.players[pid];
    if(p.cash<amount) raiseCash(st,pid,amount);
    if(p.cash>=amount){ p.cash-=amount; if(creditor>=0) st.players[creditor].cash+=amount; else if(st.freeParking) st.pot+=amount; return true; }
    bankrupt(st,pid,creditor); return false;
  }
  function bankrupt(st,pid,creditor){
    const p=st.players[pid];
    for(const pos of propsOf(st,pid)){ const h=st.houses[pos];
      if(h>0){ const s=BOARD[pos]; if(h===5)st.bankHotels++; else st.bankHouses+=h; st.houses[pos]=0; p.cash+=Math.floor(s[6]/2)*(h===5?4:h); } }
    if(creditor>=0){ st.players[creditor].cash+=Math.max(0,p.cash);
      for(const pos of propsOf(st,pid)) st.owner[pos]=creditor;
      st.players[creditor].cards+=p.cards;
    } else { for(const pos of propsOf(st,pid)){ st.owner[pos]=-1; st.mort[pos]=false; } }
    p.cash=0; p.cards=0; p.bankrupt=true;
    if(active(st).length<=1){ st.done=true; st.winner=active(st)[0]?active(st)[0].id:-1; }
  }

  // ---------- Budowa / handel ----------
  function tryBuild(st,pid){
    const p=st.players[pid], s=STRATS[p.strat]||STRATS.balanced;
    for(;;){ let best=-1,bestP=-1,bestHotel=false,bestCost=0;
      for(const g of Object.keys(GROUPS)){
        if(!ownsFullGroup(st,pid,g)) continue; const arr=GROUPS[g];
        if(arr.some(pos=>st.mort[pos])) continue;
        const minH=Math.min(...arr.map(pos=>st.houses[pos])); if(minH>=s.maxH) continue;
        const tgt=arr.reduce((a,b)=>st.houses[b]<st.houses[a]?b:a);
        const cost=BOARD[tgt][6], hotel=st.houses[tgt]===4;
        if(hotel&&st.bankHotels<=0) continue; if(!hotel&&st.bankHouses<=0) continue;
        if(p.cash-cost<s.reserve) continue;
        const pr=(g in s.gv)?s.gv[g]:s.def; if(pr>bestP){ bestP=pr; best=tgt; bestHotel=hotel; bestCost=cost; }
      }
      if(best<0) return; p.cash-=bestCost; st.houses[best]++;
      if(bestHotel){ st.bankHotels--; st.bankHouses+=4; } else st.bankHouses--;
    }
  }
  function needOne(st,pid){ // grupy gdzie brakuje 1 pola -> [group,missingPos,ownerId]
    const res=[]; for(const g of Object.keys(GROUPS)){ const arr=GROUPS[g];
      const own=arr.filter(pos=>st.owner[pos]===pid), miss=arr.filter(pos=>st.owner[pos]!==pid);
      if(own.length===arr.length-1&&miss.length===1){ const mo=st.owner[miss[0]];
        if(mo>=0&&mo!==pid) res.push([g,miss[0],mo]); } }
    return res;
  }
  function tryTrades(st,pid){
    if(!st.allowTrades) return; const p=st.players[pid], s=STRATS[p.strat]||STRATS.balanced;
    if(!s.trades) return;
    for(const [group,mpos,oid] of needOne(st,pid)){
      if(oid===st.humanId) continue; // z człowiekiem AI handluje tylko za jego zgodą (UI)
      const owner=st.players[oid]; if(owner.bankrupt||st.houses[mpos]>0) continue;
      let swapped=false;
      for(const [og,opos,ooid] of needOne(st,oid)){
        if(og===group) continue;
        if(ooid===pid&&st.houses[opos]===0){ // wymiana win-win
          st.owner[mpos]=pid; st.owner[opos]=oid; swapped=true; break; }
      }
      if(swapped) continue;
      const price=BOARD[mpos][4], premium=price*2;
      const ownerInGroup=countIn(st,oid,GROUPS[group]);
      const sellerDesperate=owner.cash<(STRATS[owner.strat]||STRATS.balanced).reserve;
      if((ownerInGroup<1||sellerDesperate)&&p.cash-premium>=s.reserve){
        p.cash-=premium; owner.cash+=premium; st.owner[mpos]=pid;
      }
    }
  }

  // ---------- Decyzje AI ----------
  function completesGroup(st,pid,pos){ const g=BOARD[pos][3]; if(!GROUPS[g])return false;
    const arr=GROUPS[g]; return arr.filter(x=>st.owner[x]===pid).length===arr.length-1; }
  function aiShouldBuy(st,pid,pos){
    const p=st.players[pid], s=STRATS[p.strat]||STRATS.balanced, price=BOARD[pos][4];
    if(p.cash<price) return false;
    if(p.strat==="rl"){ const f=rlFeatures(st,pid,pos); let z=0; for(let i=0;i<f.length;i++)z+=RL_WEIGHTS[i]*f[i]; return 1/(1+Math.exp(-z))>=0.5; }
    let v=gv(p.strat,pos); if(completesGroup(st,pid,pos)) v=3;
    const mistake=DIFF[p.diff]||0;
    if(Math.random()<mistake) return p.cash>price*1.1 && Math.random()<0.6; // słaby AI kupuje losowo
    if(v>=3) return p.cash-price>=Math.min(s.reserve,50);
    if(v>=2) return p.cash-price>=s.reserve;
    if(v>=1) return p.cash-price>=s.reserve+150;
    return completesGroup(st,pid,pos)&&p.cash-price>=s.reserve;
  }
  function aiAuctionValue(st,pid,pos){
    const p=st.players[pid], s=STRATS[p.strat]||STRATS.balanced, price=BOARD[pos][4];
    let v=gv(p.strat,pos); if(completesGroup(st,pid,pos)) v=3;
    let bid = v>=3?price*1.3 : v>=2?price : v>=1?price*0.6 : price*0.3;
    return Math.min(Math.floor(bid), Math.max(0, p.cash - Math.floor(s.reserve/2)));
  }
  function aiLeaveJail(st,pid){
    if(st.round<15) return true;
    for(let i=0;i<40;i++) if(st.houses[i]>0 && st.owner[i]!==pid && st.owner[i]>=0) return false;
    return true;
  }

  // ---------- Ruch i lądowanie ----------
  function rollDice(rnd){ rnd=rnd||liveRng; return [1+Math.floor(rnd()*6), 1+Math.floor(rnd()*6)]; }
  function sendJail(st,pid){ const p=st.players[pid]; p.pos=10; p.jail=true; p.jailTurns=0; }
  function nearest(pos,targets){ for(let s=1;s<=40;s++){ const c=(pos+s)%40; if(targets.includes(c)) return c; } return targets[0]; }

  // Zwraca {buy:pos} jeśli człowiek musi zdecydować o zakupie; inaczej null.
  function landing(st,pid,dice,rnd,interactive,opts){
    opts=opts||{}; const p=st.players[pid], s=BOARD[p.pos], t=s[2];
    if(t===GO||t===JAIL) return null;
    if(t===FP){ if(st.freeParking && st.pot>0){ st._lastPot=st.pot; p.cash+=st.pot; st.pot=0; } return null; }
    if(t===G2J){ sendJail(st,pid); return null; }
    if(t===TAX){ pay(st,pid,s[4],-1); return null; }
    if(t===CH) return drawCard(st,pid,rnd,interactive,"chance");
    if(t===CC) return drawCard(st,pid,rnd,interactive,"chest");
    // własność
    const o=st.owner[p.pos];
    if(o<0){ // nieodkupione
      if(interactive && p.isHuman) return {buy:p.pos};
      if(aiShouldBuy(st,pid,p.pos)){ p.cash-=s[4]; st.owner[p.pos]=pid; }
      else if(st.forcedAuction) auction(st,p.pos);
      return null;
    }
    if(o!==pid && !st.mort[p.pos]){ const r=rentOf(st,p.pos,dice,opts); if(r>0){ st.players[o].rentCollected+=r; pay(st,pid,r,o); } }
    return null;
  }
  function auction(st,pos){
    const bids=[]; for(const p of active(st)){ const v=Math.min(aiAuctionValue(st,p.id,pos),p.cash); if(v>0) bids.push([v,p.id]); }
    if(!bids.length) return; bids.sort((a,b)=>b[0]-a[0]);
    const winV=bids[0][0], second=bids.length>1?bids[1][0]:0, price=Math.max(1,Math.min(winV,second+10));
    st.players[bids[0][1]].cash-=price; st.owner[pos]=bids[0][1];
  }
  function drawCard(st,pid,rnd,interactive,kind){
    const deck=kind==="chance"?st.chance:st.chest, cards=kind==="chance"?CHANCE:(st.chestCards||CHEST);
    const idx=kind==="chance"?st.chancePtr++:st.chestPtr++; const [desc,act,val]=cards[deck[idx%deck.length]];
    const p=st.players[pid];
    switch(act){
      case "move": moveTo(st,pid,val,true); return landing(st,pid,0,rnd,interactive);
      case "advance": moveTo(st,pid,val,true); return landing(st,pid,0,rnd,interactive);
      case "back": p.pos=((p.pos-val)%40+40)%40; return landing(st,pid,0,rnd,interactive);
      case "get": p.cash+=val; return null;
      case "pay": pay(st,pid,val,-1); return null;
      case "tojail": sendJail(st,pid); return null;
      case "getout": p.cards++; return null;
      case "nrail": { p.pos=nearest(p.pos,RAILS); return landing(st,pid,0,rnd,interactive,{railDouble:true}); }
      case "nutil": { p.pos=nearest(p.pos,UTILS); const d=rollDice(rnd); return landing(st,pid,d[0]+d[1],rnd,interactive,{util10:true}); }
      case "payeach": for(const o of active(st)) if(o.id!==pid){ pay(st,pid,val,o.id); if(p.bankrupt)break; } return null;
      case "geteach": for(const o of active(st)) if(o.id!==pid) pay(st,o.id,val,pid); return null;
      case "repair": { let tot=0; for(const pos of propsOf(st,pid)){ const h=st.houses[pos]; tot+= h===5?val[1]:val[0]*h; } if(tot)pay(st,pid,tot,-1); return null; }
    }
    return null;
  }
  function moveTo(st,pid,pos,collectGo){ const p=st.players[pid]; if(collectGo&&pos<p.pos) p.cash+=st.goSalary; p.pos=pos; }
  function moveBy(st,pid,steps){ const p=st.players[pid]; let np=p.pos+steps; if(np>=40){ np-=40; p.cash+=st.goSalary; } p.pos=np; }

  // ---------- Tura AI (pełna) ----------
  function jailTurn(st,pid,rnd){
    const p=st.players[pid], out=aiLeaveJail(st,pid);
    if(out&&p.cards>0){ p.cards--; p.jail=false; p.jailTurns=0; const d=rollDice(rnd); moveBy(st,pid,d[0]+d[1]); landing(st,pid,d[0]+d[1],rnd,false); return true; }
    const d=rollDice(rnd);
    if(d[0]===d[1]){ p.jail=false; p.jailTurns=0; moveBy(st,pid,d[0]+d[1]); landing(st,pid,d[0]+d[1],rnd,false); return true; }
    p.jailTurns++;
    if(out||p.jailTurns>=3){ pay(st,pid,50,-1); if(p.bankrupt) return false; p.jail=false; p.jailTurns=0; moveBy(st,pid,d[0]+d[1]); landing(st,pid,d[0]+d[1],rnd,false); return true; }
    return false;
  }
  function aiTurn(st,pid,rnd){
    const p=st.players[pid]; if(p.bankrupt) return;
    tryTrades(st,pid); tryBuild(st,pid);
    let dbl=0;
    for(;;){
      if(p.jail){ jailTurn(st,pid,rnd); return; }
      const d=rollDice(rnd); const isDbl=d[0]===d[1];
      if(isDbl){ dbl++; if(dbl===3){ sendJail(st,pid); return; } }
      moveBy(st,pid,d[0]+d[1]); landing(st,pid,d[0]+d[1],rnd,false);
      if(p.bankrupt||p.jail) return;
      if(!isDbl) return;
    }
  }

  // ---------- Cele trybu Szybkiego (NEW Monopoly) ----------
  function meetsGoal(st,pid){
    if(!st.goal) return false; const p=st.players[pid]; if(p.bankrupt) return false;
    const t=st.goal.type, target=st.goal.target||1;
    if(t==="real_estate") return propsOf(st,pid).length>=target;
    if(t==="magnate") return p.cash>=target;
    if(t==="hotel_manager"){ for(let i=0;i<40;i++) if(st.owner[i]===pid&&st.houses[i]===5) return true; return false; }
    if(t==="architect"){ for(const g of fullGroups(st,pid)) if(GROUPS[g].every(x=>st.houses[x]>=1)) return true; return false; }
    if(t==="town_planner") return fullGroups(st,pid).length>=target;
    if(t==="landowner") return p.rentCollected>=target;
    return false;
  }
  function checkGoalWinner(st){ if(!st.goal) return -1; for(const p of active(st)) if(meetsGoal(st,p.id)) return p.id; return -1; }

  // ---------- Ewaluator Monte Carlo ----------
  function playout(st0,rnd,cap){
    const st=clone(st0); st.humanId=-1; cap=cap||140; // w dogrywkach wszyscy grają jak AI
    let guard=0;
    while(!st.done && st.round<cap && guard<cap*st.players.length+50){
      st.round++;
      for(const p of st.players){ if(p.bankrupt) continue; if(active(st).length<=1) break; aiTurn(st,p.id,rnd);
        const gw=checkGoalWinner(st); if(gw>=0){ st.done=true; st.winner=gw; break; }
        if(st.done) break; }
      guard++;
    }
    if(st.done && st.winner>=0) return st.winner;
    // brak nokautu -> zwycięzca wg wartości netto
    let best=-1,bw=-1; for(const p of active(st)){ const w=netWorth(st,p.id); if(w>bw){bw=w;best=p.id;} }
    return best;
  }
  function evaluate(st, n, seed){
    n=n||300; const rnd=mulberry32((seed||12345)>>>0);
    const wins=new Array(st.players.length).fill(0); let valid=0;
    for(let i=0;i<n;i++){ const w=playout(st,rnd); if(w>=0){ wins[w]++; valid++; } }
    return wins.map(w=> valid?w/valid:0);
  }

  // ---------- Metryki ryzyka (analiza „szachowa") ----------
  const DICE_DIST=(function(){ const d={}; for(let a=1;a<=6;a++)for(let b=1;b<=6;b++){ const s=a+b; d[s]=(d[s]||0)+1; } return d; })();
  function dangerNext(st,pid){ // oczekiwany czynsz, jaki zapłacisz w następnym rzucie
    const p=st.players[pid]; let exp=0;
    for(let s=2;s<=12;s++){ const prob=DICE_DIST[s]/36; const pos=(p.pos+s)%40; const o=st.owner[pos];
      if(o>=0&&o!==pid&&!st.mort[pos]){ exp += prob*rentOf(st,pos,s); } }
    return Math.round(exp);
  }
  function monopolyProximity(st,pid){ // ile grup masz „prawie" (brak 1)
    let complete=fullGroups(st,pid).length, near=0;
    for(const g of Object.keys(GROUPS)){ const arr=GROUPS[g]; const own=countIn(st,pid,arr);
      if(own===arr.length-1 && own<arr.length && !ownsFullGroup(st,pid,g)) near++; }
    return {complete,near};
  }
  function liquidity(st,pid){ const p=st.players[pid]; const danger=dangerNext(st,pid);
    return { cash:p.cash, danger, ratio: danger>0? p.cash/danger : Infinity }; }

  // ---------- Handel człowiek↔bot (oceniany silnikiem) ----------
  function groupHasHouses(st,group){ return GROUPS[group] && GROUPS[group].some(p=>st.houses[p]>0); }
  function canTrade(st,deal){
    const g=deal.give||[], r=deal.recv||[], cash=deal.cash||0, gc=deal.giveCards||0, rc=deal.recvCards||0;
    if(!g.length && !r.length && !cash && !gc && !rc) return {ok:false,why:"pusta oferta"};
    for(const p of g){ if(st.owner[p]!==deal.from) return {ok:false,why:"to nie Twoje pole"};
      if(groupHasHouses(st,BOARD[p][3])) return {ok:false,why:"najpierw sprzedaj domy w tej grupie"}; }
    for(const p of r){ if(st.owner[p]!==deal.to) return {ok:false,why:"pole nie należy do kontrahenta"};
      if(groupHasHouses(st,BOARD[p][3])) return {ok:false,why:"kontrahent ma domy w tej grupie"}; }
    if(cash>0 && st.players[deal.from].cash<cash) return {ok:false,why:"za mało Twojej gotówki"};
    if(cash<0 && st.players[deal.to].cash< -cash) return {ok:false,why:"kontrahent nie ma gotówki"};
    if(gc>st.players[deal.from].cards) return {ok:false,why:"nie masz karty wyjścia"};
    if(rc>st.players[deal.to].cards) return {ok:false,why:"kontrahent nie ma karty wyjścia"};
    return {ok:true};
  }
  function applyTrade(st,deal){
    for(const p of (deal.give||[])) st.owner[p]=deal.to;
    for(const p of (deal.recv||[])) st.owner[p]=deal.from;
    const cash=deal.cash||0; st.players[deal.from].cash-=cash; st.players[deal.to].cash+=cash;
    const gc=deal.giveCards||0, rc=deal.recvCards||0;
    st.players[deal.from].cards += rc-gc; st.players[deal.to].cards += gc-rc;
  }
  function evalDealFor(st,deal,pid,n,seed){ const c=clone(st); applyTrade(c,deal); return evaluate(c,n||160,seed)[pid]; }
  function botDecideTrade(st,deal,n){
    const seed=((deal.from+1)*99991+(deal.to+1)*7919+2654435761)>>>0; n=n||170;
    const before=evaluate(st,n,seed)[deal.to];
    const after=evalDealFor(st,deal,deal.to,n,seed);
    let accept = after >= before-0.005, counter=null;
    if(!accept){ // kontra: poproś o więcej gotówki od proponującego
      for(const extra of [50,100,150,250,400]){
        const need=(deal.cash||0)+extra; if(st.players[deal.from].cash<need) break;
        const d2=Object.assign({},deal,{cash:need});
        if(evalDealFor(st,d2,deal.to,n,seed) >= before-0.005){ counter=d2; break; }
      }
    }
    return {accept, before, after, counter};
  }

  // ---------- Detekcja strategii przeciwnika (z zachowań) ----------
  const DKEYS=["brown","lightblue","pink","orange","red","yellow","green","darkblue","rail","util"];
  function observedVec(st,pid){
    return DKEYS.map(k=>{
      if(k==="rail") return numRails(st,pid)*1.0;
      if(k==="util") return numUtils(st,pid)*1.0;
      const arr=GROUPS[k]; let v=countIn(st,pid,arr);
      for(const p of arr) if(st.owner[p]===pid) v+=st.houses[p]*0.3;
      return v;
    });
  }
  function stratVec(key){ const s=STRATS[key]; return DKEYS.map(k=>(k in s.gv)?s.gv[k]:s.def); }
  function cosine(a,b){ let d=0,na=0,nb=0; for(let i=0;i<a.length;i++){ d+=a[i]*b[i]; na+=a[i]*a[i]; nb+=b[i]*b[i]; } return (na&&nb)? d/Math.sqrt(na*nb):0; }
  function detectStrategy(st,pid){
    const v=observedVec(st,pid); if(v.reduce((a,b)=>a+b,0)<1) return {key:null,name:"—",conf:0};
    let best=null,bc=-1,second=0;
    for(const key of Object.keys(STRATS)){ if(key==="balanced") continue; const c=cosine(v,stratVec(key));
      if(c>bc){ second=bc; bc=c; best=key; } else if(c>second) second=c; }
    const conf=Math.round(Math.max(0,Math.min(1, bc*(0.6+0.4*(bc-second))))*100);
    return {key:best, name:STRATS[best].name, conf};
  }
  function threatOf(st,pid){
    let bestG=null, bestRent=0, status="";
    for(const g of Object.keys(GROUPS)){ const arr=GROUPS[g], own=countIn(st,pid,arr);
      if(own<arr.length-1) continue;
      const full=own===arr.length; const potRent=arr.reduce((a,p)=>a+BOARD[p][5][3],0); // 3 domy
      if(potRent>bestRent){ bestRent=potRent; bestG=g; status=full?"KOMPLET":"−1 do kompletu"; } }
    return bestG?{group:bestG,status,potRent:bestRent}:null;
  }

  // ---------- Sugerowana linia (plan silnika, 2-ply lookahead) ----------
  function bestGroupToComplete(st,pid,exclude){
    let tg=null, tScore=-1, miss=[]; const s=STRATS[st.players[pid].strat]||STRATS.balanced;
    for(const g of Object.keys(GROUPS)){ if(exclude&&exclude.has(g)) continue;
      const arr=GROUPS[g], own=countIn(st,pid,arr);
      if(own===0||own===arr.length) continue;
      const val=(g in s.gv)?s.gv[g]:s.def, score=val*(own/arr.length);
      if(score>tScore){ tScore=score; tg=g; miss=arr.filter(p=>st.owner[p]!==pid); } }
    return tg?{g:tg, miss}:null;
  }
  function withGroup(st,pid,g){ const c=clone(st); for(const p of GROUPS[g]){ c.owner[p]=pid; c.houses[p]=3; } return c; }
  function bestLine(st,pid,n){
    n=n||130; const base=evaluate(st,n,777)[pid];
    const t1=bestGroupToComplete(st,pid,null);
    let projDelta=null, second=null, projDelta2=null, c1=null;
    if(t1){ c1=withGroup(st,pid,t1.g); projDelta=Math.round((evaluate(c1,n,777)[pid]-base)*100);
      const t2=bestGroupToComplete(c1,pid,new Set([t1.g]));
      if(t2){ const c2=withGroup(c1,pid,t2.g); second=t2;
        projDelta2=Math.round((evaluate(c2,n,777)[pid]-base)*100); } }
    let worst=null,worstRent=0;
    for(const p of active(st)){ if(p.id===pid) continue; const t=threatOf(st,p.id); if(t&&t.potRent>worstRent){ worstRent=t.potRent; worst={id:p.id,name:p.name,t}; } }
    return {base:Math.round(base*100),
            targetGroup:t1?t1.g:null, missing:t1?t1.miss:[], projDelta,
            secondGroup:second?second.g:null, secondMissing:second?second.miss:[], projDelta2,
            threat:worst};
  }

  // ---------- Referencyjne ROI (model Markowa — dochód na rzut przeciwnika) ----------
  // Źródło: analiza łańcuchów Markowa (UIUC) — dochód $/rzut przy 3 domach i hotelu.
  const MARKOV_EV = {
    green:{h3:68.22, hotel:96.25}, yellow:{h3:61.53, hotel:87.91},
    red:{h3:58.41, hotel:86.87}, darkblue:{h3:57.33, hotel:80.43},
    orange:{h3:47.81, hotel:81.52}, pink:{h3:38.0, hotel:63.0},
    lightblue:{h3:18.17, hotel:36.77}, brown:{h3:14.0, hotel:28.0},
    rail:{h3:null, hotel:20.35}, util:{h3:null, hotel:3.31},
  };
  function groupEV(group){ return MARKOV_EV[group] || null; }

  // ---------- Analiza planszy: częstotliwość lądowań (Monte Carlo pojedynczego pionka) ----------
  function landingFrequency(steps){
    steps=steps||400000; const rnd=mulberry32(12345); const land=new Array(40).fill(0);
    let pos=0, jail=false, dbl=0;
    const near=(p,t)=>{ for(let s=1;s<=40;s++){ if(t.includes((p+s)%40)) return (p+s)%40; } return t[0]; };
    for(let k=0;k<steps;k++){
      const a=1+Math.floor(rnd()*6), b=1+Math.floor(rnd()*6);
      if(jail){ if(a===b){ jail=false; dbl=0; } else { land[10]++; continue; } }
      if(a===b){ dbl++; if(dbl===3){ pos=10; jail=true; dbl=0; land[10]++; continue; } } else dbl=0;
      pos=(pos+a+b)%40; const typ=BOARD[pos][2];
      if(typ===G2J){ pos=10; jail=true; }
      else if(typ===CH){ const c=CHANCE[Math.floor(rnd()*16)], act=c[1], v=c[2];
        if(act==="move"||act==="advance") pos=v; else if(act==="back") pos=((pos-v)%40+40)%40;
        else if(act==="tojail"){ pos=10; jail=true; } else if(act==="nrail") pos=near(pos,RAILS); else if(act==="nutil") pos=near(pos,UTILS); }
      else if(typ===CC){ const c=CHEST[Math.floor(rnd()*16)]; if(c[1]==="move") pos=c[2]; else if(c[1]==="tojail"){ pos=10; jail=true; } }
      land[pos]++;
    }
    const tot=land.reduce((a,b)=>a+b,0)||1;
    return land.map(x=>100*x/tot);
  }

  // ---------- Masowa symulacja w przeglądarce (statystyki + wykresy) ----------
  function batchSim(specs, games, opts){
    opts=opts||{}; const cap=opts.maxRounds||160;
    const strolls=[...new Set(specs.map(s=>s.strat))];
    const wins={}, played={}, bankr={}, netSum={}; strolls.forEach(s=>{wins[s]=0;played[s]=0;bankr[s]=0;netSum[s]=0;});
    const lengths=[]; let totalRounds=0, finished=0, headStart=0;
    for(let g=0; g<games; g++){
      const rot=specs.map((_,i)=>specs[(i+g)%specs.length]);
      const st=newGame(rot.map((s,i)=>({name:s.strat+"#"+i, strat:s.strat, diff:s.diff||"trudny"})),
                       {startCash:opts.startCash||1500, goal:opts.goal||null});
      const rnd=mulberry32((g*2654435761+777)>>>0); let guard=0;
      while(!st.done && st.round<cap && guard<cap*st.players.length+50){ st.round++;
        for(const p of st.players){ if(p.bankrupt) continue; if(active(st).length<=1) break; aiTurn(st,p.id,rnd);
          const gw=checkGoalWinner(st); if(gw>=0){st.done=true;st.winner=gw;break;} if(st.done) break; }
        guard++;
      }
      let winner = (st.winner>=0)? st.players[st.winner]
                 : active(st).sort((a,b)=>netWorth(st,b.id)-netWorth(st,a.id))[0];
      wins[winner.strat]++; if(st.winner>=0||active(st).length<=1) finished++;
      lengths.push(st.round); totalRounds+=st.round;
      for(const p of st.players){ played[p.strat]++; netSum[p.strat]+=netWorth(st,p.id); if(p.bankrupt) bankr[p.strat]++; }
    }
    return {strategies:strolls, wins, played, bankr, netSum, lengths,
            avgRounds:totalRounds/games, finished, games};
  }

  // ---------- Turniej H2H (1v1) w przeglądarce ----------
  function duel(aKey, bKey, games, cap){
    cap=cap||160; let aWins=0;
    for(let g=0; g<games; g++){
      const spec = g%2===0 ? [{name:"A",strat:aKey},{name:"B",strat:bKey}]
                           : [{name:"B",strat:bKey},{name:"A",strat:aKey}];
      const aIdx = g%2===0?0:1;
      const st=newGame(spec,{}); const rnd=mulberry32((g*100003+7)>>>0); let guard=0;
      while(!st.done && st.round<cap && guard<cap*2+40){ st.round++;
        for(const p of st.players){ if(p.bankrupt)continue; if(active(st).length<=1)break; aiTurn(st,p.id,rnd); if(st.done)break; }
        guard++; }
      const winner = st.winner>=0? st.winner : active(st).sort((x,y)=>netWorth(st,y.id)-netWorth(st,x.id))[0].id;
      if(winner===aIdx) aWins++;
    }
    return aWins;
  }
  function _eloMatch(elo,a,b,sa,K){ const ea=1/(1+Math.pow(10,(elo[b]-elo[a])/400)); elo[a]+=K*(sa-ea); elo[b]+=K*((1-sa)-(1-ea)); }
  function _updateElo(elo,a,b,aw,bw,K){ K=K||8; let i=0,j=0;
    while(i<aw||j<bw){ const fa=aw?i/aw:1, fb=bw?j/bw:1;
      if(i<aw && (fa<=fb || j>=bw)){ _eloMatch(elo,a,b,1,K); i++; } else { _eloMatch(elo,a,b,0,K); j++; } } }
  function h2hTournament(keys, games){
    const n=keys.length, matrix={}, elo={}; keys.forEach(k=>{matrix[k]={};elo[k]=1500;});
    for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){ const a=keys[i],b=keys[j];
      const aw=duel(a,b,games); const wrA=100*aw/games; matrix[a][b]=wrA; matrix[b][a]=100-wrA;
      _updateElo(elo,a,b,aw,games-aw); }
    const avg={}; keys.forEach(k=>{ const vs=keys.filter(o=>o!==k); avg[k]=vs.reduce((s,o)=>s+matrix[k][o],0)/Math.max(1,vs.length); });
    return {keys, matrix, avg, elo};
  }

  const M = {
    BOARD, GROUPS, GROUP_COLORS, RAILS, UTILS, STRATS, DIFF, TYPES:{P,R,U,GO,TAX,CH,CC,JAIL,FP,G2J},
    MARKOV_EV, groupEV, meetsGoal, checkGoalWinner, landingFrequency, batchSim, duel, h2hTournament,
    canTrade, applyTrade, evalDealFor, botDecideTrade, detectStrategy, threatOf, bestLine, groupHasHouses,
    newGame, clone, active, propsOf, ownsFullGroup, fullGroups, numRails, numUtils, rentOf, netWorth,
    rollDice, moveBy, moveTo, landing, auction, tryBuild, tryTrades, aiTurn, jailTurn,
    aiShouldBuy, aiAuctionValue, aiLeaveJail, aiValue:aiAuctionValue,
    pay, raiseCash, sellHouse, mortgageOne, bankrupt, sendJail, groupKey, gv,
    evaluate, playout, mulberry32,
    dangerNext, monopolyProximity, liquidity,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = M;
  root.M = M;
})(typeof self !== "undefined" ? self : this);
