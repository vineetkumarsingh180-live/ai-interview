import os
import sys

# Make `import app...` work when pytest is run from backend/ or the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
