# StoreRoute — Grocery item sorter

Small utility to order grocery items according to a store layout and
produce a bulleted shopping list. It uses a simple rule-based classifier
and an optional GenAI-backed fallback when the rule-based classifier
returns `Misc`.

## Files
- `store_sort.py` — main module. Exposes `order_items(store, items)` which
  returns a `List[str]` representing the bulleted output. The module also
  provides a CLI.
- `tests/test_store_sort.py` — pytest tests (includes mocks for GenAI).

## Usage (library)
```
from store_sort import order_items
lines = order_items('TRADER_JOES', ['Bananas', 'spinach', 'sourdough', 'milk'])
print('\n'.join(lines))
```

## CLI usage
You can run the script directly.

- Print the built-in example (no args):
```
python3 store_sort.py
```

- Use flags (preferred):
```
python3 store_sort.py --store TRADER_JOES --list "Bananas,spinach,sour dough,ice cream,milk"
```

- Short flags:
```
python3 store_sort.py -s TRADER_JOES -l "Bananas,spinach"
```

- Positional fallback (still supported):
```
python3 store_sort.py TRADER_JOES Bananas "sour dough" spinach
```

Notes:
- `--list` expects a single comma-separated string. Quoting is recommended
  for shell usage when items contain spaces.

## GenAI fallback
If you set the environment variable `GEMENI_FREE_API` to a valid API key
and have the `google.genai` library available, `store_sort.py` will attempt
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
- Add more stores to `STORE_LAYOUTS` in `store_sort.py`.
- Improve `ITEM_CLASSIFICATION` or the normalization map for better
  matching/pretty-printing.

## License
Unlicensed — copy or adapt as you like for personal use.
