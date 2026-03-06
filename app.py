from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import datetime, os
from werkzeug.utils import secure_filename

# ---- Config ----
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///babyfoot.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
UPLOAD_FOLDER = "static/img"
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)
socketio = SocketIO(app)

# ---- Modeles ----
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    photo = db.Column(db.String(200), default="/static/img/default.png")
    duel = db.Column(db.Integer, default=0)
    goal = db.Column(db.Integer, default=0)
    matches = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    p1 = db.Column(db.Integer)
    p2 = db.Column(db.Integer)
    s1 = db.Column(db.Integer)
    s2 = db.Column(db.Integer)
    type = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.datetime.now)

# ---- Création base ----
with app.app_context():
    db.create_all()

# ---- Helpers ----
def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

# ---- Routes ----
@app.route("/")
def index():
    players = Player.query.all()
    return render_template("index.html", players=players)

@app.route("/add_player", methods=["POST"])
def add_player():
    name = request.form.get("name")
    if not name:
        return "Nom joueur manquant", 400

    # Upload image
    file = request.files.get("photo")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        photo_path = "/" + filepath.replace("\\","/")
    else:
        photo_path = "/static/img/default.png"

    player = Player(name=name, photo=photo_path)
    db.session.add(player)
    db.session.commit()
    return redirect("/")

@app.route("/add_match", methods=["POST"])
def add_match():
    # Récupérer champs
    p1_raw = request.form.get("p1")
    p2_raw = request.form.get("p2")
    s1_raw = request.form.get("s1")
    s2_raw = request.form.get("s2")
    t = request.form.get("type")

    # Vérifications
    if None in [p1_raw,p2_raw,s1_raw,s2_raw,t]:
        return "Bad request : champs manquants", 400

    try:
        p1 = int(p1_raw)
        p2 = int(p2_raw)
        s1 = int(s1_raw)
        s2 = int(s2_raw)
    except ValueError:
        return "Bad request : IDs ou scores invalides", 400

    if p1 == p2:
        return "Impossible qu’un joueur s’affronte lui-même", 400

    if not (0 <= s1 <=3) or not (0 <= s2 <=3):
        return "Scores max 3 points", 400

    # Enregistrer le match
    m = Match(p1=p1,p2=p2,s1=s1,s2=s2,type=t)
    db.session.add(m)

    pl1 = Player.query.get(p1)
    pl2 = Player.query.get(p2)

    pl1.matches += 1
    pl2.matches += 1

    if t=="DUEL":
        pl1.duel += s1
        pl2.duel += s2
    else:
        pl1.goal += s1
        pl2.goal += s2

    if s1 > s2:
        pl1.wins += 1
        pl2.losses += 1
    else:
        pl2.wins += 1
        pl1.losses += 1

    db.session.commit()
    socketio.emit("refresh")
    return redirect("/")

@app.route("/global")
def global_view():
    players = Player.query.order_by((Player.duel + Player.goal).desc()).all()
    return render_template("global.html", players=players)

@app.route("/player/<int:id>")
def player(id):
    p = Player.query.get(id)
    if not p:
        return "Joueur introuvable", 404
    return render_template("player.html", player=p)

# ---- Main ----
if __name__=="__main__":
    socketio.run(app, host="0.0.0.0", port=5070, debug=True)