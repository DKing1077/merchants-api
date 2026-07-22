from fastapi import FastAPI, Depends, Response, HTTPException
from pydantic import BaseModel


# simple pass a dataclass return route
app = FastAPI()
class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float

@app.get("/items/")
async def create_item(item: Item):
    return {"name": item.name, "price": item.price}

# depend on get db function, reurn yield, close
# def get_db():
#     db = DBSession()
#     try:
#         yield db
#     finally:
#         db.close()
#
# @app.get("/items/")
# async def read_items(db = Depends(get_db)):
#     items = db.get_items()
#     return items

# return routes
@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

@app.post("/items/")
async def create_item(item: Item):
    return {"name": item.name, "price": item.price}

@app.get("/users/{user_id}")
async def read_user(user_id: int):
    return {"user_id": user_id}

@app.get("/items/")
async def read_items(q: str = None):
    return {"q": q}
    return query

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    return {"item_id": item_id, "name": item.name, "price": item.price}

@app.post("/items/", status_code=201)
async def delete_item(item: Item):
    return item

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return Response(content=f"Item ID: {item_id}", media_type="text/plain")

# handling errors HTTP exceptions
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id not in item_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": item_db[item_id]}

# dependency injection
def get_db():
    try:
        db = Database.connect()
        yield db
    finally:
        db.disconnect()

def get_current_user(db=Depends(get_db)):
    user_id = db.get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    return user_id

 # route handlers
@app.get("/users/me")
def read_current_user(user_id: int = Depends(get_current_user)):
    return {"user_id": user_id}

# dependency hieracrhy
def get_api_key(db=Depends(get_db)):
    key = db.get_api_key()
    if not key:
        raise HTTPException(status_code=404, detail="API key not set")
    return key

@app.get("/data")
def read_data(api_key: str = Depends(get_api_key)):
    return {"data": "secret data"}


