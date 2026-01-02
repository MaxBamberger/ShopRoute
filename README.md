# ShopRoute — Grocery item sorter

Small utility to order grocery items according to a store layout and
produce a bulleted shopping list. It uses a simple rule-based classifier
and an optional GenAI-backed fallback when the rule-based classifier
returns `Misc`.

## Mobile App (NEW)

**Frontend**: Expo + React Native app located in `frontend/shoproute/`

**Features**:
- Store selection dropdown (Wegmans, ShopRite, Trader Joe's)
- Item input with comma-separated grocery items
- Organized shopping list by store zones
- Interactive checkboxes with strikethrough for completed items
- Auto-completion of categories (crossed out, grayed, moved to bottom)
- Real-time organization using backend API

**Setup**:
```bash
cd frontend/shoproute
npm install
npx expo start
# Press 'w' for web browser testing
```

## Files
- `backend/app/organize.py` — canonical implementation: classification,
  DB-backed store layout lookup, AI fallback, and CLI entrypoint.
- `backend/app/db.py` — sqlite-backed item cache and store-layout storage.
- `backend/app/main.py` — FastAPI backend with CORS for mobile app integration.
- `backend/app/` — contains the FastAPI backend and related modules.
- `frontend/shoproute/` — Expo React Native mobile application.
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
cd /path/to/ShopRoute
source venv/bin/activate
```
 - Install dependencies if you haven't already:
```
pip install -r backend/requirements.txt
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
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend exposes endpoints for querying store layouts and classification;
see `backend/app/main.py` for route details.

**CORS Configuration**: The backend includes CORS middleware to allow requests from the Expo development server (typically `localhost:8081`).

## Environment Variables
Set up environment variables for AI classification:
```bash
# Create .env file in backend directory
echo "GEMENI_FREE_API=your-api-key-here" >> backend/.env
echo "ORGANIZE_DEBUG=true" >> backend/.env
```

## Mobile App Development
The mobile app uses Expo + React Native and connects to the FastAPI backend:

**Key Features**:
- Store selection with dynamic layouts
- Interactive shopping list with checkboxes
- Completed categories auto-move to bottom
- Real-time item classification via API

**Development Workflow**:
1. Start backend: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
2. Start frontend: `cd frontend/shoproute && npx expo start`
3. Press 'w' for web development or scan QR code for mobile

## License
Unlicensed — copy or adapt as you like for personal use.
