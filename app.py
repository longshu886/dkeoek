from flask import Flask, request, jsonify
import time
import os

app = Flask(__name__)

# 不需要 Firebase，直接用内存存数据！
active_servers = {}

@app.route('/', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "db": True
    }), 200

@app.route('/report', methods=['POST'])
def report_server():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    job_id      = str(data.get('jobId', ''))
    place_id    = str(data.get('placeId', ''))
    egg_type    = data.get('eggType', 'Unknown Egg')
    rarity_score = data.get('rarityScore', 0)
    player_count = data.get('playerCount', 0)

    if not job_id or not place_id:
        return jsonify({"error": "Missing jobId or placeId"}), 400

    # 把数据存到服务器的内存里
    active_servers[job_id] = {
        'placeId':     place_id,
        'jobId':       job_id,
        'eggType':     egg_type,
        'rarityScore': rarity_score,
        'playerCount': player_count,
        'lastSeen':    time.time(),
    }
    return jsonify({"status": "success"}), 200

@app.route('/servers/<int:place_id>', methods=['GET'])
def get_servers(place_id):
    place_id_str = str(place_id)
    server_list = []
    current_time = time.time()

    for job_id, data in list(active_servers.items()):
        if data['placeId'] == place_id_str:
            if current_time - data['lastSeen'] < 90:
                server_list.append(data)
            else:
                del active_servers[job_id] # 删掉掉线的服务器

    server_list.sort(key=lambda x: x.get('rarityScore', 0), reverse=True)
    return jsonify({"servers": server_list}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)