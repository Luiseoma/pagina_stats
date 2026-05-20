from flask import Flask, render_template

app = Flask(__name__)

def fuerza(form):
    return sum(form) / len(form)

matches = {
    1: {
        "team1": "México",
        "team2": "Sudáfrica",
        "home_advantage": 0.15,
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

    f1 = fuerza(match["form_team1"])
    f2 = fuerza(match["form_team2"])

    # ventaja local
    f1 = f1 + match.get("home_advantage", 0)

    total = f1 + f2

    base_draw = 0.25  # 25% empate base tipo Sofascore

    prob_draw = round(base_draw * 100, 1)

    remaining = 100 - prob_draw

    prob_team1 = round((f1 / total) * remaining, 1)
    prob_team2 = round((f2 / total) * remaining, 1)

    return render_template(
        "match.html",
        match=match,
        prob_team1=prob_team1,
        prob_team2=prob_team2,
        prob_draw=prob_draw
    )

if __name__ == "__main__":
    app.run(debug=True)