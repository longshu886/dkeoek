from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import time
import os
import json

app = Flask(__name__)

# ---------------------------------------------------------
# Initialize Firebase
# ---------------------------------------------------------
try:
    firebase_json = os.environ.get("FIREBASE_CONFIG_JSON")
    if firebase_json:
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("🔥 [FIREBASE] Initialized from environment variable.")
    elif os.path.exists('serviceAccountKey.json'):
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
        print("🔥 [FIREBASE] Initialized from local file.")
    else:
        print("⚠️ [WARNING] No Firebase credentials found!")

    db = firestore.client() if firebase_admin._apps else None
except Exception as e:
    print(f"❌ [FIREBASE ERROR]: {e}")
    db = None


# ---------------------------------------------------------
# ROUTE 0: Health check (Render 用)
# ---------------------------------------------------------
@app.route('/', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "db": db is not None,
    }), 200


# ---------------------------------------------------------
# ROUTE 1: Receive Telemetry (POST /report)
# ---------------------------------------------------------
@app.route('/report', methods=['POST'])
def report_server():
    if not db:
        return jsonify({"error": "Database not initialized"}), 500

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    job_id      = data.get('jobId')
    place_id    = data.get('placeId')
    egg_type    = data.get('eggType', 'Unknown Egg')
    rarity_score = data.get('rarityScore', 0)
    player_count = data.get('playerCount', 0)

    if not job_id or not place_id:
        return jsonify({"error": "Missing jobId or placeId"}), 400

    # 统一转字符串，避免类型不一致
    job_id   = str(job_id)
    place_id = str(place_id)

    print(f"📥 [REPORT] Game: {place_id} | Server: {job_id} | Egg: {egg_type} | Score: {rarity_score}")

    doc_ref = db.collection('active_servers').document(job_id)
    doc_ref.set({
        'placeId':     place_id,
        'jobId':       job_id,
        'eggType':     egg_type,
        'rarityScore': rarity_score,
        'playerCount': player_count,
        'lastSeen':    time.time(),
    })

    return jsonify({"status": "success"}), 200


# ---------------------------------------------------------
# ROUTE 2: Get Active Servers (GET /servers/<place_id>)
# ---------------------------------------------------------
@app.route('/servers/<int:place_id>', methods=['GET'])
def get_servers(place_id):
    if not db:
        return jsonify({"error": "Database not initialized"}), 500

    place_id_str = str(place_id)
    docs = db.collection('active_servers').where('placeId', '==', place_id_str).stream()

    server_list  = []
    current_time = time.time()

    for doc in docs:
        server_data = doc.to_dict()
        # 只返回 90 秒内还活着的服务器
        if current_time - server_data.get('lastSeen', 0) < 90:
            server_list.append(server_data)

    # 按稀有度分数降序
    server_list.sort(key=lambda x: x.get('rarityScore', 0), reverse=True)

    print(f"📤 [GET SERVERS] Game {place_id_str} → {len(server_list)} server(s)")
    return jsonify({"servers": server_list}), 200


# ---------------------------------------------------------
# Entry point (本地测试用；Render 用 gunicorn)
# ---------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)