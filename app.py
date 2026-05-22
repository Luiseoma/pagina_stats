from flask import Flask, render_template
from collections import defaultdict
import json

app = Flask(__name__)

# =========================
# FUNCIONES
# =========================

def fuerza(form):
    return sum(form) / len(form)


# =========================
# LEER JSONS
# =========================

with open("data/matches.json", "r", encoding="utf-8") as file:
    matches_list = json.load(file)

with open("data/teams.json", "r", encoding="utf-8") as file:
    teams = json.load(file)

# Convertir matches en diccionario para búsquedas rápidas
matches = {str(match["id"]): match for match in matches_list}


# =========================
# HOME
# =========================

@app.route("/")
def home():

    matches_by_date = defaultdict(list)

    for match in matches_list:
        matches_by_date[match["date"]].append(match)

    return render_template(
        "home.html",
        matches_by_date=matches_by_date,
        teams=teams
    )


# =========================
# MATCH PAGE
# =========================

@app.route("/match/<id>")
def match(id):

    match = matches[id]

    # Revisar si existen team1 y team2
    if "team1" not in match or "team2" not in match:

        return render_template(
            "match.html",
            match=match,
            no_teams=True
        )

    # Buscar datos de equipos
    team1_data = teams.get(match["team1"])
    team2_data = teams.get(match["team2"])

    # Calcular fuerza
    f1 = fuerza(team1_data["form"])
    f2 = fuerza(team2_data["form"])

    # Probabilidad empate base
    base_draw = 0.25

    prob_draw = round(base_draw * 100, 1)

    remaining = 100 - prob_draw

    prob_team1 = round((f1 / (f1 + f2)) * remaining, 1)
    prob_team2 = round((f2 / (f1 + f2)) * remaining, 1)

    return render_template(
        "match.html",
        match=match,
        team1_data=team1_data,
        team2_data=team2_data,
        prob_team1=prob_team1,
        prob_team2=prob_team2,
        prob_draw=prob_draw,
        no_teams=False
    )



# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)