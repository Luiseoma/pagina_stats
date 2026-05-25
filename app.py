from flask import Flask, render_template, request, redirect
from collections import defaultdict
import json
import os

app = Flask(__name__)

admin_key = os.getenv("admin_key","statsprogram")

# =========================
# FUNCIONES
# =========================

def fuerza(form):
    return sum(form) / len(form) *10

# =========================
# TABLAS
# =========================

def generar_tablas(matches_list):
    tablas = {}

    for match in matches_list:

        group = match.get("group")
        if not group:
            continue

        group = group.strip().upper()

        if group not in tablas:
            tablas[group] = {}

        team1 = match["team1"]
        team2 = match["team2"]

        for team in [team1, team2]:
            if team not in tablas[group]:
                tablas[group][team] = {
                    "pts": 0,
                    "pj": 0,
                    "g": 0,
                    "e": 0,
                    "p": 0,
                    "gf": 0,
                    "gc": 0,
                    "dg": 0,
                }

        if match["score1"] is None or match["score2"] is None:
            continue

        score1 = match["score1"]
        score2 = match["score2"]

        tablas[group][team1]["pj"] += 1
        tablas[group][team2]["pj"] += 1

        tablas[group][team1]["gf"] += score1
        tablas[group][team1]["gc"] += score2

        tablas[group][team2]["gf"] += score2
        tablas[group][team2]["gc"] += score1

        if score1 > score2:
            tablas[group][team1]["pts"] += 3
            tablas[group][team1]["g"] += 1
            tablas[group][team2]["p"] += 1

        elif score2 > score1:
            tablas[group][team2]["pts"] += 3
            tablas[group][team2]["g"] += 1
            tablas[group][team1]["p"] += 1

        else:
            tablas[group][team1]["pts"] += 1
            tablas[group][team2]["pts"] += 1
            tablas[group][team1]["e"] += 1
            tablas[group][team2]["e"] += 1

    # diferencia de goles
    for group in tablas:
        for team in tablas[group]:
            tablas[group][team]["dg"] = (
                tablas[group][team]["gf"] - tablas[group][team]["gc"]
            )

    # ordenar grupos
    for group in tablas:
        tablas[group] = dict(
            sorted(
                tablas[group].items(),
                key=lambda item: (
                    item[1]["pts"],
                    item[1]["dg"],
                    item[1]["gf"],
                ),
                reverse=True
            )
        )

    CLASIFICAN_DIRECTO = 2
    MEJORES_TERCEROS = 8

    terceros = []

    for group in tablas:
        equipos = list(tablas[group].items())

        for i, (team, stats) in enumerate(equipos):
            if i == 2:
                terceros.append((team, stats))

    terceros_ordenados = sorted(
        terceros,
        key=lambda x: (
            x[1]["pts"],
            x[1]["dg"],
            x[1]["gf"]
        ),
        reverse=True
    )

    mejores_terceros = terceros_ordenados[:MEJORES_TERCEROS]
    mejores_terceros_nombres = [t[0] for t in mejores_terceros]

    clasificados = []

    for group in tablas:
        equipos = list(tablas[group].items())

        for i, (team, stats) in enumerate(equipos):

            if i < CLASIFICAN_DIRECTO:
                stats["status"] = "clasificado"
                clasificados.append(team)

            elif i == CLASIFICAN_DIRECTO:
                if team in mejores_terceros_nombres:
                    stats["status"] = "tercero"
                    clasificados.append(team)
                else:
                    stats["status"] = "eliminado"
            else:
                stats["status"] = "eliminado"

    return tablas, clasificados

# =========================
# DEFINIR RONDA 32
# =========================
def resolver_equipos_r32(matches_list, tablas):
    posiciones = {}

    for group, teams in tablas.items():

        equipos = list(teams.keys())

        if len(equipos) >= 1:
            posiciones[f"{group}1"] = equipos[0]

        if len(equipos) >= 2:
            posiciones[f"{group}2"] = equipos[1]

        if len(equipos) >= 3:
            posiciones[f"{group}3"] = equipos[2]

    # reemplazar placeholders
    for match in matches_list:

        if match.get("stage") != "Round of 32":
            continue

        # TEAM1
        team1 = match.get("team1")

        if team1 in posiciones:
            match["team1"] = posiciones[team1]

        # TEAM2
        team2 = match.get("team2")

        if team2 in posiciones:
            match["team2"] = posiciones[team2]

        # TEAM2 OPTIONS
        if "team2_options" in match:

            opciones_reales = []

            for option in match["team2_options"]:

                if option in posiciones:
                    opciones_reales.append(posiciones[option])

            if opciones_reales:
                match["team2"] = opciones_reales[0]

    return matches_list


