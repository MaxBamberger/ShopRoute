import os
import sys

# Ensure the repository root is on sys.path so tests can import the
# `backend` package regardless of the current working directory pytest uses.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# Also add `backend` directory so modules that import top-level `app` (as
# `from app import ...`) resolve to `backend/app` during tests.
BACKEND_DIR = os.path.join(ROOT, 'backend')
if os.path.isdir(BACKEND_DIR) and BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
