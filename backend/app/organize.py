from collections import defaultdict
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

# Prefer package import, but allow running this file directly by adding
# the repository root to sys.path when `backend` isn't importable.
from app.db import get_cached_item, cache_item, get_store_layout, get_store_id, get_store_details

GENERIC_LAYOUT = [
    ('Produce', ['Produce']),
    ('Meat & Seafood', ['Meat', 'Seafood', 'Deli']),
    ('Bakery', ['Bakery']),
    ('Dairy', ['Dairy']),
    ('Frozen', ['Frozen']),
    ('Pantry', ['Pantry']),
    ('Snacks', ['Snacks']),
    ('Beverages', ['Beverages']),
    ('Household', ['Household']),
    ('Personal Care', ['Personal Care']),
]

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

ALLOWED_CATEGORIES = {'Produce', 'Meat', 'Seafood', 'Dairy', 'Bakery', 'Frozen', 'Pantry',
    'Snacks', 'Beverages', 'Household', 'Personal Care', 'Misc'}

DEBUG = bool(os.getenv('ORGANIZE_DEBUG'))

def _parse_dict_from_ai_response(response_text):
    match = re.search(r'```json\n(.*?)```', response_text, re.DOTALL)
    if match:
        json_string = match.group(1).strip()
        try:
            data_dict = json.loads(json_string)
            return data_dict
        except json.JSONDecodeError:
            return None
    return None


def _prettify_name(name: str) -> str:
    return name.strip().title()

def _call_llm(prompt: str, api_key: str, model: str, debug: bool) -> Tuple[str, str]:
    try:
        from google import genai
    except Exception:
        if debug:
            print('[DEBUG] google.genai import failed', file=sys.stderr)
        return 'NO_CLIENT', ''

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        if debug:
            print('\n[DEBUG] GenAI API response (truncated):', file=sys.stdout)
            print(response.text, file=sys.stdout)
        return 'OK', response.text
    except Exception as e:
        client_error_cls = None
        try:
            errs = getattr(genai, 'errors', None)
            if errs is not None:
                client_error_cls = getattr(errs, 'ClientError', None)
        except Exception:
            client_error_cls = None

        if client_error_cls is not None and isinstance(e, client_error_cls):
            if debug:
                print(f'[DEBUG] GenAI ClientError for model {model}:', file=sys.stderr)
                print(e, file=sys.stderr)
            return 'RESOURCE_EXHAUSTED', ''

        if debug:
            print(f'[DEBUG] GenAI call exception for model {model}:', file=sys.stderr)
            print(e, file=sys.stderr)
        return 'EXCEPTION', ''


def ai_fallback_classify(item: str) -> Tuple[str, str]:
    lowered = item.strip().lower()
    api_key = os.getenv('GEMENI_FREE_API')
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
        status, response_text = _call_llm(model=primary_model, prompt=prompt, api_key=api_key, debug=DEBUG)
        if status == 'RESOURCE_EXHAUSTED':
            if DEBUG:
                print(f'[DEBUG] GenAI primary model resource exhausted for \'{item}\', trying alternative model', file=sys.stderr)
            status, response_text = _call_llm(model=alternative_model, prompt=prompt, api_key=api_key, debug=DEBUG)

        if status == 'OK':
            data_dict = _parse_dict_from_ai_response(response_text)

        if data_dict:
            cat = _prettify_name(data_dict.get('category'))
            norm = _prettify_name(data_dict.get('normalized_name'))
            
            if cat[:4] == 'Misc':
                if DEBUG:
                    print(f"[DEBUG] llm returned 'Misc' for item '{item}', attempting upgrade model", file=sys.stderr)
                status, response_text = _call_llm(model=upgrade_model, prompt=prompt, api_key=api_key, debug=DEBUG)
                
                if status == 'OK':
                    data_dict = _parse_dict_from_ai_response(response_text)
                    if data_dict:
                        cat = _prettify_name(data_dict.get('category'))
                        norm = _prettify_name(data_dict.get('normalized_name'))

            if isinstance(cat, str) and cat in ALLOWED_CATEGORIES and isinstance(norm, str):
                norm = ' '.join(norm.split()[:3])
                return cat, norm
    else:
        if DEBUG:
            print('[DEBUG] GEMENI_FREE_API key not set, skipping AI classification', file=sys.stderr)

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
    cached = get_cached_item(item_key)
    if cached:
        return (
            cached["category"],
            cached["normalized_name"],
            cached["source"]
        )

    try:
        category, norm = ai_fallback_classify(item)
        if DEBUG:
            print('[DEBUG] AI classified item:', item, '->', category, '/', norm, file=sys.stderr)
        if category != "Misc":
            cache_item(item_key, category, norm, source="ai")
        return category, norm, "ai"
    except Exception:
        if DEBUG:
            print('[DEBUG] AI classification failed for item:', item, file=sys.stderr)
        return "Misc", _prettify_name(item_key), "fallback"

