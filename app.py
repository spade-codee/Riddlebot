from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit
import requests
import random
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "riddlesecret"
socketio = SocketIO(app)

current_riddle = None
leaderboard = {}
visitors = set()

# quiz_quips.py

wrong_quips = [
    # Naija Roasts
    "Nope! Even a chicken go reason faster!",
    "Wrong! Your brain dey do sabbatical leave!",
    "Omo, na zero you carry come abi?",
    "You miss am! Even NEPA dey disappoint less!",
    "Incorrect! Try use your head small — not for decoration!",
    "You answer like say you dey dream with eyes open!",
    "My guy, that response weak like Monday morning vibes!",
    "Your brain just dey play hide and seek!",
    "You dey answer like person wey dey find network!",

    # British Insults
    "Nah fam, your thinking cap is clearly missing!",
    "Wrong again! Did your common sense go on holiday?",
    "Flopped it! Even a broken kettle has more logic!",
    "You what?! That was tragic, mate!",
    "Oi, you sure you’re not just guessing for vibes?",
    "That answer’s about as useful as a chocolate teapot!",
    "You’ve absolutely bottled it, haven’t you?",
    "Blimey! Even the Queen’s corgi would’ve done better!"
]

right_quips = [
    # Naija Wins
    "Correct! You sabi something today!",
    "Ehn ehn! This your head get small oil o!",
    "Sharp! You finally connect the wires!",
    "You got it! Brain don wake up small!",
    "Yes boss! Even your ancestors dey proud!",
    "Wawu! You no dull this one at all!",
    "You try! Even village people dey fear you now!",
    "Clean answer! You dey move like person wey chop correct yam!",
    "Ah! You burst my head with this one o!",

    # British Wit
    "Spot on! You’re not just vibes after all!",
    "Right! You reason am well, no cap!",
    "Top marks! That’s some tidy brainwork!",
    "Nailed it! Proper clever, that one!",
    "Well done, mate! Didn’t think you had it in ya!",
    "Correctamundo! Brains over beans today!",
    "Bang on! You’re cooking with actual logic!",
    "You’ve smashed it, smartypants!"
]

streak_quips = {
    2: "Two correct back-to-back! You dey warm up like gen!",
    3: "Three straight! You no come here to joke o!",
    5: "FIVE in a row! Big brain dey your side today!",
    7: "SEVEN?! Be like say na you dey set the questions!",
    10: "TEN?! You don join mental hall of fame!",
    13: "THIRTEEN correct? My guy, open church for brilliance!",
    15: "Fifteen! Crikey! You’re on fire, genius!",
    20: "TWENTY?! Who be this?! You dey read minds?"
}

break_quips = [
    # Naija Fail Banter
    "Omo, streak don break like Okada brake!",
    "Ah! You fall hand just now — try again abeg!",
    "Crash! Your hot streak just cool like harmattan breeze!",
    "Na from hero to zero be this one o!",
    "Village people just off your shine like NEPA!",
    "Your brain jam like Lagos traffic!",

    # British Burn
    "Oops! You’ve dropped the ball, mate!",
    "Streak’s gone—tea break for your brain!",
    "You were flying... then crashed like a Poundland rocket.",
    "Well, that escalated... downwards.",
    "You fumbled the bag harder than a British weather forecast!"
]


def fetch_api_riddle():
    try:
        response = requests.get("https://riddles-api.vercel.app/random", timeout=5)
        data = response.json()
        return {"q": data["riddle"], "a": data["answer"].lower(), "answered": None}
    except Exception as e:
        print(f"API error: {e}")
        return {"q": "What’s always running but never moves?", "a": "clock", "answered": None}

@app.route("/")
def index():
    session.setdefault("points", 0)
    session.setdefault("streak", 0)
    session.setdefault("username", f"Anon{random.randint(1000, 9999)}")
    visitors.add(request.remote_addr)
    if session["username"] not in leaderboard:
        leaderboard[session["username"]] = session["points"]
    return render_template("index.html", points=session["points"], streak=session["streak"],
                         username=session["username"], leaderboard=leaderboard, visitor_count=len(visitors),
                         github="https://github.com/yourusername",  # Replace
                         instagram="https://instagram.com/yourusername",  # Replace
                         x="https://x.com/yourusername")  # Replace

@socketio.on("message")
def handle_message(data):
    global current_riddle, leaderboard
    msg = data.strip().lower()

    if msg.startswith("setname "):
        old_name = session["username"]
        new_name = msg.replace("setname ", "").strip()
        if new_name:
            session["username"] = new_name[:15]
            leaderboard[session["username"]] = leaderboard.pop(old_name, 0)
            emit("message", f"Riddle Bot: {old_name} is now {session['username']}!", broadcast=True)
            emit("leaderboard", leaderboard, broadcast=True)
        return

    if msg == "/riddle":
        if not current_riddle:
            current_riddle = fetch_api_riddle()
            emit("message", f"Riddle Bot: {current_riddle['q']}", broadcast=True)
        elif current_riddle["answered"] is False:
            current_riddle = fetch_api_riddle()
            emit("message", f"Riddle Bot: Next twisted riddle: {current_riddle['q']}", broadcast=True)
        else:
            emit("message", "Riddle Bot: Solve the current one first, you impatient bat!", to=request.sid)
    elif current_riddle:
        if msg == current_riddle["a"]:
            session["points"] += 1
            session["streak"] += 1
            leaderboard[session["username"]] = session["points"]
            streak_msg = streak_quips.get(session["streak"], "")
            emit("message", f"Riddle Bot: {random.choice(right_quips)} {session['username']} scores! "
                            f"Points: {session['points']} {streak_msg}", broadcast=True)
            if session["streak"] in [2, 3, 5, 7]:
                emit("streak", session["streak"], broadcast=True)
            emit("leaderboard", leaderboard, broadcast=True)
            current_riddle["answered"] = True
            current_riddle = None
        else:
            session["points"] = max(0, session["points"] - 1)
            leaderboard[session["username"]] = session["points"]
            if session["streak"] > 1:
                emit("message", f"Riddle Bot: {random.choice(break_quips)} {session['username']} guessed '{msg}'. "
                                f"Streak lost! Points: {session['points']}", broadcast=True)
                session["streak"] = 0
            else:
                emit("message", f"Riddle Bot: {random.choice(wrong_quips)} Hint: It’s not ‘{msg}’, ya joker! "
                                f"Points: {session['points']} Type /riddle for the next one.", broadcast=True)
            emit("joker", True, broadcast=True)
            emit("leaderboard", leaderboard, broadcast=True)
            current_riddle["answered"] = False
    else:
        emit("message", f"{session['username']}: {msg}", broadcast=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)