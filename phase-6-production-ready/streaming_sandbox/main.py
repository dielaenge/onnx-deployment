from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
import uvicorn
import numpy as np

app = FastAPI()

# serve the index.html
@app.get("/")
async def get():
    return FileResponse("index.html")

@app.get("/processor.js")
async def get_processor():
    # get the processor.js file so the browser can load it
    return FileResponse("processor.js")

# establish websocket connection
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected via WebSocket.")
    
    audio_buffer = np.array([], dtype=np.float32)
    try:
        while True:
            # receive binary data from frontend
            raw_data = await websocket.receive_bytes()

            # convert bytes to float32 np array
            converted_data = np.frombuffer(raw_data, dtype=np.float32)
            
            # add 2 second converted_data (spliced in index.html's JavaScript) to rolling buffer
            audio_buffer = np.concatenate((audio_buffer, converted_data))

            #check if buffer has enough data for 4 seconds (required by onnx model)
            if len(audio_buffer) >= 64000:
                print(f"4 second window available. Ready to run inference\nRunning inference on shape: {audio_buffer.shape}")

                # TBD: will run inference at this point in production
                
                # confirm completed inference
                await websocket.send_text("DUMMY: Inference complete for window.")

                # slice buffer to keep the latter half of the window (2 seconds; which will be concatenated with new input if available)
                audio_buffer = audio_buffer[-32000:]

    except Exception as e:
        print(f"Connection closed: {e}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)