def get_store(store_name: str, postal_code: str = None):
    return get_store_details(store_name, postal_code)

def order_items(store_id: int = None, items: List[str] = []) -> List[dict]:
    """Classify items and return a mapping of category -> [normalized item names] 
    in order of store layout
    Input:
    store_id: int - Store identifier for layout lookup
    items: List[str] - List of item names to classify and group

    Returns:
    [
        {
            "zone": "Produce",
            "items": ["Bananas", "Apples"]
        },
        {
            "zone": "Dairy",
            "items": ["Milk", "Eggs"]
        }
    ]
    """
    # Determine store layout: prefer DB-backed store layout if available
    if store_id:
        db_layout = get_store_layout(store_id)
    else:
        print('No store_id provided, using GENERIC_LAYOUT', file=sys.stderr)
        db_layout = GENERIC_LAYOUT
        
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
        cat, norm, _source = classify_item_with_cache(item)
        if DEBUG:
            print(f"[DEBUG] Item '{item}' classified as Category '{cat}' with normalized name '{norm}'", file=sys.stderr)
        grouped[cat].append(norm)
    # Build output following the store layout order; any extra categories
    # (including 'Misc') come at the end in alphabetical order.
    output = []
    for cat in layout:
        if cat in grouped:
            output.append({
                "zone": cat,
                "items": grouped[cat]
            })
    remaining = [c for c in grouped.keys() if c not in layout]
    for cat in sorted(remaining):
        output.append({ 
            "zone": cat,
            "items": grouped[cat]
        })
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Order grocery items by store layout and print a bulleted list.'
    )
    parser.add_argument('--store_id', '-sid', help='Store id (e.g. 1 or 2).', type=str)
    parser.add_argument('--store', '-s', help='Store key (e.g. Wegmans or ShopRite).', type=str)
    parser.add_argument('--list', '-l', help='Comma-separated list of items (single string).', type=str)
    parser.add_argument('--zip', '-z', help='Postal code / ZIP for store layout lookup (optional).', type=str)

    parser.add_argument('pos_store', nargs='?', help='Positional store (fallback)')
    parser.add_argument('pos_items', nargs='*', help='Positional items (fallback)')

    args = parser.parse_args()

    if not args.store_id and args.store:
        try:
            args.store_id = get_store_id(store_name = args.store, postal_code = args.zip)
        except ValueError as ve:
            parser.error(str(ve))

    store_id = args.store_id

    parsed_items: List[str] = []
    if args.list:
        parsed_items = [p.strip() for p in args.list.split(',') if p.strip()]
    else:
        raw_tokens = args.pos_items
        if not raw_tokens:
            parser.error('items must be provided via --list or as positional arguments')
        parsed_items = raw_tokens

    output = order_items(store_id = store_id, items = parsed_items)
    for group in output:
        print(f"{group['zone']}:")
        for name in group['items']:
            print(f"- {name}")
        print("")