# =========================
# RONDA 32
# =========================

def asignar_ronda_32(matches_list, clasificados):

    r32_matches = [
        m for m in matches_list
        if m.get("stage", "").startswith("R32")
    ]

    index = 0

    for match in r32_matches:

        # =========================
        # CASO 1: ya tiene equipos fijos
        # =========================
        if match.get("team1") and match.get("team2"):
            continue

        # =========================
        # CASO 2: team2 viene como opciones
        # =========================
        if match.get("team1") and match.get("team2_options"):

            if index + 1 >= len(clasificados):
                break

            match["team2"] = clasificados[index]
            index += 1
            continue

        # =========================
        # CASO 3: vacío total
        # =========================
        if not match.get("team1") and not match.get("team2"):

            if index + 1 >= len(clasificados):
                break

            match["team1"] = clasificados[index]
            match["team2"] = clasificados[index + 1]
            index += 2

    return matches_list

# =========================
# OCTAVOS DE FINAL
# =========================

def obtener_ganador(match):

    if match["score1"] is None or match["score2"] is None:
        return None

    if match["score1"] > match["score2"]:
        return match["team1"]

    elif match["score2"] > match["score1"]:
        return match["team2"]

    return None

def obtener_perdedor(match):

    if match["score1"] is None or match["score2"] is None:
        return None

    if match["score1"] > match["score2"]:
        return match["team2"]

    elif match["score2"] > match["score1"]:
        return match["team1"]

    return None

def generar_r16(matches_list):

    # buscar partidos R32
    r32 = {
        match["id"]: match
        for match in matches_list
        if str(match["id"]).startswith("R32")
    }

    # mapa de cruces
    cruces = {
        "R16A": ("R32A", "R32D"),
        "R16B": ("R32C", "R32F"),
        "R16C": ("R32B", "R32E"),
        "R16D": ("R32G", "R32H"),
        "R16E": ("R32L", "R32K"),
        "R16F": ("R32I", "R32J"),
        "R16G": ("R32O", "R32N"),
        "R16H": ("R32M", "R32P"),
    }

    for match in matches_list:

        if match["id"] not in cruces:
            continue

        r32_1, r32_2 = cruces[match["id"]]

        ganador1 = obtener_ganador(r32[r32_1])
        ganador2 = obtener_ganador(r32[r32_2])

        match["team1"] = ganador1
        match["team2"] = ganador2

    return matches_list

# =========================
# CUARTOS DE FINAL
# =========================

def generar_cuartos(matches_list):

    r16 = {
        match["id"]: match
        for match in matches_list
        if str(match["id"]).startswith("R16")
    }

    cruces = {
        "QR1": ("R16A", "R16B"),
        "QR2": ("R16E", "R16F"),
        "QR3": ("R16C", "R16D"),
        "QR4": ("R16G", "R16H"),
    }

    for match in matches_list:

        if match["id"] not in cruces:
            continue

        r16_1, r16_2 = cruces[match["id"]]

        ganador1 = obtener_ganador(r16[r16_1])
        ganador2 = obtener_ganador(r16[r16_2])

        match["team1"] = ganador1
        match["team2"] = ganador2

    return matches_list

# =========================
# SEMIFINALES
# =========================

def generar_semis(matches_list):

    cuartos = {
        match["id"]: match
        for match in matches_list
        if str(match["id"]).startswith("QR")
    }

    cruces = {
        "SF1": ("QR1", "QR2"),
        "SF2": ("QR3", "QR4"),
    }

    for match in matches_list:

        if match["id"] not in cruces:
            continue

        qr1, qr2 = cruces[match["id"]]

        ganador1 = obtener_ganador(cuartos[qr1])
        ganador2 = obtener_ganador(cuartos[qr2])

        match["team1"] = ganador1
        match["team2"] = ganador2

    return matches_list

# =========================
# FINAL
# =========================

def generar_final(matches_list):

    semis = {
        match["id"]: match
        for match in matches_list
        if str(match["id"]).startswith("SF")
    }

    for match in matches_list:

        # FINAL
        if match["id"] == "FINAL":

            ganador1 = obtener_ganador(semis["SF1"])
            ganador2 = obtener_ganador(semis["SF2"])

            match["team1"] = ganador1
            match["team2"] = ganador2

        # TERCER PUESTO
        elif match["id"] == "THIRD":

            perdedor1 = obtener_perdedor(semis["SF1"])
            perdedor2 = obtener_perdedor(semis["SF2"])

            match["team1"] = perdedor1
            match["team2"] = perdedor2

    return matches_list

