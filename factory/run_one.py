# -*- coding: utf-8 -*-
"""Run exactly one channel's daily step, right now.

    python run_one.py 2      pick -> chess_factory render -> upload -> advance
    python run_one.py 1      same, for science (factory.py)
    python run_one.py 3      same, for biography

Separate from daily_local.py so a single channel can be pushed without
re-rendering the other two.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_local

key = (sys.argv[1] if len(sys.argv) > 1 else "2").strip()
print(daily_local.do_channel(key))
