"""Stands in for runAiBot.py in worker tests. Behaviour picked by FAKE_BOT_MODE."""

import os
import sys
import time

mode = os.environ.get("FAKE_BOT_MODE", "print")

if mode == "print":
    for i in range(3):
        print(f"fake line {i}")
    sys.exit(0)

if mode == "settings":
    from config.search import search_terms
    from config.secrets import claude_api_key

    print(f"terms={search_terms}")
    print(f"has_key={bool(claude_api_key)}")
    sys.exit(0)

if mode == "crash":
    print("starting")
    print("Chrome failed to start: session not created", file=sys.stderr)
    sys.exit(1)

if mode == "ask":
    from modules import bridge

    print("asking")
    answer = bridge.ask("Needs you", "Solve the captcha", ["Done, continue"])
    print(f"answer={answer}")
    sys.exit(0)

if mode == "sleep":
    print("sleeping")
    time.sleep(60)
