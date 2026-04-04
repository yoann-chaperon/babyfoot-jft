
from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, case
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
from itertools import combinations
from datetime import datetime
from collections import defaultdict
import datetime, os

# ----------------------------
# ANCHOR CONFIG
# ----------------------------

app = Flask(__name__)

app.secret_key = "cle-secrete-super-random"

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
        
        card_video = db.Column(db.String(200), nullable=True)
        
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
        
        chbb = db.Column(db.Boolean, default=False)
        
        chbb_count = db.Column(db.Integer, default=3)

        chbb_date1 = db.Column(db.String(50))

        chbb_date2 = db.Column(db.String(50))

        chbb_date3 = db.Column(db.String(50))

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
# ANCHOR CREATION BASE
# ----------------------------

with app.app_context():

    db.create_all()

    migrations = [

        'ALTER TABLE player ADD COLUMN sexe TEXT DEFAULT "M"',
        'ALTER TABLE player ADD COLUMN actif BOOLEAN DEFAULT 1',
        'ALTER TABLE player ADD COLUMN force_team_b BOOLEAN DEFAULT 0',
        'ALTER TABLE player ADD COLUMN card_background TEXT',
        'ALTER TABLE player ADD COLUMN elo INTEGER DEFAULT 1000',
        'ALTER TABLE player ADD COLUMN dette FLOAT DEFAULT 0',
        'ALTER TABLE player ADD COLUMN chbb BOOLEAN DEFAULT 0',
        'ALTER TABLE joueur ADD COLUMN chbb_count INTEGER DEFAULT 3',
        'ALTER TABLE joueur ADD COLUMN chbb_date1 TEXT',
        'ALTER TABLE joueur ADD COLUMN chbb_date2 TEXT',
        'ALTER TABLE joueur ADD COLUMN chbb_date3 TEXT',
        'ALTER TABLE player ADD COLUMN card_video TEXT'

    ]

    for m in migrations:
        try:
            db.session.execute(db.text(m))
            db.session.commit()
        except:
            pass


# ----------------------------
# ANCHOR HELPERS
# ----------------------------

