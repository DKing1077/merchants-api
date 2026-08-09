from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager

# web socket
app = FastAPI()
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")


# multiple web sockets management
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            self.active_connections.remove(websocket)

        async def broadcast(self, message: str):
            for connection in self.active_connections:
                await connection.send(message)

manager = ConnectionManager()

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("client disconnected")

# context manager
@asynccontextmanager
async def get_database_connection():
    conn = await database.connect()
    try:
        yield conn
    finally:
        await conn.close()

async def use_database():
    async with get_database_connection() as conn:
        result = await conn.fetch("SELECT * FROM users")
        data = await result.fetchall()
        print(data)

# decoupling and modularization
class WebSocketManager:
    def __init__(self):
        self.active_connections = []

        async def connect(self, websocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        async def broadcast(self, message):
            for websocket in self.active_connections:
                await websocket.send_text(message)

        async def disconnect(self, websocket):
            self.active_connections.remove(websocket)

websocket_manager = WebSocketManager()

@app.websocket('/ws/{user_id}')
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket_manager.broadcast(f"User {user_id} sent: {data}")
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)




