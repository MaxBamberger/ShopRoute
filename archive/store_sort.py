"""Compatibility wrapper for legacy `store_sort` import path.

This module forwards key symbols to `backend.app.classify` so external
scripts using `import store_sort` continue to work after the refactor.
"""

from backend.app import organize as _classify
from backend.app.db import get_store_layout as get_store_layout

# Re-export commonly-used functions
order_items = _classify.order_items
classify_item_with_cache = _classify.classify_item_with_cache
ai_fallback_classify = _classify.ai_fallback_classify

__all__ = [
    'order_items', 'classify_item_with_cache', 'ai_fallback_classify', 'get_store_layout'
]

from typing import List, Dict, Tuple
import os
import json
import argparse
import warnings
# Suppress the urllib3 NotOpenSSLWarning by matching its message text.
# Avoid importing urllib3.exceptions (which can itself trigger the warning),
# so filter by message substrings instead.
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
warnings.filterwarnings("ignore", message="NotOpenSSLWarning")
import re
import sys
from archive.db import get_cached_item, cache_item, get_store_layout
from collections import defaultdict

HEURISTIC_BUCKETS = [
        ('Meat', ['chicken', 'beef', 'pork', 'steak', 'bacon', 'sausage', 'turkey', 'ham', 'lamb']),
        ('Seafood', ['salmon', 'shrimp', 'tuna', 'cod', 'crab', 'lobster', 'scallop']),
        ('Produce', ['banana', 'apple', 'spinach', 'lettuce', 'tomato', 'onion', 'potato', 'carrot', 'berry', 'fruit', 'vegetable']),
        ('Dairy', ['milk', 'yogurt', 'cheese', 'butter', 'cream', 'eggs', 'egg']),
        ('Bakery', ['bread', 'bagel', 'sourdough', 'bun', 'roll', 'croissant']),
        ('Frozen', ['ice cream', 'popsicle', 'frozen', 'ice-cream', 'icecream']),
        ('Pantry', ['rice', 'pasta', 'canned', 'beans', 'sauce', 'oil', 'vinegar', 'flour', 'sugar', 'spice', 'cereal']),
        ('Snacks', ['chip', 'chips', 'cracker', 'cookie', 'chocolate', 'popcorn', 'granola']),
        ('Beverages', ['juice', 'soda', 'cola', 'water', 'beer', 'wine', 'coffee', 'tea']),
        ('Household', ['detergent', 'paper towel', 'toilet paper', 'trash bag', 'cleaner', 'bleach', 'dish soap']),
        ('Personal Care', ['shampoo', 'soap', 'toothpaste', 'deodorant', 'razor', 'lotion', 'conditioner']),
    ]

def _parse_dict_from_ai_response(response_text):
    """
    Extracts the 'category' value from a markdown-formatted JSON response.
    """
    # 1. Use regex to find the JSON content between the triple backticks
    # The pattern r'```json\n(.*?)```' looks for '```json\n', captures everything non-greedy (.*?)
    # until it hits the closing '```'. The re.DOTALL flag ensures it works across multiple lines.
    match = re.search(r'```json\n(.*?)```', response_text, re.DOTALL)

    if match:
        json_string = match.group(1).strip()
        
        # 2. Use the json library to parse the string into a Python dictionary
        try:
            data_dict = json.loads(json_string)
            
            return data_dict
            
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON")
            return None
    else:
        print("Error: Could not find JSON block in response")
        return None


def _prettify_name(name: str) -> str:
    """Make a readable form of an item name (small heuristic)."""
    return name.strip().title()

def _call_llm(prompt: str, api_key: str, model: str, debug: bool) -> Tuple[str, str]:
    """Helper to call GenAI LLM with given prompt and return text response."""
    # Import genai at call time so tests can monkeypatch `google.genai` after
    # this module is imported.
    try:
        from google import genai
    except Exception:
        if debug:
            print('[STORE_SORT DEBUG] google.genai import failed', file=sys.stderr)
        return 'NO_CLIENT', ''

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        if debug:
            print('\n[STORE_SORT DEBUG] GenAI API response (truncated):', file=sys.stdout)
            print(response.text, file=sys.stdout)
        return 'OK', response.text
    except Exception as e:
        # Determine if the raised exception is the genai client-specific error
        client_error_cls = None
        try:
            errs = getattr(genai, 'errors', None)
            if errs is not None:
                client_error_cls = getattr(errs, 'ClientError', None)
        except Exception:
            client_error_cls = None

        if client_error_cls is not None and isinstance(e, client_error_cls):
            if debug:
                print(f'[STORE_SORT DEBUG] GenAI ClientError for model {model}:', file=sys.stderr)
                print(e, file=sys.stderr)
            return 'RESOURCE_EXHAUSTED', ''

        if debug:
            print(f'[STORE_SORT DEBUG] GenAI call exception for model {model}:', file=sys.stderr)
            print(e, file=sys.stderr)
        return 'EXCEPTION', ''
    

