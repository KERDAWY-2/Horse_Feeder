import asyncio
import websockets
from flask import Flask, Response
from threading import Thread
import os

# Config
WS_PORT = 3001
HTTP_PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(BASE_DIR, "current_frame.jpg")

# Shared frame buffer
latest_frame = None
frame_lock = asyncio.Lock()

# Flask app for serving stream
app = Flask(__name__)

@app.route('/')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    """Serve frames as Motion JPEG"""
    global latest_frame
    while True:
        if latest_frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')

# WebSocket handler
async def handle_client(websocket):
    global latest_frame
    print(f"Client connected: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            # Skip non-binary or small frames
            if not isinstance(message, (bytes, bytearray)) or len(message) < 5000:
                continue
            
            # Update frame in memory (no disk writes)
            latest_frame = message
            
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

# WebSocket server
async def websocket_server():
    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        WS_PORT,
        max_size=5_000_000,
        ping_interval=None
    ):
        print(f"WebSocket server running on port {WS_PORT}")
        await asyncio.Future()

# Run Flask in thread
def run_flask():
    app.run(host='0.0.0.0', port=HTTP_PORT, debug=False, threaded=True)

# Main
if __name__ == "__main__":
    print("Starting server...")
    
    # Start Flask in background
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start WebSocket server
    asyncio.run(websocket_server())
