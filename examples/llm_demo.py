#!/usr/bin/env python3
"""
Demo: agent LLM (lokalne LM Studio) gra jedną partię Monopoly przeciw botom.

Najpierw w LM Studio wczytaj model i włącz Local Server (port 1234).
Potem:  python3 examples/llm_demo.py

Jeśli LM Studio nie działa, agent użyje heurystyki (gra się i tak zakończy).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monopoly.llm_agent import LLMAgent
from monopoly.agent import play_match
from monopoly.strategies import ALL_STRATEGIES


def main():
    llm = LLMAgent(verbose=True)
    if llm.check_connection():
        print("✅ Połączono z LM Studio — LLM podejmuje decyzje lokalnie.\n")
    else:
        print("⚠️  LM Studio niedostępne (localhost:1234) — agent gra heurystyką.\n")

    opponents = [ALL_STRATEGIES[k]() for k in ("kolejowy", "pomczerw", "monopolista")]
    res = play_match([llm] + opponents, seed=7, max_rounds=200)

    print(f"\nKONIEC: zwycięzca {res['winner'].name} [{res['winner_strategy']}], "
          f"{res['rounds']} rund.")
    for name, strat, worth, bankrupt in res["ranking"]:
        print(f"  {name:<16} majątek {worth:>6} {'BANKRUT' if bankrupt else ''}")


if __name__ == "__main__":
    main()
