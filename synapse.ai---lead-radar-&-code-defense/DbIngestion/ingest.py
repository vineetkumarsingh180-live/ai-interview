#!/usr/bin/env python3
"""
DbIngestion entry point. Run with the backend virtualenv:

    backend/.venv/bin/python DbIngestion/ingest.py --help

It puts the backend (config, DB session, ORM models, module public interfaces) and this package on
sys.path, then hands over to dbingestion.cli.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))
sys.path.insert(0, HERE)

from dbingestion.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