def ai_fallback_classify(item: str) -> Tuple[str, str]:
    """AI-backed fallback classifier.

    This is called only when `classify_item` returned 'Misc'. It will
    attempt to call Google GenAI using the API key in the `GEMENI_FREE_API`
    environment variable and the `google.genai` library. The prompt asks
    the model to return ONLY a JSON object matching the schema:
    {"category": "<category>", "normalized_name": "<name>"}.

    If the API/key/library is unavailable or the model response cannot be
    parsed/validated, the function falls back to a conservative keyword
    heuristic. The heuristic never invents items and prefers 'Misc' when
    uncertain.
    """
    lowered = item.strip().lower()

    api_key = os.getenv('GEMENI_FREE_API')
    debug = bool(os.getenv('STORE_SORT_DEBUG'))
    primary_model = os.getenv('GEMENI_PRIMARY_MODEL', 'gemini-2.5-flash')
    alternative_model = os.getenv('GEMENI_ALTERNATIVE_MODEL', 'gemini-2.5-flash-lite')
    upgrade_model = os.getenv('GEMENI_UPGRADE_MODEL', 'gemini-2.5-pro')

    if api_key:

        prompt = (
            "You are a grocery categorization assistant. "
            "Classify the following grocery item into ONE of these categories: "
            "Produce, Meat, Seafood, Dairy, Bakery, Frozen, Pantry, Snacks, "
            "Beverages, Household, Personal Care, Misc.\n\n"
            "Return ONLY a JSON object with the exact schema:\n"
            "{\n  \"category\": \"<category>\",\n  \"normalized_name\": \"<name>\"\n}\n\n"
            "Rules: do NOT invent items; do NOT include brand names unless essential; "
            "if uncertain choose \"Misc\"; normalized_name must be 1-3 words.\n\n"
            f"Item: \"{item}\"\n\nRespond with JSON only."
        )

        cat = None
        norm = None
        data_dict = None
        status, response_text = _call_llm(model=primary_model, prompt=prompt, api_key=api_key, debug=debug)
        
        if status == 'RESOURCE_EXHAUSTED':
            # If the primary model fails because of resource limits, try alternative model
            if debug:
                print(f'[STORE_SORT DEBUG] GenAI primary model resource exhausted for \'{item}\', trying alternative model', file=sys.stderr)
            status, response_text = _call_llm(model=alternative_model, prompt=prompt, api_key=api_key, debug=debug)

        if status == 'OK':
            data_dict = _parse_dict_from_ai_response(response_text)
        else:
            if debug:
                print(f'[STORE_SORT DEBUG] GenAI API call failed for \'{item}\' categorization, trying generate_text fallback', file=sys.stderr)
        
        if data_dict:
            cat = _prettify_name(data_dict.get('category'))
            norm = _prettify_name(data_dict.get('normalized_name'))
            allowed = {
                'Produce', 'Meat', 'Seafood', 'Dairy', 'Bakery', 'Frozen', 'Pantry',
                'Snacks', 'Beverages', 'Household', 'Personal Care', 'Misc'
            }

            if cat[:4] == 'Misc':
                # Try upgrade model for better specificity
                status, response_text = _call_llm(model=upgrade_model, prompt=prompt, api_key=api_key, debug=debug)
                if status == 'OK':
                    data_dict = _parse_dict_from_ai_response(response_text)
                    if data_dict:
                        cat = _prettify_name(data_dict.get('category'))
                        norm = _prettify_name(data_dict.get('normalized_name'))

            if isinstance(cat, str) and cat in allowed and isinstance(norm, str):
                norm = ' '.join(norm.split()[:3])
                return cat, norm
            else:
                if debug:
                    print('[STORE_SORT DEBUG] GenAI returned invalid category/normalized_name:', file=sys.stderr)
                    print(data_dict, file=sys.stderr)


    # Fallback heuristic / Fuzzy Logic (conservative)
    for cat, keywords in HEURISTIC_BUCKETS:
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in lowered:
                norm = _prettify_name(item)
                norm = ' '.join(norm.split()[:3])
                return cat, norm

    norm = _prettify_name(item)
    norm = ' '.join(norm.split()[:3])
    return 'Misc', norm

