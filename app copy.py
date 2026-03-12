from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
from itertools import combinations
import datetime, os

# ----------------------------
# ANCHOR CONFIG
# ----------------------------

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///babyfoot.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = "static/img/equipe"
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)
socketio = SocketIO(app)

# ----------------------------
# ANCHOR MODELES
# ----------------------------

class Player(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    photo = db.Column(db.String(200), default="/static/img/default.png")

    sexe = db.Column(db.String(1), default="M")

    actif = db.Column(db.Boolean, default=True)

    force_team_b = db.Column(db.Boolean, default=False)

    card_background = db.Column(db.String(200))

    duel = db.Column(db.Integer, default=0)

    goal = db.Column(db.Integer, default=0)

    goal_won = db.Column(db.Integer, default=0)

    matches = db.Column(db.Integer, default=0)

    wins = db.Column(db.Integer, default=0)

    losses = db.Column(db.Integer, default=0)

    elo = db.Column(db.Integer, default=1000)

    membre_club = db.Column(db.Boolean, default=True)

    interclub = db.Column(db.Boolean, default=False)

    interclub_wins = db.Column(db.Integer, default=0)

    atelier_duel = db.Column(db.Boolean, default=True)

    atelier_goal = db.Column(db.Boolean, default=True)

    external_club = db.Column(db.String(100))

    club_logo = db.Column(db.String(200))

    dette = db.Column(db.Float, default=0)

class Match(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    date = db.Column(db.String(20))

    playerA_id = db.Column(db.Integer, db.ForeignKey('player.id'))

    playerB_id = db.Column(db.Integer, db.ForeignKey('player.id'))

    playerA = db.relationship("Player", foreign_keys=[playerA_id])

    playerB = db.relationship("Player", foreign_keys=[playerB_id])

    scoreA = db.Column(db.Integer)

    scoreB = db.Column(db.Integer)

    type = db.Column(db.String(10))
class DetteTransaction(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))

    montant = db.Column(db.Float)

    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    description = db.Column(db.String(100))

    joueur = db.relationship("Player")
    
# créer la table si elle n’existe pas
with app.app_context():
    db.create_all()
    
# ----------------------------
# ANCHOR SETUP BASE + DETTE_TRANSACTION CLEAN
# ----------------------------
with app.app_context():
    # 1️⃣ Création de toutes les tables définies dans les modèles
    db.create_all()

    # 2️⃣ Colonnes manquantes sur Player
    migrations_player = [
        ('sexe', 'TEXT', '"M"'),
        ('actif', 'BOOLEAN', '1'),
        ('force_team_b', 'BOOLEAN', '0'),
        ('card_background', 'TEXT', 'NULL'),
        ('elo', 'INTEGER', '1000'),
        ('dette', 'FLOAT', '0')
    ]

    for col, col_type, default in migrations_player:
        try:
            db.session.execute(
                db.text(f'ALTER TABLE player ADD COLUMN {col} {col_type} DEFAULT {default}')
            )
            db.session.commit()
        except Exception:
            db.session.rollback()  # colonne existe déjà, ok

    # 3️⃣ Supprime la table DetteTransaction si elle existe (old/broken)
    try:
        db.session.execute(db.text("DROP TABLE IF EXISTS dette_transaction"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # 4️⃣ Création propre de la table DetteTransaction
    try:
        db.session.execute(db.text("""
            CREATE TABLE dette_transaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                montant FLOAT NOT NULL,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                FOREIGN KEY(player_id) REFERENCES player(id)
            )
        """))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Erreur création DetteTransaction:", e)

    # 5️⃣ Initialisation des dettes Player NULL
    try:
        db.session.execute(db.text("UPDATE player SET dette = 0 WHERE dette IS NULL"))
        db.session.commit()
    except Exception:
        db.session.rollback()
# ----------------------------
# ANCHOR CALCUL ELO
# ----------------------------

def update_elo(p1, p2, score1, score2):

    K = 32

    expected1 = 1 / (1 + 10 ** ((p2.elo - p1.elo) / 400))
    expected2 = 1 / (1 + 10 ** ((p1.elo - p2.elo) / 400))

    if score1 > score2:
        result1, result2 = 1, 0
    elif score2 > score1:
        result1, result2 = 0, 1
    else:
        result1 = result2 = 0.5

    p1.elo = int(p1.elo + K * (result1 - expected1))
    p2.elo = int(p2.elo + K * (result2 - expected2))


# ----------------------------
# ROUTES
# ----------------------------
# ANCHOR index
@app.route("/")
def index():

    duel = Player.query.filter_by(actif=True).order_by(Player.duel.desc()).limit(5).all()

    goal = Player.query.filter_by(actif=True).order_by(Player.goal.desc()).limit(5).all()

    elo = Player.query.filter_by(actif=True).order_by(Player.elo.desc()).limit(5).all()

    last_duel = Match.query.filter_by(type="DUEL").order_by(Match.date.desc()).first()

    last_goal = Match.query.filter_by(type="GOAL").order_by(Match.date.desc()).first()

    return render_template(
        "index.html",
        duel=duel,
        goal=goal,
        elo=elo,
        last_duel=last_duel,
        last_goal=last_goal
    )


from itertools import combinations

# ANCHOR admin
@app.route("/admin")
def admin():
    # Tous les joueurs
    players = Player.query.all()

    # Joueurs actifs interclub uniquement pour les matchs restants
    interclub_players = Player.query.filter_by(interclub=True, actif=True).all()

    # Tous les matchs existants
    matches = Match.query.order_by(Match.date.desc()).all()

    players_dict = {p.id: p for p in players}

    # Paires déjà jouées
    played_pairs = {
        (min(m.playerA_id, m.playerB_id), max(m.playerA_id, m.playerB_id), m.type)
        for m in matches if m.playerA_id and m.playerB_id
    }

    # Génération round-robin uniquement interclub
    remaining_matches = []
    for p1, p2 in combinations(interclub_players, 2):
        pair = (min(p1.id, p2.id), max(p1.id, p2.id))
        if (pair[0], pair[1], "DUEL") not in played_pairs:
            remaining_matches.append({"playerA_id": p1.id, "playerB_id": p2.id, "type": "DUEL"})
        if (pair[0], pair[1], "GOAL") not in played_pairs:
            remaining_matches.append({"playerA_id": p1.id, "playerB_id": p2.id, "type": "GOAL"})

    # Séparer Duel et Goal
    duel_remaining = [m for m in remaining_matches if m["type"] == "DUEL"]
    goal_remaining = [m for m in remaining_matches if m["type"] == "GOAL"]

    return render_template(
        "admin.html",
        players=players,
        matches=matches,
        players_dict=players_dict,
        remaining_matches=remaining_matches,
        duel_remaining=duel_remaining,
        goal_remaining=goal_remaining
    )

# ANCHOR toggle player
@app.route("/admin/player/toggle/<int:id>")
def toggle_player(id):

    player = Player.query.get_or_404(id)

    player.actif = not player.actif

    db.session.commit()

    return redirect("/admin")

# ANCHOR composition équipes
@app.route("/equipe")
def equipe():

    players = Player.query.filter_by(actif=True).all()

    players_sorted = sorted(
        players,
        key=lambda p: p.duel + p.goal,
        reverse=True
    )

    interclub_players = [p for p in players_sorted if p.interclub]

    teamA = [
        p for p in interclub_players
        if (p.duel + p.goal) >= 35 and not p.force_team_b
    ]

    if len(teamA) < 8:
        teamA = interclub_players[:8]

    teamB = [p for p in interclub_players if p not in teamA]

    club_players = [p for p in players_sorted if not p.interclub]

    return render_template(
        "equipe.html",
        teamA=teamA,
        teamB=teamB,
        club_players=club_players
    )

# ANCHOR add match
@app.route("/add_match", methods=["POST"])
def add_match():

    p1 = int(request.form.get("p1"))
    p2 = int(request.form.get("p2"))

    s1 = int(request.form.get("s1"))
    s2 = int(request.form.get("s2"))

    t = request.form.get("type")

    pl1 = Player.query.get(p1)
    pl2 = Player.query.get(p2)

    if not pl1 or not pl2:
        return "Joueur introuvable", 404

    if not pl1.actif or not pl2.actif:
        return "Un joueur est inactif", 400

    m = Match(
        playerA_id=p1,
        playerB_id=p2,
        scoreA=s1,
        scoreB=s2,
        type=t,
        date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    db.session.add(m)

    pl1.matches += 1
    pl2.matches += 1

    if t == "DUEL":
        pl1.duel += s1
        pl2.duel += s2
    else:
        pl1.goal += s1
        pl2.goal += s2

    if s1 > s2:
        pl1.wins += 1
        pl2.losses += 1
    elif s2 > s1:
        pl2.wins += 1
        pl1.losses += 1

    update_elo(pl1, pl2, s1, s2)

    db.session.commit()

    socketio.emit("refresh")

    return redirect("/")

# ANCHOR player profile
@app.route("/player/<int:id>")
def player(id):

    p = Player.query.get_or_404(id)

    all_players = Player.query.filter(
        Player.id != id,
        Player.actif == True
    ).all()

    matches = Match.query.filter(
        (Match.playerA_id == id) | (Match.playerB_id == id)
    ).all()

    duel_history = [m for m in matches if m.type == "DUEL"]
    goal_history = [m for m in matches if m.type == "GOAL"]

    duel_remaining = sorted(all_players, key=lambda pl: pl.duel, reverse=True)

    goal_remaining = sorted(all_players, key=lambda pl: pl.goal, reverse=True)

    if not p.membre_club and p.card_background:
        card_image = p.card_background

    elif not p.membre_club:
        card_image = "/static/img/cards/exterieur.png"

    elif not p.interclub:
        card_image = "/static/img/cards/violet.png"

    else:
        card_image = "/static/img/cards/gold.png"

    return render_template(
        "player.html",
        player=p,
        card_image=card_image,
        duel_remaining=duel_remaining,
        goal_remaining=goal_remaining,
        duel_history=duel_history,
        goal_history=goal_history
    )
# ANCHOR admin new player
@app.route("/admin/player/new", methods=["GET", "POST"])
def admin_new_player():

    import os

    # récupérer clubs existants
    clubs = db.session.query(Player.external_club).distinct().all()
    clubs = [c[0] for c in clubs if c[0]]

    # récupérer backgrounds externes
    cards_ext_path = os.path.join(app.root_path, "static/img/cards_ext")

    if os.path.exists(cards_ext_path):
        cards_ext = [f for f in os.listdir(cards_ext_path)
                        if f.lower().endswith((".png",".jpg",".jpeg",".gif"))]
    else:
        cards_ext = []

    if request.method == "POST":

        name = request.form.get("name")
        sexe = request.form.get("sexe")

        membre_club = "membre_club" in request.form
        interclub = "interclub" in request.form
        actif = "actif" in request.form
        force_team_b = "force_team_b" in request.form

        atelier_duel = "atelier_duel" in request.form if membre_club else False
        atelier_goal = "atelier_goal" in request.form if membre_club else False

        # ----------------
        # PHOTO
        # ----------------

        photo_file = request.files.get("photo")

        if photo_file and allowed_file(photo_file.filename):

            filename = secure_filename(photo_file.filename)

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            photo_file.save(filepath)

            photo = f"/static/img/equipe/{filename}"

        else:

            photo = "/static/img/default.png"

        # ----------------
        # CLUB
        # ----------------

        new_club = request.form.get("new_club")
        selected_club = request.form.get("external_club")

        external_club = None
        club_logo = None
        card_background = "/static/img/cards/default.png"

        if new_club:

            external_club = new_club
            club_logo = f"/static/img/logo/logo_{new_club}.png"
            card_background = f"/static/img/cards_ext/card_{new_club}.png"

        elif selected_club:

            external_club = selected_club
            club_logo = f"/static/img/logo/logo_{selected_club}.png"
            card_background = f"/static/img/cards_ext/card_{selected_club}.png"

        else:

            if sexe == "F":

                card_background = "/static/img/cards/rose.png"

            elif membre_club and not interclub and not actif:

                card_background = "/static/img/cards/ancien.png"

            elif membre_club and interclub and actif and force_team_b:

                card_background = "/static/img/cards/argent.png"

            elif membre_club and not interclub and actif:

                card_background = "/static/img/cards/bronze.png"

        # ----------------
        # CREATION JOUEUR
        # ----------------

        player = Player(
            name=name,
            sexe=sexe,
            membre_club=membre_club,
            interclub=interclub,
            actif=actif,
            force_team_b=force_team_b,
            atelier_duel=atelier_duel,
            atelier_goal=atelier_goal,
            photo=photo,
            external_club=external_club,
            club_logo=club_logo,
            card_background=card_background
        )

        db.session.add(player)
        db.session.commit()

        return redirect("/admin")

    # joueur vide pour éviter les erreurs Jinja
    dummy_player = Player(
        name="",
        sexe="M",
        photo="/static/img/default.png",
        membre_club=True,
        interclub=False,
        actif=True,
        atelier_duel=True,
        atelier_goal=True
    )

    return render_template(
        "admin_player_new.html",
        player=dummy_player,
        clubs=clubs,
        cards_ext=cards_ext
    )
    
# ANCHOR edit player
@app.route("/admin/player/edit/<int:id>", methods=["GET","POST"])
def edit_player(id):

    player = Player.query.get_or_404(id)

    # récupérer clubs existants
    clubs = db.session.query(Player.external_club).distinct().all()
    clubs = [c[0] for c in clubs if c[0]]

    if request.method == "POST":

        player.name = request.form.get("name")
        player.sexe = request.form.get("sexe")

        player.membre_club = "membre_club" in request.form
        player.interclub = "interclub" in request.form
        player.actif = "actif" in request.form
        player.force_team_b = "force_team_b" in request.form

        player.atelier_duel = "atelier_duel" in request.form if player.membre_club else False
        player.atelier_goal = "atelier_goal" in request.form if player.membre_club else False

        # ----------------
        # PHOTO
        # ----------------
        photo_file = request.files.get("photo")

        if photo_file and allowed_file(photo_file.filename):

            filename = secure_filename(photo_file.filename)

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            photo_file.save(filepath)

            player.photo = f"/static/img/equipe/{filename}"

        # ----------------
        # CLUB
        # ----------------

        new_club = request.form.get("new_club")
        selected_club = request.form.get("external_club")

        if new_club:

            player.external_club = new_club
            player.club_logo = f"/static/img/logo/logo_{new_club}.png"
            player.card_background = f"/static/img/cards_ext/card_{new_club}.png"

        elif selected_club:

            player.external_club = selected_club
            player.club_logo = f"/static/img/logo/logo_{selected_club}.png"
            player.card_background = f"/static/img/cards_ext/card_{selected_club}.png"

        else:

            player.external_club = None
            player.club_logo = None

        # ----------------
        # CARD BACKGROUND RULES
        # ----------------

        if not player.external_club:

            if player.sexe == "F":

                player.card_background = "/static/img/cards/rose.png"

            elif player.membre_club and not player.interclub and not player.actif:

                player.card_background = "/static/img/cards/ancien.png"

            elif player.membre_club and player.interclub and player.actif and player.force_team_b:

                player.card_background = "/static/img/cards/argent.png"

            elif player.membre_club and not player.interclub and player.actif:

                player.card_background = "/static/img/cards/bronze.png"

            else:

                player.card_background = "/static/img/cards/argent.png"

        db.session.commit()

        return redirect("/admin")

    return render_template(
        "admin_player_edit.html",
        player=player,
        clubs=clubs
    )

# ANCHOR admin match list
@app.route("/admin/match/list")
def admin_match_list():
    from flask import request

    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Joueurs pour affichage
    players = Player.query.all()
    players_dict = {p.id: p for p in players}

    # Pagination par type de match
    duel_pagination = Match.query.filter_by(type="DUEL").order_by(Match.date.desc()).paginate(page=page, per_page=per_page)
    goal_pagination = Match.query.filter_by(type="GOAL").order_by(Match.date.desc()).paginate(page=page, per_page=per_page)

    duel_matches = duel_pagination.items
    goal_matches = goal_pagination.items

    # Stats live
    total_matches = Match.query.count()
    duel_count = Match.query.filter_by(type="DUEL").count()
    goal_count = Match.query.filter_by(type="GOAL").count()
    top_elo = Player.query.order_by(Player.elo.desc()).first()

    return render_template(
        "admin_match_list.html",
        players_dict=players_dict,
        duel_matches=duel_matches,
        goal_matches=goal_matches,
        duel_pagination=duel_pagination,
        goal_pagination=goal_pagination,
        total_matches=total_matches,
        duel_count=duel_count,
        goal_count=goal_count,
        top_elo=top_elo
    )
    
# ANCHOR delete match
@app.route("/admin/match/delete/<int:id>")
def delete_match(id):
    match = Match.query.get_or_404(id)
    db.session.delete(match)
    db.session.commit()

    # Recalcul ELO de tous les joueurs
    recalculate_all_elo()
    return redirect("/admin/match/list")

def recalculate_all_elo():

    players = Player.query.all()

    for p in players:
        p.elo = 1000
        p.matches = 0
        p.wins = 0
        p.losses = 0
        p.duel = 0
        p.goal = 0

    matches = Match.query.order_by(Match.date.asc()).all()

    for m in matches:

        p1 = Player.query.get(m.playerA_id)
        p2 = Player.query.get(m.playerB_id)

        if not p1 or not p2:
            continue

        p1.matches += 1
        p2.matches += 1

        if m.type == "DUEL":
            p1.duel += m.scoreA
            p2.duel += m.scoreB
        else:
            p1.goal += m.scoreA
            p2.goal += m.scoreB

        if m.scoreA > m.scoreB:
            p1.wins += 1
            p2.losses += 1
        elif m.scoreB > m.scoreA:
            p2.wins += 1
            p1.losses += 1

        update_elo(p1, p2, m.scoreA, m.scoreB)

    db.session.commit()

# ANCHOR edit match
@app.route("/admin/match/edit/<int:id>", methods=["GET","POST"])
def edit_match(id):

    match = Match.query.get_or_404(id)

    if request.method == "POST":

        scoreA = max(0, min(3, int(request.form.get("scoreA"))))
        scoreB = max(0, min(3, int(request.form.get("scoreB"))))

        match.scoreA = scoreA
        match.scoreB = scoreB

        db.session.commit()

        # recalcul complet ELO et stats
        recalculate_all_elo()

        return redirect("/admin/match/list")

    players = Player.query.all()
    players_dict = {p.id: p for p in players}

    return render_template(
        "admin_match_edit.html",
        match=match,
        players_dict=players_dict
    )
    
#ANCHOR - admin player list
@app.route("/admin/player/list")
def admin_player_list():
    joueurs = Player.query.all()

    club_jft = [j for j in joueurs if j.membre_club]
    clubs_exterieurs = {}
    for j in joueurs:
        if not j.membre_club:
            clubs_exterieurs.setdefault(j.external_club or "Inconnu", []).append(j)

    return render_template(
        "admin_player_list.html",
        players=joueurs,
        club_jft=club_jft,
        clubs_exterieurs=clubs_exterieurs
    )


#ANCHOR - dettes
@app.route("/admin/dettes")
def admin_dettes():

    joueurs = Player.query.filter_by(
        membre_club=True,
        actif=True
    ).order_by(Player.dette.desc()).all()

    # TOP 5 dettes
    top_dettes = Player.query.filter(
        Player.membre_club == True,
        Player.actif == True,
        Player.dette > 0
    ).order_by(Player.dette.desc()).limit(5).all()

    # TOTAL DETTES
    total_dettes = db.session.query(db.func.sum(Player.dette)).scalar() or 0

    return render_template(
        "admin_dettes.html",
        joueurs=joueurs,
        top_dettes=top_dettes,
        total_dettes=total_dettes
    )

#ANCHOR - dette password
ADMIN_PASSWORD = "monsecret"  # à changer

#ANCHOR - fiche dette edit player
@app.route("/admin/dettes/add/<int:player_id>", methods=["POST"])
def add_dette(player_id):

    joueur = Player.query.get_or_404(player_id)

    montant = float(request.form["montant"])

    description = request.form.get("description","")

    joueur.dette = (joueur.dette or 0) + montant

    transaction = DetteTransaction(
        player_id = player_id,
        montant = montant,
        description = description
    )

    db.session.add(transaction)

    db.session.commit()

    return redirect("/admin/dettes")

#ANCHOR - admin dettes reset
@app.route("/admin/dettes/reset/<int:player_id>", methods=["POST"])
def reset_dette(player_id):

    joueur = Player.query.get_or_404(player_id)

    montant = -(joueur.dette or 0)

    transaction = DetteTransaction(
        player_id = player_id,
        montant = montant,
        description = "Paiement"
    )

    db.session.add(transaction)

    joueur.dette = 0

    db.session.commit()

    return redirect("/admin/dettes")

#ANCHOR - historique dettesæ 
@app.route("/admin/dettes/historique")
def historique_dettes():

    transactions = DetteTransaction.query.order_by(
        DetteTransaction.date.desc()
    ).limit(200).all()

    return render_template(
        "admin_dettes_historique.html",
        transactions=transactions
    )
    
# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":

    socketio.run(app, host="0.0.0.0", port=5070, debug=True)