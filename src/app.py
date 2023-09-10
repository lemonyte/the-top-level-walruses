import datetime
import os

from flask import Flask, render_template
from flask_socketio import SocketIO

from piet import ImageGenerator

app = Flask(__name__)
socketio = SocketIO(app)


@app.route("/")
def index():
    if os.path.exists(os.path.join(os.getcwd(), "src/static/img/", "curimg.png")):
        os.remove(os.path.join(os.getcwd(), "src/static/img/", "curimg.png"))
    return render_template("editor.html")


@socketio.on("code")
def handle_code(code):
    generator = ImageGenerator()
    socketio.emit("result", "Generating image...")
    encoded = generator.generate_image(bytes(code, encoding="utf-8"), 4)
    encoded.save(os.path.join(os.getcwd(), "src/static/img/", "curimg.png"))
    # Process and execute the code (add security measures)
    socketio.emit("result", "Generated Image:")
    socketio.emit("cachebreaker", str(datetime.datetime.now()))


if __name__ == "__main__":
    socketio.run(app, debug=True)
