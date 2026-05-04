from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
import uvicorn


app = FastAPI()

# serve the index.html
@app.get("/")
async def get():
    return FileResponse("index.html")

# establish websocket connection
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected via WebSocket.")
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except Exception as e:
        print(f"Connection closed: {e}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)