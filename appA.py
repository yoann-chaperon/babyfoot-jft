from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/equipe")
def equipe():
    return render_template("equipe.html")

@app.route("/statistique")
def statistique():
    return render_template("statistique.html")

@app.route("/interclub")
def interclub():
    return render_template("interclub.html")

@app.route("/export")
def export():
    return render_template("export.html")

@app.route("/player")
def pl():
    return render_template("player.html")

# -------------------------
# Base de donné
# -------------------------
SQLALCHEMY_DATABASE_URI = "sqlite:///instance/babyfoot.db"

# -------------------------
# Lancement serveur
# -------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5070, debug=True)