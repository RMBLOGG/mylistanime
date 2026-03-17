from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://mafnnqttvkdgqqxczqyt.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1hZm5ucXR0dmtkZ3FxeGN6cXl0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4NzQyMDEsImV4cCI6MjA4NzQ1MDIwMX0.YRh1oWVKnn4tyQNRbcPhlSyvr7V_1LseWN7VjcImb-Y")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ── Pages ──────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/explore")
def explore():
    return render_template("explore.html")

@app.route("/list/<list_id>")
def view_list(list_id):
    return render_template("view_list.html", list_id=list_id)

# ── API: Search anime via Jikan ────────────────────────
@app.route("/api/search")
def search_anime():
    q = request.args.get("q", "")
    if not q:
        return jsonify([])
    try:
        r = requests.get(
            f"https://api.jikan.moe/v4/anime?q={q}&limit=10&sfw=true",
            timeout=10
        )
        data = r.json().get("data", [])
        results = []
        for a in data:
            results.append({
                "mal_id": a["mal_id"],
                "title": a["title"],
                "title_en": a.get("title_english") or a["title"],
                "image": a["images"]["jpg"]["large_image_url"],
                "score": a.get("score"),
                "year": a.get("year"),
                "episodes": a.get("episodes"),
                "type": a.get("type"),
            })
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── API: Save list to Supabase ─────────────────────────
@app.route("/api/save", methods=["POST"])
def save_list():
    body = request.json
    username = body.get("username", "").strip()
    anime_list = body.get("anime_list", [])

    if not username or len(anime_list) != 9:
        return jsonify({"error": "Username wajib diisi dan pilih tepat 9 anime"}), 400

    payload = {
        "username": username,
        "anime_list": anime_list,  # array of {mal_id, title, image}
    }

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/anime_lists",
        headers=SUPABASE_HEADERS,
        json=payload,
        timeout=10
    )

    if r.status_code in (200, 201):
        data = r.json()
        return jsonify({"success": True, "id": data[0]["id"]})
    else:
        return jsonify({"error": r.text}), 500

# ── API: Get all lists from Supabase ───────────────────
@app.route("/api/lists")
def get_lists():
    page = int(request.args.get("page", 1))
    limit = 12
    offset = (page - 1) * limit

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/anime_lists?select=*&order=created_at.desc&limit={limit}&offset={offset}",
        headers=SUPABASE_HEADERS,
        timeout=10
    )
    return jsonify(r.json())

# ── API: Get single list ───────────────────────────────
@app.route("/api/list/<list_id>")
def get_list(list_id):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/anime_lists?id=eq.{list_id}&select=*",
        headers=SUPABASE_HEADERS,
        timeout=10
    )
    data = r.json()
    if data:
        return jsonify(data[0])
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
