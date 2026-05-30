"""
NepalTrail Backend — Flask + SQLite
Endpoints:
  POST /api/auth/register
  POST /api/auth/login
  GET  /api/user/<id>
  PUT  /api/user/<id>/credits

  GET  /api/routes
  GET  /api/accommodations
  GET  /api/guides
  GET  /api/transport

  GET  /api/bookings?user_id=
  POST /api/bookings

  GET  /api/feedbacks
  POST /api/feedbacks

  GET  /api/checkins?user_id=
  POST /api/checkins

  POST /api/sos
  GET  /api/sos?user_id=
"""

from flask import Flask, request, jsonify, send_from_directory
import sqlite3, hashlib, os, time, json, re

app = Flask(__name__, static_folder='public', static_url_path='')

DB_PATH = os.path.join(os.path.dirname(__file__), 'nepaltrail.db')

# ── DB helpers ─────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        email       TEXT UNIQUE NOT NULL,
        password    TEXT NOT NULL,
        avatar      TEXT,
        rank        TEXT DEFAULT 'Trail Starter',
        credits     INTEGER DEFAULT 0,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        item_name   TEXT NOT NULL,
        item_type   TEXT NOT NULL,   -- transport | accommodation | guide
        price       TEXT,
        emoji       TEXT,
        booking_ref TEXT,
        date        TEXT DEFAULT (date('now')),
        status      TEXT DEFAULT 'confirmed',
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS feedbacks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        user_name   TEXT DEFAULT 'Anonymous',
        location    TEXT NOT NULL,
        rating      INTEGER NOT NULL,
        condition   TEXT,
        comment     TEXT,
        date        TEXT DEFAULT (date('now'))
    );

    CREATE TABLE IF NOT EXISTS checkins (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        checkpoint_id   TEXT NOT NULL,
        checkpoint_name TEXT NOT NULL,
        altitude        TEXT,
        credits_earned  INTEGER DEFAULT 0,
        timestamp       TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS sos_alerts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        user_name   TEXT,
        sos_type    TEXT NOT NULL,
        symptoms    TEXT,
        latitude    REAL,
        longitude   REAL,
        status      TEXT DEFAULT 'pending',
        timestamp   TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()

    # Seed a demo user if empty
    row = c.execute("SELECT id FROM users LIMIT 1").fetchone()
    if not row:
        pw = hashlib.sha256("demo123".encode()).hexdigest()
        c.execute(
            "INSERT INTO users (name, email, password, avatar, rank, credits) VALUES (?,?,?,?,?,?)",
            ("Maya Gurung", "maya@nepaltrail.com", pw, "MG", "Mountain Navigator", 420)
        )
        conn.commit()
    conn.close()

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def gen_ref():
    import random, string
    return "NT" + "".join(random.choices(string.digits, k=6))

# ── Auth ───────────────────────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    name  = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    pw    = (data.get("password") or "")
    if not name or not email or not pw:
        return jsonify(error="Name, email and password required"), 400
    if len(pw) < 6:
        return jsonify(error="Password must be at least 6 characters"), 400
    avatar = "".join([p[0].upper() for p in name.split()[:2]])
    hashed = hashlib.sha256(pw.encode()).hexdigest()
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO users (name, email, password, avatar) VALUES (?,?,?,?)",
            (name, email, hashed, avatar)
        )
        conn.commit()
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone())
        conn.close()
        user.pop("password", None)
        return jsonify(user=user), 201
    except sqlite3.IntegrityError:
        return jsonify(error="Email already registered"), 409

@app.route("/api/auth/login", methods=["POST"])
def login():
    data  = request.get_json()
    email = (data.get("email") or "").strip().lower()
    pw    = (data.get("password") or "")
    hashed = hashlib.sha256(pw.encode()).hexdigest()
    conn = get_db()
    user = row_to_dict(conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?", (email, hashed)
    ).fetchone())
    conn.close()
    if not user:
        return jsonify(error="Invalid email or password"), 401
    user.pop("password", None)
    return jsonify(user=user)

# ── Users ──────────────────────────────────────────────────────────────────

@app.route("/api/user/<int:uid>", methods=["GET"])
def get_user(uid):
    conn = get_db()
    user = row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    conn.close()
    if not user:
        return jsonify(error="User not found"), 404
    user.pop("password", None)
    return jsonify(user=user)

@app.route("/api/user/<int:uid>/credits", methods=["PUT"])
def update_credits(uid):
    data   = request.get_json()
    delta  = int(data.get("delta", 0))
    conn   = get_db()
    conn.execute("UPDATE users SET credits = credits + ? WHERE id=?", (delta, uid))
    conn.commit()
    user = row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    conn.close()
    user.pop("password", None)
    return jsonify(user=user)

# ── Static catalog data ────────────────────────────────────────────────────

