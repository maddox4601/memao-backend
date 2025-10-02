from app import create_app
from extensions import socketio

app = create_app()
socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")