# =========================
# LEER JSONS
# =========================

with open("data/teams.json", "r", encoding="utf-8") as file:
    teams = json.load(file)


# =========================
# HOME
# =========================

@app.route("/")
def home():

    with open("data/matches.json", "r", encoding="utf-8") as file:
        matches_list = json.load(file)

    tablas, clasificados = generar_tablas(matches_list)

    updated_matches = resolver_equipos_r32(matches_list, tablas)

    updated_matches = generar_r16(updated_matches)

    updated_matches = generar_cuartos(updated_matches)

    updated_matches = generar_semis(updated_matches)

    updated_matches = generar_final(updated_matches)

    global matches
    matches = {
        str(match["id"]): match
        for match in updated_matches
    }

    matches_by_date = defaultdict(list)

    for match in updated_matches:
        matches_by_date[match["date"]].append(match)

    return render_template(
        "home.html",
        matches_by_date=matches_by_date,
        teams=teams
    )
#==========================
#TABLES PAGE
#==========================

@app.route("/tables")
def tables ():

    with open("data/matches.json", "r", encoding="utf-8") as file:
        matches_list = json.load(file)

    #Calcular grupos
    tablas,clasificados = generar_tablas(matches_list)

    #actualizar ronde de 32
    updated_matches = asignar_ronda_32(matches_list, clasificados)

    return render_template(
        "tables.html",
        tablas=tablas,
        matches=updated_matches,
        teams=teams
    )

# =========================
# MATCH PAGE
# =========================

@app.route("/match/<id>")
def match(id):

    with open("data/matches.json", "r", encoding="utf-8") as file:
        matches_list = json.load(file)

    matches = {
        str(match["id"]): match
        for match in matches_list
    }

    match = matches[id]

    # Revisar si existen team1 y team2
    if (
        "team1" not in match
        or "team2" not in match
        or match["team1"] is None
        or match["team2"] is None
    ):

        return render_template(
            "match.html",
            match=match,
            no_teams=True
        )

    # Buscar datos de equipos
    team1_data = teams.get(match["team1"])
    team2_data = teams.get(match["team2"])

    #Por si falta data
    if not team1_data or not team2_data:
        return "Error: equipo no encontrado"

    # Calcular fuerza

    import math

    # =========================
    # RATING BASE (FIFA manual)
    # =========================
    r1 = team1_data["rating"]
    r2 = team2_data["rating"]

    # =========================
    # FORMA (AJUSTE PEQUEÑO)
    # =========================
    form1 = sum(team1_data["form"]) / len(team1_data["form"])
    form2 = sum(team2_data["form"]) / len(team2_data["form"])

    form_bonus1 = (form1 - 0.5) * 100
    form_bonus2 = (form2 - 0.5) * 100

    # rating final
    f1 = r1 + form_bonus1
    f2 = r2 + form_bonus2

    # =========================
    # ELO PROBABILITY
    # =========================
    prob_team1 = 1 / (1 + 10 ** ((f2 - f1) / 400))
    prob_team2 = 1 - prob_team1

    # =========================
    # EMPATE (dinámico realista)
    # =========================
    diff = abs(f1 - f2)

    prob_draw = max(0.10, 0.28 - diff * 0.0002)

    # =========================
    # NORMALIZAR A 100%
    # =========================
    total = prob_team1 + prob_team2 + prob_draw

    prob_team1 = round(prob_team1 / total * 100, 1)
    prob_team2 = round(prob_team2 / total * 100, 1)
    prob_draw = round(prob_draw / total * 100, 1)

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

#==========================
#ADMIN PAGE
#==========================

@app.route("/admin")
def admin():

    key = request.args.get("key") or request.form.get("key")

    if key != admin_key:
        return "NO AUTORIZADO", 403

    with open("data/matches.json", "r", encoding="utf-8") as f:
        matches = json.load(f)

    return render_template(
        "admin.html",
        matches=matches,
        key=key
)

@app.route("/update_match/<int:match_id>", methods=["POST"])
def update_match(match_id):

    key = request.args.get("key")

    if key != admin_key:
        return "NO AUTORIZADO", 403


    with open("data/matches.json", "r", encoding="utf-8") as f:
        matches = json.load(f)

    for match in matches:

        if match["id"] == match_id:

            score1 = request.form["score1"]
            score2 = request.form["score2"]

            match["score1"] = int(score1) if score1 != "" else None
            match["score2"] = int(score2) if score2 != "" else None

    with open("data/matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=4, ensure_ascii=False)

    return redirect(f"/admin?key={key}")

# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)