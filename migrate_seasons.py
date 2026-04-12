from app import app, db, Player, Match
from datetime import datetime

# =========================
# MODELES A AJOUTER SI PAS ENCORE FAIT
# =========================

class Season(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    date_start = db.Column(db.DateTime)
    date_end = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=False)


class PlayerSeasonStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer)
    season_id = db.Column(db.Integer)

    duel = db.Column(db.Integer, default=0)
    goal = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    matches = db.Column(db.Integer, default=0)
    elo = db.Column(db.Integer, default=1000)


# =========================
# SCRIPT
# =========================

def migrate():
    with app.app_context():

        print("🚀 MIGRATION SAISONS")

        # sécurité anti double run
        if Season.query.count() > 0:
            print("❌ Migration déjà effectuée")
            return

        # =========================
        # 1. CREATION SAISONS AUTO
        # =========================

        matches = Match.query.all()
        years = set()

        for m in matches:
            if m.date:
                years.add(m.date[:4])

        seasons = {}

        for y in sorted(years):
            season = Season(
                name=f"Saison {y}",
                date_start=datetime(int(y), 1, 1),
                date_end=datetime(int(y), 12, 31),
                active=False
            )
            db.session.add(season)
            db.session.flush()  # pour récupérer ID
            seasons[y] = season

        db.session.commit()

        print(f"✅ {len(seasons)} saisons créées")

        # =========================
        # 2. ASSIGNATION MATCHS
        # =========================

        for m in matches:
            if m.date:
                year = m.date[:4]
                if year in seasons:
                    m.season_id = seasons[year].id

        db.session.commit()
        print("✅ Matchs assignés")

        # =========================
        # 3. CALCUL STATS PAR SAISON
        # =========================

        players = Player.query.all()

        for season_key, season in seasons.items():

            print(f"📊 Calcul stats {season.name}")

            # reset temporaire
            stats = {p.id: {
                "duel": 0,
                "goal": 0,
                "wins": 0,
                "losses": 0,
                "matches": 0,
                "elo": 1000
            } for p in players}

            season_matches = Match.query.filter_by(season_id=season.id).order_by(Match.date.asc()).all()

            for m in season_matches:

                p1 = m.playerA_id
                p2 = m.playerB_id

                if not p1 or not p2:
                    continue

                stats[p1]["matches"] += 1
                stats[p2]["matches"] += 1

                if m.type == "DUEL":
                    stats[p1]["duel"] += m.scoreA
                    stats[p2]["duel"] += m.scoreB
                else:
                    stats[p1]["goal"] += m.scoreA
                    stats[p2]["goal"] += m.scoreB

                if m.scoreA > m.scoreB:
                    stats[p1]["wins"] += 1
                    stats[p2]["losses"] += 1
                else:
                    stats[p2]["wins"] += 1
                    stats[p1]["losses"] += 1

                # ELO simple
                K = 32
                e1 = 1 / (1 + 10 ** ((stats[p2]["elo"] - stats[p1]["elo"]) / 400))
                e2 = 1 / (1 + 10 ** ((stats[p1]["elo"] - stats[p2]["elo"]) / 400))

                r1 = 1 if m.scoreA > m.scoreB else 0
                r2 = 1 if m.scoreB > m.scoreA else 0

                stats[p1]["elo"] += int(K * (r1 - e1))
                stats[p2]["elo"] += int(K * (r2 - e2))

            # sauvegarde DB
            for pid, s in stats.items():
                db.session.add(PlayerSeasonStats(
                    player_id=pid,
                    season_id=season.id,
                    duel=s["duel"],
                    goal=s["goal"],
                    wins=s["wins"],
                    losses=s["losses"],
                    matches=s["matches"],
                    elo=s["elo"]
                ))

            db.session.commit()

        print("🎉 MIGRATION TERMINÉE")


if __name__ == "__main__":
    CONFIRM = True  # ⚠️ passe à True pour lancer

    if CONFIRM:
        migrate()
    else:
        print("⚠️ CONFIRM = False")