def allowed_file(filename):

    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS


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
    # Récupérer TOUS les joueurs actifs (sans filtres supplémentaires)
    interclub_actifs = Player.query.filter_by(actif=True).all()

    # ================= CLASSEMENTS =================
    # DUEL : membre_club=true ET atelier_duel=true
    joueurs_duel = [j for j in interclub_actifs if j.membre_club and j.atelier_duel]
    classement_duel = sorted(joueurs_duel, key=lambda j: j.duel, reverse=True)
    
    # GOAL : membre_club=true ET atelier_goal=true
    joueurs_goal = [j for j in interclub_actifs if j.membre_club and j.atelier_goal]
    classement_goal = sorted(joueurs_goal, key=lambda j: j.goal, reverse=True)

    # ================= CLASSEMENT TOTAL (DUEL + GOAL) - MEMBRE CLUB UNIQUEMENT =================
    joueurs_membre_club = [j for j in interclub_actifs if j.membre_club]
    classement_total = sorted(
        joueurs_membre_club,
        key=lambda j: (j.duel + j.goal),
        reverse=True
    )
    legend = classement_total[0] if classement_total else None

    # ================= MEILLEUR BUTEUR =================
    meilleur_buteur = None
    rang_buteur = None

    for i, j in enumerate(classement_duel):
        if legend and j.id != legend.id:
            meilleur_buteur = j
            rang_buteur = i + 1
            break

    # ================= MEILLEUR GOAL =================
    meilleur_goal = None
    rang_goal = None

    ids_exclus = set()
    if legend:
        ids_exclus.add(legend.id)
    if meilleur_buteur:
        ids_exclus.add(meilleur_buteur.id)

    for i, j in enumerate(classement_goal):
        if j.id not in ids_exclus:
            meilleur_goal = j
            rang_goal = i + 1
            break

    # ================= MATCHS (IMPORTANT 🔥) =================
    # ⚠️ adapte les champs selon ton modèle Match
    matchs_duel = Match.query.filter_by(type="DUEL").order_by(Match.date.desc()).limit(10).all()
    matchs_goal = Match.query.filter_by(type="GOAL").order_by(Match.date.desc()).limit(10).all()

    def format_matches(matchs):
        matches_data = []
        for m in matchs:
            if isinstance(m.date, str):
                date_str = m.date
            else:
                date_str = m.date.strftime("%d/%m/%Y") if m.date else ""

            matches_data.append({
                "date": date_str,
                "playerA_name": m.playerA.name if m.playerA else "J1",
                "playerA_photo": m.playerA.photo if m.playerA else "/static/img/default.png",
                "playerB_name": m.playerB.name if m.playerB else "J2", 
                "playerB_photo": m.playerB.photo if m.playerB else "/static/img/default.png",
                "scoreA": m.scoreA,
                "scoreB": m.scoreB
            })
        return matches_data

    matches_duel_data = format_matches(matchs_duel)
    matches_goal_data = format_matches(matchs_goal)
    # ================= GRAPH ELO GLOBAL =================

    # Sépare les joueurs selon leur atelier
    joueurs_goal_ids  = {j.id for j in interclub_actifs if j.atelier_goal}
    joueurs_duel_ids  = {j.id for j in interclub_actifs if j.atelier_duel}
    # Matchs GOAL : les deux joueurs doivent être inscrits à l'atelier goal
    matchs_goal = (
        Match.query
        .filter(
            Match.type == "GOAL",
            Match.playerA_id.in_(joueurs_goal_ids),
            Match.playerB_id.in_(joueurs_goal_ids)
        )
        .order_by(Match.date.asc())
        .all()
    )

    # Matchs DUEL : les deux joueurs doivent être inscrits à l'atelier duel
    matchs_duel = (
        Match.query
        .filter(
            Match.type == "DUEL",
            Match.playerA_id.in_(joueurs_duel_ids),
            Match.playerB_id.in_(joueurs_duel_ids)
        )
        .order_by(Match.date.asc())
        .all()
    )

    # Fusionne et retrie par date
    from itertools import chain
    matchs_all = sorted(chain(matchs_goal, matchs_duel), key=lambda m: m.date)

    print("MATCHS GOAL filtrés :", len(matchs_goal))
    print("MATCHS DUEL filtrés :", len(matchs_duel))
    print("TOTAL :", len(matchs_all))

    elo_history = {}
    labels = []

    for j in interclub_actifs:
        elo_history[j.id] = [j.elo]

    for i, m in enumerate(matchs_all):
        if not m.playerA or not m.playerB:
            continue

        class Temp:
            def __init__(self, elo):
                self.elo = elo

        p1_temp = Temp(elo_history[m.playerA.id][-1])
        p2_temp = Temp(elo_history[m.playerB.id][-1])

        update_elo(p1_temp, p2_temp, m.scoreA, m.scoreB)

        elo_history[m.playerA.id].append(p1_temp.elo)
        elo_history[m.playerB.id].append(p2_temp.elo)

        labels.append(i + 1)

    # ✅ ICI, en dehors de la boucle
    top_players = [j for j in classement_total if len(elo_history.get(j.id, [])) > 1]

    graph_data = []
    for j in top_players:
        graph_data.append({
            "name": j.name,
            "data": elo_history.get(j.id, []),
            "photo": j.photo
        })
        print("MATCHS FILTRÉS :", len(matchs_all))

    # ================= RENDER =================
    return render_template(
        "index.html",
        duel=classement_duel,
        goal=classement_goal,
        classement_club=classement_total,
        legend=legend,
        meilleur_buteur=meilleur_buteur,
        meilleur_goal=meilleur_goal,
        rang_buteur=rang_buteur,
        rang_goal=rang_goal,
        matches_duel=matches_duel_data,
        matches_goal=matches_goal_data,
        labels=labels,
        graph_data=graph_data,
    )



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
# ANCHOR players
@app.route("/players")
def players():

    joueurs = Player.query.order_by(Player.name).all()

    club_javene = []
    clubs_ext = defaultdict(list)

    for j in joueurs:

        if j.membre_club:
            club_javene.append(j)

        else:
            club = j.external_club or "Autre"
            clubs_ext[club].append(j)

    # tri JAVENÉ
    club_javene.sort(
        key=lambda x: (
            not x.interclub,
            -(x.elo or 0),
            x.name
        )
    )

    # tri clubs ext
    for club in clubs_ext:
        clubs_ext[club].sort(key=lambda x: x.name)

    return render_template(
        "players.html",
        club_javene=club_javene,
        clubs_ext=clubs_ext
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

    # DUEL : interclub uniquement
    duel_players = Player.query.filter(
        Player.id != id,
        Player.actif == True,
        Player.membre_club == True,
        Player.interclub == True
    ).all()

    # GOAL : tous les membres actifs du club
    goal_players = Player.query.filter(
        Player.id != id,
        Player.actif == True,
        Player.membre_club == True
    ).all()

    matches = Match.query.filter(
        (Match.playerA_id == id) | (Match.playerB_id == id)
    ).all()

    duel_history = [m for m in matches if m.type == "DUEL"]
    goal_history  = [m for m in matches if m.type == "GOAL"]

    played_pairs = {
        (min(m.playerA_id, m.playerB_id), max(m.playerA_id, m.playerB_id), m.type)
        for m in matches
    }

    duel_remaining = []
    goal_remaining = []

    for pl in duel_players:
        pair = (min(p.id, pl.id), max(p.id, pl.id))
        if (pair[0], pair[1], "DUEL") not in played_pairs:
            duel_remaining.append(pl)

    for pl in goal_players:
        pair = (min(p.id, pl.id), max(p.id, pl.id))
        if (pair[0], pair[1], "GOAL") not in played_pairs:
            goal_remaining.append(pl)

    # tri style FIFA
    duel_remaining = sorted(duel_remaining, key=lambda x: abs(x.elo - p.elo))
    goal_remaining = sorted(goal_remaining, key=lambda x: abs(x.elo - p.elo))


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
        chbb = "chbb" in request.form

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
        card_background = "/static/img/cards/bronze.png"

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
            card_background=card_background,
            chbb=chbb
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
        atelier_goal=True,
        chbb=False
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
        player.chbb = "chbb" in request.form
        

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

                player.card_background = "/static/img/cards/bronze.png"

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


#ANCHOR - dettes admin
@app.route("/admin/dettes")
@app.route("/admin/dettes")
def admin_dettes():
    # Vérifie si connecté
    if not session.get("dettes_auth"):
        return redirect("/admin/dettes/login")
    
    joueurs = Player.query.filter_by(
        membre_club=True,
        actif=True
    ).order_by(Player.dette.desc()).all()

    top_dettes = Player.query.filter(
        Player.membre_club == True,
        Player.actif == True,
        Player.dette > 0
    ).order_by(Player.dette.desc()).limit(5).all()

    top_credits = Player.query.filter(
        Player.membre_club == True,
        Player.actif == True,
        Player.dette < 0
    ).order_by(Player.dette.asc()).limit(5).all()

    total_dettes = sum((j.dette or 0) for j in joueurs if (j.dette or 0) > 0)

    return render_template(
        "admin_dettes.html",
        joueurs=joueurs,
        top_dettes=top_dettes,
        top_credits=top_credits,
        total_dettes=total_dettes
    )

#ANCHOR - dette password
ADMIN_PASSWORD = "bonziniitsf"  # à changer

#ANCHOR - dettes login
@app.route("/admin/dettes/login", methods=["GET","POST"])
def dettes_login():
    # Si déjà connecté → redirige vers la page dettes
    if session.get("dettes_auth"):
        return redirect("/admin/dettes")

    error = None

    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["dettes_auth"] = True
            return redirect("/admin/dettes")
        else:
            error = "Mot de passe incorrect"

    return render_template("dettes_login.html", error=error)

#ANCHOR - dettes logout
@app.route("/admin/dettes/logout")
def dettes_logout():
    session.pop("dettes_auth", None)
    return redirect("/admin/dettes/login")

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
@app.route("/admin/dettes/add_one/<int:player_id>", methods=["POST"])
def add_one_dette(player_id):
    try:
        joueur = Player.query.get_or_404(player_id)
        joueur.dette = (joueur.dette or 0) + 1
        transaction = DetteTransaction(
            player_id=player_id,
            montant=1,
            description="+1"
        )
        db.session.add(transaction)
        db.session.commit()
    except Exception as e:
        print("Erreur add_one_dette:", e)
    return redirect("/admin/dettes")

#ANCHOR - admin dettes reset
@app.route("/admin/dettes/pay/<int:player_id>", methods=["POST"])
def pay_dette(player_id):
    joueur = Player.query.get_or_404(player_id)
    transaction = DetteTransaction(
        player_id=player_id,
        montant=-joueur.dette,  # remet la dette à 0
        description="Paiement"
    )
    joueur.dette = 0
    db.session.add(transaction)
    db.session.commit()
    return redirect("/admin/dettes")

CHBB_PASSWORD = "biere"
#ANCHOR - chbb admin
@app.route("/admin/chbb")
def admin_chbb():
    # Vérifie que l’utilisateur est connecté
    if not session.get("chbb_auth"):
        return redirect("/admin/chbb/login")

    players = Player.query.filter_by(
        membre_club=True,
        chbb=True,
        actif=True
    ).all()

    return render_template("chbb.html", players=players)

#ANCHOR - chbb login
CHBB_PASSWORD = "biere"

@app.route("/admin/chbb/login", methods=["GET","POST"])
def chbb_login():
    # Si déjà connecté → va au tableau
    if session.get("chbb_auth"):
        return redirect("/admin/chbb")

    error = None

    if request.method == "POST":
        password = request.form.get("password")
        if password == CHBB_PASSWORD:
            session["chbb_auth"] = True
            return redirect("/admin/chbb")
        else:
            error = "Mot de passe incorrect"

    return render_template("chbb_login.html", error=error)

#ANCHOR - chbb logout
@app.route("/admin/chbb/logout")
def chbb_logout():
    session.pop("chbb_auth", None)
    return redirect("/admin/chbb/login")

#ANCHOR - chbb update
@app.route("/admin/chbb/update", methods=["POST"])
def chbb_update():

    player_id = request.form["player_id"]

    value = int(request.form["value"])

    player = Player.query.get(player_id)

    from datetime import datetime

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    if value == 2 and player.chbb_date1 is None:
        player.chbb_date1 = now

    if value == 1 and player.chbb_date2 is None:
        player.chbb_date2 = now

    if value == 0 and player.chbb_date3 is None:
        player.chbb_date3 = now

    player.chbb_count = value

    db.session.commit()

    return "ok"

#ANCHOR - chbb reset
@app.route("/admin/chbb/reset")
def chbb_reset():
    players = Player.query.filter_by(
        membre_club=True,
        chbb=True,
        actif=True
    ).all()

    for p in players:
        p.chbb_count = 3
        p.chbb_date1 = None
        p.chbb_date2 = None
        p.chbb_date3 = None

    db.session.commit()

    # Retour vers la page CHBB
    return redirect(url_for('admin_chbb'))

#ANCHOR - no cache
@app.after_request
def add_header(response):

    response.headers["Cache-Control"] = "no-store"

    return response
# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":

    socketio.run(app, host="0.0.0.0", port=5070, debug=True)