from flask import Flask, render_template

app = Flask(__name__)

matches = {
    1: {
        'team1': 'México',
        'team2': 'Sudáfrica',
        'probabilities': {
            'team1': 55,
            'draw': 25,
            'team2': 20,
        },
        'link': 'https://example.com/bet'

    }
}

@app.route("/")
def home ():
    return render_template('home.html',matches=matches)

@app.route('/match/<int:id>)')
def match (id):
    match = matches.get (id)
    return render_template('match.html',match=match)

if __name__ == "__main__":
    app.run(debug=True)

    