from fastapi import FastAPI, Query
from .models import OrganizeRequest, OrganizeResponse, StoreDetailRequest, StoreDetailsResponse
from .organize import order_items, get_store

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}

@app.post("/organize", response_model=OrganizeResponse)
def organize(req: OrganizeRequest) -> OrganizeResponse:
    groups = order_items(
        items=req.items,
        store_id=req.store_id
    )
    return OrganizeResponse(content=groups)

@app.get("/stores", response_model=StoreDetailsResponse)
def stores(
    store_name: str = Query(...,
        alias="name",
        min_length=2,
        description="Store name (e.g. Wegmans, ShopRite)"
    ),
    postal_code: str = Query(
        None, 
        alias="zip",
        pattern="^[0-9]{5}$",
        description="5-digit ZIP code"
    )) -> StoreDetailsResponse:
    details = get_store(
        store_name=store_name,
        postal_code=postal_code
    )
    return StoreDetailsResponse(**details)