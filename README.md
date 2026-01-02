# ShopRoute — Grocery item sorter

Small utility to order grocery items according to a store layout and
produce a bulleted shopping list. It uses a simple rule-based classifier
and an optional GenAI-backed fallback when the rule-based classifier
returns `Misc`.

## Files
- `backend/app/organize.py` — canonical implementation: classification,
  DB-backed store layout lookup, AI fallback, and CLI entrypoint.
- `backend/app/db.py` — sqlite-backed item cache and store-layout storage.
- `backend/app/` — contains the FastAPI backend and related modules.
- `tests/test_store_sort.py` — pytest tests (includes mocks for GenAI).

## Usage (library)
The canonical library entry is now `backend.app.organize.order_items` which
returns structured data (`dict` or list-of-groups depending on version).
For backwards compatibility, you can still import the top-level wrapper:
```
from store_sort import order_items
groups = order_items(store_id = 1, items=['Bananas','spinach','sourdough','milk'])
for g in groups:
  print(f"{g['zone']}:")
    for name in g['items']:
        print(f"- {name}")
    print("")
```

## CLI usage

- Run the canonical module directly (recommended):
```
python3 -m backend.app.organize --store ShopRite --zip 07006 --list "Bananas,spinach"
```

Notes:
- `--list` expects a single comma-separated string. Quoting is recommended
  for shell usage when items contain spaces.
- You can optionally pass `--zip` for postal-code specific layouts, or
  `--store_id` when you know the DB id.

Notes:
- `--list` expects a single comma-separated string. Quoting is recommended
  for shell usage when items contain spaces.

## GenAI / LLM fallback
If you set the environment variable `GEMENI_FREE_API` to a valid API key
and have the `google.genai` library available, the classifier will attempt
to call the GenAI model to get a JSON response with the schema:

```json
{ "category": "<category>", "normalized_name": "<name>" }
```

The code validates the returned JSON and falls back to a conservative
keyword heuristic if the API is unavailable or returns invalid output.

## Tests
Run tests with:
```
python3 -m pytest -q
```

The tests include mocks for the GenAI client so they don't require an
actual API key to run.

## Extending
 - Add store layouts using the DB helpers in `backend/app/db.py`.
 - Improve the heuristic buckets or AI prompt in `backend/app/organize.py`.
 - The FastAPI backend (see `backend/app/main.py`) exposes HTTP endpoints
   you can integrate with other apps or a web UI.

## Development / VS Code
 - Activate the project venv (example - adjust to your venv path):
```
source backend/app/venv/bin/activate
```
 - Install dependencies if you haven't already:
```
pip install -r requirements.txt
```
 - Ensure VS Code uses that interpreter (see `.vscode/settings.json`).

## Database
 - Initialize the sqlite DB (creates tables at repo-root `grocery_cache.db`):
```
python3 -c "from backend.app.db import init_db; init_db()"
```
 - You can add a store layout programmatically:
```
python3 - <<'PY'
from backend.app.db import add_store_layout
zones = [
  ("Produce", ["Produce"]),
  ("Dairy", ["Dairy"]),
]
add_store_layout("Wegmans","Wegmans", "Town", "ST", "07052", zones)
PY

## Running the FastAPI backend
From the repo root, while the venv is active:
```
uvicorn backend.app.main:app --reload
```

The backend exposes endpoints for querying store layouts and classification;
see `backend/app/main.py` for route details.

## License
Unlicensed — copy or adapt as you like for personal use.
