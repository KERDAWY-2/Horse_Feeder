import asyncio
import websockets
from flask import Flask, Response
from threading import Thread, Lock
import time

# Config
WS_PORT = 3001
HTTP_PORT = 5000

# Frame buffer with lock
latest_frame = None
frame_lock = Lock()
frame_updated = False

app = Flask(__name__)

@app.route('/')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    """Non-blocking frame generator"""
    global latest_frame, frame_updated
    last_frame = None
    
    while True:
        with frame_lock:
            if latest_frame and latest_frame != last_frame:
                current = latest_frame
                last_frame = current
            else:
                current = last_frame
        
        if current:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + current + b'\r\n')
        
        time.sleep(0.033)  # 30 FPS max for viewers

async def handle_client(websocket):
    """Fast websocket handler - no blocking"""
    global latest_frame
    print(f"✓ Client connected")
    
    try:
        async for message in websocket:
            if isinstance(message, (bytes, bytearray)) and len(message) > 5000:
                # Fast non-blocking update
                with frame_lock:
                    latest_frame = message
                    
    except websockets.exceptions.ConnectionClosed:
        print("✗ Client disconnected")

async def websocket_server():
    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        WS_PORT,
        max_size=10_000_000,
        ping_interval=None,
        max_queue=2  # Limit queue to prevent buildup
    ):
        print(f"✓ WebSocket on port {WS_PORT}")
        await asyncio.Future()

def run_flask():
    app.run(host='0.0.0.0', port=HTTP_PORT, debug=False, threaded=True)

if __name__ == "__main__":
    print("Starting optimized server...")
    
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    asyncio.run(websocket_server())
