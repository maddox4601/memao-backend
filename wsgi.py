from app import create_app
from extensions import socketio
from scheduler import start_scheduler

app = create_app()
start_scheduler(app)
socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")
