from flask import Flask, render_template

app = Flask(__name__)

def calcular_fuerza(form):
    return sum(form) / len(form)

matches = {
    1: {
        "team1": "México",
        "team2": "Sudáfrica",
        "form_team1": [1, 0, 1, 1, 1],
        "form_team2": [0, 1, 0, 0, 1]
    }
}

@app.route("/")
def home ():
    return render_template('home.html',matches=matches)

@app.route("/match/<int:id>")
def match(id):
    match = matches[id]

    f1 = calcular_fuerza(match["form_team1"])
    f2 = calcular_fuerza(match["form_team2"])

    total = f1 + f2

    prob_team1 = round((f1 / total) * 100, 1)
    prob_team2 = round((f2 / total) * 100, 1)
    prob_draw = round(100 - (prob_team1 + prob_team2), 1)

    return render_template(
        "match.html",
        match=match,
        prob_team1=prob_team1,
        prob_team2=prob_team2,
        prob_draw=prob_draw
    )
    