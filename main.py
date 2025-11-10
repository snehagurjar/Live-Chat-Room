import os
import random
import logging
from datetime import datetime
from typing import Dict

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    CHAT_ROOMS = ['General', 'Lets discuss DSA!', 'P for Python', 'Readers Chat', 'C Group']

app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
socketio = SocketIO(app, cors_allowed_origins=app.config['CORS_ORIGINS'], logger=True)

active_users: Dict[str, dict] = {}

def generate_guest_username():
    timestamp = datetime.now().strftime('%H%M')
    return f'Guest{timestamp}{random.randint(1000,9999)}'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if username:
            session['username'] = username
            return redirect(url_for('chat'))
    return render_template('username.html')

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('index.html', username=session['username'], rooms=app.config['CHAT_ROOMS'])

@socketio.event
def connect():
    try:
        if 'username' not in session:
            session['username'] = generate_guest_username()
        active_users[request.sid] = {'username': session['username'], 'connected_at': datetime.now().isoformat()}
        emit('active_users', {'users': [u['username'] for u in active_users.values()]}, broadcast=True)
        logger.info(f"{session['username']} connected")
    except Exception as e:
        logger.error(f"Connect error: {e}")
        return False

@socketio.event
def disconnect():
    try:
        if request.sid in active_users:
            username = active_users[request.sid]['username']
            del active_users[request.sid]
            emit('active_users', {'users': [u['username'] for u in active_users.values()]}, broadcast=True)
            logger.info(f"{username} disconnected")
    except Exception as e:
        logger.error(f"Disconnect error: {e}")

@socketio.on('join')
def on_join(data):
    try:
        username = session['username']
        room = data['room']
        join_room(room)
        active_users[request.sid]['room'] = room
        emit('status', {'msg': f'{username} joined the room.', 'type': 'join', 'timestamp': datetime.now().isoformat()}, room=room)
    except Exception as e:
        logger.error(f"Join error: {e}")

@socketio.on('leave')
def on_leave(data):
    try:
        username = session['username']
        room = data['room']
        leave_room(room)
        if request.sid in active_users:
            active_users[request.sid].pop('room', None)
        emit('status', {'msg': f'{username} left the room.', 'type': 'leave', 'timestamp': datetime.now().isoformat()}, room=room)
    except Exception as e:
        logger.error(f"Leave error: {e}")

@socketio.on('message')
def handle_message(data):
    try:
        username = session['username']
        room = data.get('room', 'General')
        message = data.get('msg', '').strip()
        if not message:
            return
        timestamp = datetime.now().isoformat()

        if data.get('type') == 'private':
            target_user = data.get('target')
            for sid, user_data in active_users.items():
                if user_data['username'] == target_user:
                    emit('private_message', {'msg': message, 'from': username, 'timestamp': timestamp}, room=sid)
                    return
        else:
            emit('message', {'msg': message, 'username': username, 'room': room, 'timestamp': timestamp}, room=room)
    except Exception as e:
        logger.error(f"Message error: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=app.config['DEBUG'])