ROUTES_DATA = [
    {"id":"ebc","name":"Everest Base Camp","emoji":"🏔️","days":14,"diff":"Hard","dist":"130 km","elev":"5,364m","region":"Khumbu","checkpoints":["Lukla","Phakding","Namche Bazaar","Tengboche","Dingboche","Lobuche","Gorak Shep","Base Camp"],"color":"#1B3A5C"},
    {"id":"abc","name":"Annapurna Circuit","emoji":"⛰️","days":21,"diff":"Moderate","dist":"160 km","elev":"5,416m","region":"Gandaki","checkpoints":["Besisahar","Chame","Manang","Thorong La","Muktinath","Jomsom","Tatopani","Pokhara"],"color":"#2D6A4F"},
    {"id":"langtang","name":"Langtang Valley","emoji":"🌿","days":7,"diff":"Easy","dist":"60 km","elev":"3,870m","region":"Bagmati","checkpoints":["Syabrubesi","Lama Hotel","Mundu","Kyanjin Gompa"],"color":"#8B3A3A"},
    {"id":"mardi","name":"Mardi Himal","emoji":"🌄","days":5,"diff":"Easy","dist":"38 km","elev":"4,500m","region":"Gandaki","checkpoints":["Phedi","Forest Camp","High Camp","Base Camp"],"color":"#5C3A8B"},
]

ACCOMMODATIONS_DATA = [
    {"name":"Yak & Yeti Namche","type":"Tea House","price":"$25/night","rating":4.8,"region":"Namche","emoji":"🏡","reviews":142},
    {"name":"Everest View Hotel","type":"Hotel","price":"$85/night","rating":4.9,"region":"Syangboche","emoji":"🏨","reviews":89},
    {"name":"Pheriche Guesthouse","type":"Homestay","price":"$15/night","rating":4.5,"region":"Pheriche","emoji":"🏠","reviews":210},
    {"name":"Tengboche Monastery Lodge","type":"Lodge","price":"$30/night","rating":4.7,"region":"Tengboche","emoji":"🏯","reviews":67},
    {"name":"Lakeside Resort Pokhara","type":"Hotel","price":"$60/night","rating":4.6,"region":"Pokhara","emoji":"🌊","reviews":304},
    {"name":"Thamel Heritage Inn","type":"Hotel","price":"$45/night","rating":4.4,"region":"Kathmandu","emoji":"🏛️","reviews":189},
]

GUIDES_DATA = [
    {"name":"Pemba Sherpa","langs":["English","Nepali","Tibetan"],"exp":12,"routes":["EBC","Everest","Cho Oyu"],"rating":4.9,"certified":True,"reviews":87,"badge":"🏅"},
    {"name":"Sunita Tamang","langs":["English","Nepali","Hindi"],"exp":8,"routes":["Annapurna","Langtang"],"rating":4.8,"certified":True,"reviews":64,"badge":"🏆"},
    {"name":"Dawa Lama","langs":["English","Nepali"],"exp":15,"routes":["EBC","Makalu","Kanchenjunga"],"rating":5.0,"certified":True,"reviews":112,"badge":"🌟"},
    {"name":"Nima Dorji","langs":["English","Nepali","Chinese"],"exp":6,"routes":["Mardi","Ghorepani"],"rating":4.6,"certified":False,"reviews":38,"badge":""},
]

TRANSPORT_DATA = [
    {"name":"Kathmandu → Pokhara","type":"Tourist Bus","duration":"6–7 hr","price":"$12","seats":8,"dep":"07:00","emoji":"🚌"},
    {"name":"Pokhara → Jomsom","type":"Mountain Flight","duration":"20 min","price":"$115","seats":2,"dep":"06:30","emoji":"✈️"},
    {"name":"Kathmandu → Lukla","type":"Domestic Flight","duration":"35 min","price":"$180","seats":3,"dep":"06:00","emoji":"🛩️"},
    {"name":"Sunauli → Pokhara","type":"Tourist Bus","duration":"5 hr","price":"$8","seats":12,"dep":"08:00","emoji":"🚌"},
]

@app.route("/api/routes")
def get_routes():
    return jsonify(routes=ROUTES_DATA)

@app.route("/api/accommodations")
def get_accommodations():
    return jsonify(accommodations=ACCOMMODATIONS_DATA)

@app.route("/api/guides")
def get_guides():
    return jsonify(guides=GUIDES_DATA)

@app.route("/api/transport")
def get_transport():
    return jsonify(transport=TRANSPORT_DATA)

# ── Bookings ───────────────────────────────────────────────────────────────

@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    uid = request.args.get("user_id")
    conn = get_db()
    if uid:
        rows = rows_to_list(conn.execute(
            "SELECT * FROM bookings WHERE user_id=? ORDER BY id DESC", (uid,)
        ).fetchall())
    else:
        rows = rows_to_list(conn.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall())
    conn.close()
    return jsonify(bookings=rows)

