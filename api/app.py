from flask import Flask, request, jsonify
from engine.recommendation_engine import generate

app = Flask(__name__)

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.json
    result = generate(
        data["rainfall"],
        data["temperature"]
    )
    return jsonify(result)

@app.route("/", methods=["GET"])
def status():
    return jsonify({
        "status": "Q-CYO API is running",
        "message": "Send farm data to /recommend"
    })

if __name__ == "__main__":
    app.run(debug=True)
