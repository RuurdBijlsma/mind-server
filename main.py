import socketio
import eventlet

# create a Socket.IO server
sio = socketio.Server(cors_allowed_origins='*')
app = socketio.WSGIApp(sio)


@sio.event
def connect(sid, environ):
    print('connect sid:', sid)
    sio.emit("hello", "world")


@sio.event
def disconnect(sid):
    print('disconnect sid:', sid)


@sio.event
def hello(sid, data):
    print(f"Received hello event sid: {sid} data: {data}")
    return "i received your hello :)"


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