@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json()
    uid  = data.get("user_id")
    if not uid:
        return jsonify(error="user_id required"), 400
    ref = gen_ref()
    conn = get_db()
    conn.execute(
        "INSERT INTO bookings (user_id, item_name, item_type, price, emoji, booking_ref) VALUES (?,?,?,?,?,?)",
        (uid, data.get("item_name",""), data.get("item_type",""), data.get("price",""), data.get("emoji",""), ref)
    )
    conn.commit()
    row = row_to_dict(conn.execute("SELECT * FROM bookings WHERE booking_ref=?", (ref,)).fetchone())
    conn.close()
    return jsonify(booking=row, ref=ref), 201

# ── Feedbacks ──────────────────────────────────────────────────────────────

@app.route("/api/feedbacks", methods=["GET"])
def get_feedbacks():
    conn = get_db()
    rows = rows_to_list(conn.execute("SELECT * FROM feedbacks ORDER BY id DESC LIMIT 50").fetchall())
    conn.close()
    return jsonify(feedbacks=rows)

@app.route("/api/feedbacks", methods=["POST"])
def create_feedback():
    data = request.get_json()
    loc  = (data.get("location") or "").strip()
    if not loc:
        return jsonify(error="location required"), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO feedbacks (user_id, user_name, location, rating, condition, comment) VALUES (?,?,?,?,?,?)",
        (data.get("user_id"), data.get("user_name","Anonymous"), loc,
         int(data.get("rating", 5)), data.get("condition",""), data.get("comment",""))
    )
    conn.commit()
    row = row_to_dict(conn.execute("SELECT * FROM feedbacks ORDER BY id DESC LIMIT 1").fetchone())
    conn.close()
    return jsonify(feedback=row), 201

# ── Check-ins ──────────────────────────────────────────────────────────────

@app.route("/api/checkins", methods=["GET"])
def get_checkins():
    uid = request.args.get("user_id")
    conn = get_db()
    if uid:
        rows = rows_to_list(conn.execute(
            "SELECT * FROM checkins WHERE user_id=? ORDER BY id DESC", (uid,)
        ).fetchall())
    else:
        rows = rows_to_list(conn.execute("SELECT * FROM checkins ORDER BY id DESC LIMIT 100").fetchall())
    conn.close()
    return jsonify(checkins=rows)

@app.route("/api/checkins", methods=["POST"])
def create_checkin():
    data = request.get_json()
    uid  = data.get("user_id")
    if not uid:
        return jsonify(error="user_id required"), 400
    credits = int(data.get("credits_earned", 0))
    conn = get_db()
    # Prevent double check-in at same checkpoint
    existing = conn.execute(
        "SELECT id FROM checkins WHERE user_id=? AND checkpoint_id=?",
        (uid, data.get("checkpoint_id",""))
    ).fetchone()
    if existing:
        conn.close()
        return jsonify(error="Already checked in at this checkpoint"), 409
    conn.execute(
        "INSERT INTO checkins (user_id, checkpoint_id, checkpoint_name, altitude, credits_earned) VALUES (?,?,?,?,?)",
        (uid, data.get("checkpoint_id",""), data.get("checkpoint_name",""), data.get("altitude",""), credits)
    )
    conn.execute("UPDATE users SET credits = credits + ? WHERE id=?", (credits, uid))
    conn.commit()
    user = row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    conn.close()
    user.pop("password", None)
    return jsonify(success=True, credits=user["credits"]), 201

# ── SOS ────────────────────────────────────────────────────────────────────

@app.route("/api/sos", methods=["POST"])
def create_sos():
    data = request.get_json()
    sos_type = (data.get("sos_type") or "").strip()
    if not sos_type:
        return jsonify(error="sos_type required"), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO sos_alerts (user_id, user_name, sos_type, symptoms, latitude, longitude) VALUES (?,?,?,?,?,?)",
        (data.get("user_id"), data.get("user_name","Unknown"), sos_type,
         json.dumps(data.get("symptoms", [])),
         data.get("latitude"), data.get("longitude"))
    )
    conn.commit()
    conn.close()
    return jsonify(success=True, message="SOS alert recorded"), 201

@app.route("/api/sos", methods=["GET"])
def get_sos():
    uid = request.args.get("user_id")
    conn = get_db()
    if uid:
        rows = rows_to_list(conn.execute(
            "SELECT * FROM sos_alerts WHERE user_id=? ORDER BY id DESC", (uid,)
        ).fetchall())
    else:
        rows = rows_to_list(conn.execute("SELECT * FROM sos_alerts ORDER BY id DESC LIMIT 50").fetchall())
    conn.close()
    return jsonify(alerts=rows)

# ── Health check ───────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify(status="ok", db=DB_PATH)

# ── Serve frontend ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("public", "index.html")

# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("✅  Database initialised:", DB_PATH)
    print("🚀  Starting NepalTrail server on http://localhost:5000")
    app.run(debug=True, port=5000)
