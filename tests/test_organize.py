import pytest

import backend.app.db as db
import backend.app.organize as store_sort
from backend.app.organize import order_items

# DB-backed layout used for tests (matches previous hard-coded TRADER_JOES order)
TEST_TJ_LAYOUT = [
    ("Zone1", ["Produce"]),
    ("Zone2", ["Bakery"]),
    ("Zone3", ["Deli"]),
    ("Zone4", ["Pantry"]),
    ("Zone5", ["Beverages"]),
    ("Zone6", ["Dairy"]),
    ("Zone7", ["Frozen"]),
    ("Zone8", ["Household"]),
]


def test_order_example(monkeypatch):
    monkeypatch.setattr(store_sort, 'get_store_layout', lambda store_id: TEST_TJ_LAYOUT)
    items = ['Bananas', 'spinach', 'sour dough', 'greek yogurt', 'ice cream', 'milk']
    result = order_items(store_id=1, items=items)
    # Validate result is a list of dicts with 'zone' and 'items' keys
    result_dict = {z['zone']: z['items'] for z in result}
    
    assert 'Produce' in result_dict
    produce = [s.lower() for s in result_dict['Produce']]
    assert 'bananas' in produce
    assert 'spinach' in produce

    assert 'Bakery' in result_dict
    assert len(result_dict.get('Bakery', [])) > 0

    dairy = [s.lower() for s in result_dict.get('Dairy', [])]
    assert 'greek yogurt' in dairy
    assert 'milk' in dairy

    frozen = [s.lower() for s in result_dict.get('Frozen', [])]
    assert any('ice' in s and 'cream' in s for s in frozen)


def test_unknown_store_raises():
    # `order_items` with no store_id uses GENERIC_LAYOUT and classifies items.
    result = order_items(store_id=None, items=['milk'])
    result_dict = {z['zone']: z['items'] for z in result}
    assert 'Dairy' in result_dict
    assert any('milk' in s.lower() for s in result_dict.get('Dairy', []))


def test_misc_category_for_unmapped_item(monkeypatch):
    monkeypatch.setattr(store_sort, 'get_store_layout', lambda store_id: TEST_TJ_LAYOUT)
    result = order_items(store_id=1, items=['quirky item'])
    result_dict = {z['zone']: z['items'] for z in result}
    assert 'Misc' in result_dict
    assert any('quirky item' in s.lower() for s in result_dict.get('Misc', []))


def test_ai_fallback_uses_genai(monkeypatch):
    """When GEMENI_FREE_API is set and genai returns valid JSON, use it."""
    monkeypatch.setenv('GEMENI_FREE_API', 'fake-key')
    monkeypatch.setattr(store_sort, 'get_store_layout', lambda store_id: TEST_TJ_LAYOUT)
    import types, sys

    class DummyResp:
        def __init__(self, text):
            self.text = text

    class DummyClient:
        def __init__(self, api_key=None):
            self.models = types.SimpleNamespace(
                generate_content=lambda model, contents: DummyResp('```json\n{"category":"Produce","normalized_name":"Quirky Item"}\n```')
            )

        def generate(self, model, prompt):
            return DummyResp('{"category":"Produce","normalized_name":"Quirky Item"}')

    genai_mod = types.ModuleType('genai')
    genai_mod.Client = DummyClient
    genai_mod.generate_text = lambda model, input: DummyResp('```json\n{"category":"Produce","normalized_name":"Quirky Item"}\n```')

    google_mod = types.ModuleType('google')
    google_mod.genai = genai_mod

    monkeypatch.setitem(sys.modules, 'google', google_mod)
    monkeypatch.setitem(sys.modules, 'google.genai', genai_mod)

    # Ensure cache lookup does not short-circuit the AI path
    monkeypatch.setattr(store_sort, 'get_cached_item', lambda item: None)
    monkeypatch.setattr(store_sort, 'cache_item', lambda *args, **kwargs: None)

    result = order_items(store_id=1, items=['quirky item'])
    # AI mapped to Produce and used normalized name
    result_dict = {z['zone']: z['items'] for z in result}
    assert 'Produce' in result_dict
    assert any('quirky item' in s.lower() for s in result_dict.get('Produce', []))


def test_ai_fallback_invalid_response_then_heuristic(monkeypatch):
    """If genai returns invalid output, fallback heuristic should classify."""
    monkeypatch.setenv('GEMENI_FREE_API', 'fake-key')
    monkeypatch.setattr(store_sort, 'get_store_layout', lambda store_id: TEST_TJ_LAYOUT)
    import types, sys

    class DummyResp:
        def __init__(self, text):
            self.text = text

    class DummyClientBad:
        def __init__(self, api_key=None):
            pass

        def generate(self, model, prompt):
            return DummyResp('NOT JSON')

    genai_mod = types.ModuleType('genai')
    genai_mod.Client = DummyClientBad
    genai_mod.generate_text = lambda model, input: DummyResp('NOT JSON')

    google_mod = types.ModuleType('google')
    google_mod.genai = genai_mod

    monkeypatch.setitem(sys.modules, 'google', google_mod)
    monkeypatch.setitem(sys.modules, 'google.genai', genai_mod)

    # 'salmon fillet' should be classified by heuristic as Seafood
    result = order_items(store_id=1, items=['salmon fillet'])
    result_dict = {z['zone']: z['items'] for z in result}
    assert 'Seafood' in result_dict
    assert any('salmon' in s.lower() for s in result_dict.get('Seafood', []))
