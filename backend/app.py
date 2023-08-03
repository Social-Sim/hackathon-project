from flask import (
    Flask,
    request,
    make_response,
    jsonify,
)
from scene import Scene
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Scene Data
s = Scene("", [], app.logger)

# Set up a rotating file handler for the logger
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

# Set the log level to INFO
app.logger.setLevel(logging.INFO)

@app.route('/test', methods=['GET'])
def test():
    return 'It works!'

@app.route('/scene/setup', methods=['POST'])
def setup_scene():
    global s

    data = request.json

    social_skill = data["social_skill"] if "social_skill" in data and data["social_skill"] else None
    goals = data["goals"] if "goals" in data and data["goals"] else None

    if not social_skill or not goals:
        return make_response(jsonify({
            "error_message": "Missing social skill or goals"
        }), 500)

    s = Scene(social_skill, goals, app.logger)

    s.generate_scene()

    return make_response(jsonify(s.as_dict()), 200)

@app.route('/scene/interact', methods=['POST'])
def interact_scene():
    global s

    data = request.json
    print(data)

    if ("user_spoke" not in data) or (data["user_spoke"] and "message" in data and len(data["message"]) == 0):
        return make_response(jsonify({
            "error_message": "Missing user_spoke or message"
        }), 500)

    user_spoke = data["user_spoke"]
    message = data["message"] if "message" in data and data["message"] else ""

    next_message, inner_voice = s.interact(user_spoke, message)

    score = s.scores[-1] if user_spoke else None

    if score and "none" in score:
        score = None
    elif score:
        score = s.score_string(score)

    return make_response(jsonify({
        "message": next_message,
        "inner_voice": inner_voice,
        "score": score
    }), 200)

@app.route('/scene/data', methods=['GET'])
def scene_data():
    global s

    return make_response(jsonify(s.as_dict()), 200)


if __name__ == '__main__':
    app.run()
