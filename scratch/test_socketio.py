import socketio
import time

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to server')

@sio.on('train_locations')
def on_train_locations(data):
    print(f'Received train_locations with {len(data)} trains')
    sio.disconnect()

@sio.on('disconnect')
def on_disconnect():
    print('Disconnected from server')

try:
    sio.connect('http://127.0.0.1:5001')
    sio.wait()
except Exception as e:
    print(f'Error: {e}')