def classify_item_with_cache(item: str):
    item_key = item.strip().lower()

    # Cache lookup
    cached = get_cached_item(item_key)
    if cached:
        return (
            cached["category"],
            cached["normalized_name"],
            cached["source"]
        )

    # AI fallback
    try:
        category, norm = ai_fallback_classify(item)
        if category != "Misc":
            cache_item(item_key, category, norm, source="ai")
        return category, norm, "ai"
    except Exception:
        # Safe fallback
        # cache_item(item_key, "Misc", norm, source="fallback")
        return "Misc", _prettify_name(item_key), "fallback"

def order_items(store: str, items: List[str], postal_code: str = None) -> List[str]:
    """Group and order `items` according to `store` layout.

    Returns a list of lines (strings) representing the bulleted output.
    Use "\n".join(...) to print as a multi-line bulleted list.
    """
    # Determine store layout: prefer DB-backed store layout when a postal code is provided
    if postal_code:
        db_layout = get_store_layout(store, postal_code)
        
    else:
        db_layout = get_store_layout(store)

    if not db_layout:
            raise ValueError(f"Unknown store layout for: {store} @ Zip: {postal_code}")
    # db_layout is a list of (zone_name, [categories]) in order. Flatten
    # categories while preserving first-seen order.
    seen = set()
    layout = []
    for _zone, cats in db_layout:
        for c in cats:
            if c not in seen:
                seen.add(c)
                layout.append(c)

    grouped: Dict[str, List[str]] = defaultdict(list)

    for item in items:
        # Use cache-backed classification as the single entry point. It will
        # consult DB cache, apply rule-based logic, and call AI fallback when
        # necessary. The function returns (category, normalized_name, source).
        cat, norm, _source = classify_item_with_cache(item)

        grouped[cat].append(norm)

    # Build output following the store layout order; any extra categories
    # (including 'Misc') come at the end in alphabetical order.
    lines: List[str] = []
    used = set()

    for cat in layout:
        if cat in grouped and grouped[cat]:
            lines.append(f"{cat}:")
            for name in grouped[cat]:
                lines.append(f"- {name}")
            lines.append("")
            used.add(cat)

    # Remaining categories not present in layout
    remaining = [c for c in grouped.keys() if c not in used]
    for cat in sorted(remaining):
        lines.append(f"{cat}:")
        for name in grouped[cat]:
            lines.append(f"- {name}")
        lines.append("")

    # Trim trailing blank line
    if lines and lines[-1] == "":
        lines = lines[:-1]

    return lines


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Order grocery items by store layout and print a bulleted list.'
    )
    parser.add_argument('--store', '-s', help='Store key (e.g., TRADER_JOES)')
    parser.add_argument('--list', '-l', help='Comma-separated list of items (single string).', type=str)
    parser.add_argument('--zip', '-z', help='Postal code / ZIP for store layout lookup (optional).', type=str)

    # positional fallback (kept for convenience)
    parser.add_argument('pos_store', nargs='?', help='Positional store (fallback)')
    parser.add_argument('pos_items', nargs='*', help='Positional items (fallback)')

    args = parser.parse_args()

    # If no args given at all, run the built-in example (convenience)
    if not (args.store or args.list or args.pos_store or args.pos_items):
        example_store = 'ShopRite'
        example_zip = '07052'
        example_items = [
            'Bananas',
            'spinach',
            'sour dough',
            'greek yogurt',
            'ice cream',
            'milk',
        ]
        print("\n".join(order_items(example_store, example_items, postal_code=example_zip)))
        raise SystemExit(0)

    # Determine store: prefer --store flag, then positional
    store_val = args.store or args.pos_store
    if not store_val:
        parser.error('store must be provided via --store or as the first positional argument')

    # Postal code from CLI (optional)
    postal_code = args.zip or None

    # Determine items: prefer --list flag (comma-separated string), then positional items
    parsed_items: List[str] = []
    if args.list:
        parsed_items = [p.strip() for p in args.list.split(',') if p.strip()]
    else:
        raw_tokens = args.pos_items
        if not raw_tokens:
            parser.error('items must be provided via --list or as positional arguments')
        parsed_items = raw_tokens

    lines = order_items(store_val, parsed_items, postal_code=postal_code)
    print("\n".join(lines))
