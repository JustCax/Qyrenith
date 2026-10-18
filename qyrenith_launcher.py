#!/usr/bin/env python3
"""Qyrenith public launcher.

The legacy qyrenith.py entrypoint remains supported for compatibility.
"""
from qyrenith import main

if __name__ == "__main__":
    raise SystemExit(main())
