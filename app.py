from flask import Flask, render_template, request, jsonify
import requests
import random
import string

app = Flask(__name__)

SUPABASE_URL = "https://mafnnqttvkdgqqxczqyt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1hZm5ucXR0dmtkZ3FxeGN6cXl0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4NzQyMDEsImV4cCI6MjA4NzQ1MDIwMX0.YRh1oWVKnn4tyQNRbcPhlSyvr7V_1LseWN7VjcImb-Y"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def gen_pin():
    """Generate 6-digit alphanumeric PIN"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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

@app.route("/drafts")
def drafts_page():
    return render_template("drafts.html")

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

    if not username:
        return jsonify({"error": "Username wajib diisi"}), 400
    if len(anime_list) < 1:
        return jsonify({"error": "Pilih minimal 1 anime"}), 400

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/anime_lists",
        headers=SUPABASE_HEADERS,
        json={"username": username, "anime_list": anime_list},
        timeout=10
    )
    if r.status_code in (200, 201):
        return jsonify({"success": True, "id": r.json()[0]["id"]})
    return jsonify({"error": r.text}), 500

# ── API: Get all lists ─────────────────────────────────
@app.route("/api/lists")
def get_lists():
    page = int(request.args.get("page", 1))
    limit = 12
    offset = (page - 1) * limit
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/anime_lists?select=*&order=created_at.desc&limit={limit}&offset={offset}",
        headers=SUPABASE_HEADERS, timeout=10
    )
    return jsonify(r.json())

# ── API: Get single list ───────────────────────────────
@app.route("/api/list/<list_id>")
def get_list(list_id):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/anime_lists?id=eq.{list_id}&select=*",
        headers=SUPABASE_HEADERS, timeout=10
    )
    data = r.json()
    if data:
        return jsonify(data[0])
    return jsonify({"error": "Not found"}), 404

# ════════════════════════════════════════
# DRAFT API
# ════════════════════════════════════════

# ── Buat draft baru ────────────────────
@app.route("/api/draft/create", methods=["POST"])
def create_draft():
    body = request.json
    username = body.get("username", "").strip()
    anime_list = body.get("anime_list", [])
    title = body.get("title", "Draft baru").strip()

    if not username:
        return jsonify({"error": "Username wajib diisi"}), 400

    pin = gen_pin()
    # pastikan PIN unik
    for _ in range(5):
        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/anime_drafts?pin=eq.{pin}&select=id",
            headers=SUPABASE_HEADERS, timeout=10
        )
        if not check.json():
            break
        pin = gen_pin()

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/anime_drafts",
        headers=SUPABASE_HEADERS,
        json={"username": username, "anime_list": anime_list, "title": title, "pin": pin},
        timeout=10
    )
    if r.status_code in (200, 201):
        data = r.json()[0]
        return jsonify({"success": True, "id": data["id"], "pin": pin})
    return jsonify({"error": r.text}), 500

# ── Ambil semua draft by PIN ───────────
@app.route("/api/draft/list")
def get_drafts():
    pin = request.args.get("pin", "").strip().upper()
    if not pin:
        return jsonify({"error": "PIN wajib diisi"}), 400

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/anime_drafts?pin=eq.{pin}&select=*&order=updated_at.desc",
        headers=SUPABASE_HEADERS, timeout=10
    )
    data = r.json()
    if isinstance(data, list):
        return jsonify(data)
    return jsonify({"error": "Tidak ditemukan"}), 404

# ── Update draft ───────────────────────
@app.route("/api/draft/update/<draft_id>", methods=["POST"])
def update_draft(draft_id):
    body = request.json
    pin = body.get("pin", "").strip().upper()
    if not pin:
        return jsonify({"error": "PIN wajib"}), 400

    # verifikasi PIN cocok dengan draft
    check = requests.get(
        f"{SUPABASE_URL}/rest/v1/anime_drafts?id=eq.{draft_id}&pin=eq.{pin}&select=id",
        headers=SUPABASE_HEADERS, timeout=10
    )
    if not check.json():
        return jsonify({"error": "PIN salah atau draft tidak ditemukan"}), 403

    update_data = {}
    if "anime_list" in body: update_data["anime_list"] = body["anime_list"]
    if "username" in body:   update_data["username"]   = body["username"].strip()
    if "title" in body:      update_data["title"]      = body["title"].strip()

    headers = {**SUPABASE_HEADERS, "Prefer": "return=representation"}
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/anime_drafts?id=eq.{draft_id}",
        headers=headers, json=update_data, timeout=10
    )
    if r.status_code in (200, 201):
        return jsonify({"success": True})
    return jsonify({"error": r.text}), 500

# ── Hapus draft ────────────────────────
@app.route("/api/draft/delete/<draft_id>", methods=["DELETE"])
def delete_draft(draft_id):
    pin = request.args.get("pin", "").strip().upper()
    if not pin:
        return jsonify({"error": "PIN wajib"}), 400

    check = requests.get(
        f"{SUPABASE_URL}/rest/v1/anime_drafts?id=eq.{draft_id}&pin=eq.{pin}&select=id",
        headers=SUPABASE_HEADERS, timeout=10
    )
    if not check.json():
        return jsonify({"error": "PIN salah atau draft tidak ditemukan"}), 403

    r = requests.delete(
        f"{SUPABASE_URL}/rest/v1/anime_drafts?id=eq.{draft_id}",
        headers=SUPABASE_HEADERS, timeout=10
    )
    if r.status_code in (200, 204):
        return jsonify({"success": True})
    return jsonify({"error": r.text}), 500

# ── Publish draft → jadi list publik ──
@app.route("/api/draft/publish/<draft_id>", methods=["POST"])
def publish_draft(draft_id):
    body = request.json
    pin = body.get("pin", "").strip().upper()
    if not pin:
        return jsonify({"error": "PIN wajib"}), 400

    # ambil draft
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/anime_drafts?id=eq.{draft_id}&pin=eq.{pin}&select=*",
        headers=SUPABASE_HEADERS, timeout=10
    )
    drafts = r.json()
    if not drafts:
        return jsonify({"error": "PIN salah atau draft tidak ditemukan"}), 403

    draft = drafts[0]
    # simpan ke anime_lists
    r2 = requests.post(
        f"{SUPABASE_URL}/rest/v1/anime_lists",
        headers=SUPABASE_HEADERS,
        json={"username": draft["username"], "anime_list": draft["anime_list"]},
        timeout=10
    )
    if r2.status_code in (200, 201):
        list_id = r2.json()[0]["id"]
        return jsonify({"success": True, "id": list_id})
    return jsonify({"error": r2.text}), 500

if __name__ == "__main__":
    app.run(debug=True)
