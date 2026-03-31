
from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import math

app = Flask(__name__)
app.secret_key = "secret"
DB_NAME = "db.db"

def db():
    return sqlite3.connect(DB_NAME)

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["u"]
        p=request.form["p"]
        con=db()
        cur=con.cursor()
        cur.execute("SELECT * FROM users WHERE u=? AND p=?", (u,p))
        if cur.fetchone():
            session["user"]=u
            return redirect(url_for("menu"))
    return render_template("login.html")

# ================= REGISTER =================
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        u=request.form["u"]
        p=request.form["p"]
        con=db()
        cur=con.cursor()
        try:
            cur.execute("INSERT INTO users (u,p,c,r,p2,m,t,l,sus) VALUES (?,?,?,?,?,?,?,?,?)",
                        (u,p,0,0,0,0,0,0,0))
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return "El usuario ya existe"
        return redirect(url_for("login"))
    return render_template("register.html")

# ================= MENU =================
@app.route("/menu")
def menu():
    return render_template("menu.html")

# ================= RANKING =================
@app.route("/ranking")
def ranking():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    all_users = cur.fetchall()
    ranking = []
    for u in all_users:
        avg = round(sum(u[2:8])/6,2)
        ranking.append({"username": u[0], "average": avg})
    ranking.sort(key=lambda x: x["average"], reverse=True)
    return render_template("ranking.html", ranking=ranking)

# ================= PROFILE =================
@app.route("/profile")
def profile():
    u = session.get("user")
    if not u:
        return redirect(url_for("login"))
    
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE u=?", (u,))
    data = cur.fetchone()
    con.close()

    if data:
        clicks = data[2]
        reaction = data[3]
        precision_score = data[4]
        memory = data[5]
        text = data[6]
        letter = data[7]

        avg = round(sum([clicks, reaction, precision_score, memory, text, letter]) / 6, 2)

        scores = {
            "clicks": clicks,
            "reaction": reaction,
            "precision": precision_score,
            "memoria": memory,
            "text": text,
            "letter": letter,
            "average": avg
        }
    else:
        scores = {
            "clicks": 0,
            "reaction": 0,
            "precision": 0,
            "memoria": 0,
            "text": 0,
            "letter": 0,
            "average": 0
        }

    return render_template("profile.html", username=u, scores=scores)

# ================= SAVE NORMAL =================
@app.route("/save/<test>/<int:score>")
def save(test, score):
    u = session.get("user")
    if not u:
        return "no user"
    con = db()
    cur = con.cursor()
    col_map = {
        "clicks": "c",
        "reaction": "r",
        "precision": "p2",
        "memory": "m",
        "text": "t",
        "letter": "l"
    }
    col = col_map.get(test)
    if col:
        cur.execute(f"UPDATE users SET {col}=MAX({col},?) WHERE u=?", (score,u))
        con.commit()
    con.close()
    return "ok"

# ================= ANTI-CHEAT CLICKS =================
@app.route('/save/clicks', methods=['POST'])
def save_clicks():
    data = request.get_json()

    username = session.get("user")
    score = data["score"]
    clicks = data["clicks"]
    intervals = data["intervals"]

    suspicious_score = 0

    if not intervals or len(intervals) < 5:
        return "ok"

    avg = sum(intervals)/len(intervals)

    # 1 velocidad extrema
    if clicks / 10 > 18:
        suspicious_score += 2

    # 2 varianza baja
    variance = sum((x - avg)**2 for x in intervals) / len(intervals)
    if variance < 120:
        suspicious_score += 2

    # 3 picos imposibles
    fast_clicks = sum(1 for i in intervals if i < 35)
    if fast_clicks > len(intervals) * 0.25:
        suspicious_score += 2

    # 4 irregularidad baja
    diffs = [abs(intervals[i] - intervals[i-1]) for i in range(1, len(intervals))]
    irregularity = sum(diffs) / len(diffs)
    if irregularity < 25:
        suspicious_score += 2

    # 5 rachas rápidas
    streak = 0
    for i in intervals:
        if i < 60:
            streak += 1
            if streak > 10:
                suspicious_score += 2
                break
        else:
            streak = 0

    # 6 desviación estándar ultra baja
    std = math.sqrt(variance)
    if std < 10:
        suspicious_score += 2

    # 7 ratio rápido total
    if fast_clicks > len(intervals) * 0.4:
        suspicious_score += 2

    # 8 clicks demasiado constantes (check repetición)
    repeats = sum(1 for i in range(1,len(intervals)) if abs(intervals[i]-intervals[i-1])<5)
    if repeats > len(intervals)*0.4:
        suspicious_score += 2

    # 9 bloques de ritmo constante
    block = 0
    for i in intervals:
        if abs(i - avg) < 10:
            block += 1
            if block > 12:
                suspicious_score += 2
                break
        else:
            block = 0

    # 10 detección de ritmo artificial
    pattern_hits = 0
    for i in range(2,len(intervals)):
        if abs(intervals[i] - intervals[i-2]) < 8:
            pattern_hits += 1
    if pattern_hits > len(intervals)*0.3:
        suspicious_score += 2

    # SISTEMA ACUMULATIVO
    con = db()
    cur = con.cursor()
    cur.execute("SELECT sus FROM users WHERE u=?", (username,))
    current_sus = cur.fetchone()[0]

    current_sus += suspicious_score

    if suspicious_score == 0 and current_sus > 0:
        current_sus -= 1

    cur.execute("UPDATE users SET sus=? WHERE u=?", (current_sus, username))
    con.commit()

    if current_sus >= 8:
        con.close()
        return "ok"

    # guardar score
    cur.execute("UPDATE users SET c = MAX(c, ?) WHERE u=?", (score, username))
    con.commit()
    con.close()

    return "ok"

# ================= GAMES =================
@app.route("/clicks")
def clicks():
    return render_template("clicks.html")

@app.route("/precision")
def precision():
    return render_template("precision.html")

@app.route("/memoria")
def memoria():
    return render_template("memoria.html")

@app.route("/reaction")
def reaction():
    return render_template("reaction.html")

@app.route("/letter")
def letter():
    return render_template("letter.html")

@app.route("/choose-music")
def choose_music():
    return render_template("choose-music.html")

# ================= CREATE TABLE =================
if __name__=="__main__":
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        u TEXT PRIMARY KEY,
        p TEXT,
        c INT,
        r INT,
        p2 INT,
        m INT,
        t INT,
        l INT,
        sus INT DEFAULT 0
    )
    """)

    con.commit()
    con.close()

    app.run(host="0.0.0.0", port=10000)

