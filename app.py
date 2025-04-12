from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit
import requests
import random
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "riddlesecret"
socketio = SocketIO(app)

leaderboard = {}
visitors = set()

# ❌ Wrong Answers
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

# ✅ Right Answers
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

# 🔥 Streak Quips
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

# 💥 Break Quips
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

def generate_hint(answer):
    hints = {
        "clock": "Think of something that measures time…",
        "bottle": "Think of something you might drink from…",
        "zebra": "Think of an animal with stripes…",
        "shadow": "Think of something that follows you…",
        "echo": "Think of something you hear in a cave…",
        "shirt": "Think of something you wear…",
        "riddle": "Think of a puzzle or game…",
    }
    return hints.get(answer, "Think carefully about the riddle…")

@app.route("/")
def index():
    session.setdefault("points", 0)
    session.setdefault("streak", 0)
    session.setdefault("username", f"Anon{random.randint(1000, 9999)}")
    session.modified = True
    visitors.add(request.remote_addr)
    if session["username"] not in leaderboard:
        leaderboard[session["username"]] = session["points"]
    return render_template("index.html", points=session["points"], streak=session["streak"],
                         username=session["username"], leaderboard=leaderboard, visitor_count=len(visitors),
                         github="https://github.com/yourusername",  # Replace
                         instagram="https://instagram.com/yourusername",  # Replace
                         x="https://x.com/yourusername")  # Replace

@socketio.on("connect")
def handle_connect():
    emit("global_message", "Riddle Bot: Welcome to the global chat! Use /chat to talk.", broadcast=True)

@socketio.on("message")
def handle_message(data):
    global leaderboard
    msg = data.strip().lower()

    if msg.startswith("setname "):
        old_name = session["username"]
        new_name = msg.replace("setname ", "").strip()
        if new_name:
            session["username"] = new_name[:15]
            leaderboard[session["username"]] = leaderboard.pop(old_name, 0)
            session.modified = True
            emit("message", f"Riddle Bot: {old_name} is now {session['username']}!", broadcast=True)
            emit("global_message", f"{old_name} is now {session['username']}!", broadcast=True)
            emit("leaderboard", leaderboard, broadcast=True)
        return

    # Handle /chat and common typos
    if msg.startswith("/chat ") or msg in ["/chat", "/cht", "/cht "]:
        if msg.startswith("/chat "):
            chat_msg = msg.replace("/chat ", "").strip()
            if chat_msg:
                emit("global_message", f"{session['username']}: {chat_msg}", broadcast=True)
                return
        emit("message", "Riddle Bot: Use /chat followed by a message, like /chat Hello! (Did you mean /chat?)", to=request.sid)
        return

    if msg == "/riddle":
        if not session.get("current_riddle"):
            session["current_riddle"] = fetch_api_riddle()
            session.modified = True
            emit("message", f"Riddle Bot: {session['current_riddle']['q']}", to=request.sid)
        elif session["current_riddle"].get("answered") is False:
            session["current_riddle"] = fetch_api_riddle()
            session.modified = True
            emit("message", f"Riddle Bot: Next twisted riddle: {session['current_riddle']['q']}", to=request.sid)
        else:
            emit("message", "Riddle Bot: Solve the current one first, you impatient bat!", to=request.sid)
    elif msg == "/hint":
        if session.get("current_riddle"):
            hint = generate_hint(session["current_riddle"]["a"])
            emit("message", f"Riddle Bot: Hint: {hint}", to=request.sid)
        else:
            emit("message", "Riddle Bot: No riddle active! Type /riddle to start.", to=request.sid)
    elif session.get("current_riddle"):
        if msg == session["current_riddle"]["a"]:
            session["points"] += 1
            session["streak"] += 1
            leaderboard[session["username"]] = session["points"]
            streak_msg = streak_quips.get(session["streak"], "")
            session.modified = True
            emit("message", f"Riddle Bot: {random.choice(right_quips)} You score! "
                            f"Points: {session['points']} {streak_msg}", to=request.sid)
            if session["streak"] in [2, 3, 5, 7]:
                emit("streak", session["streak"], to=request.sid)
            emit("leaderboard", leaderboard, broadcast=True)
            session["current_riddle"] = None
        else:
            session["points"] = max(0, session["points"] - 1)
            leaderboard[session["username"]] = session["points"]
            session.modified = True
            if session["streak"] > 1:
                emit("message", f"Riddle Bot: {random.choice(break_quips)} You guessed '{msg}'. "
                                f"Streak lost! Points: {session['points']}", to=request.sid)
                session["streak"] = 0
            else:
                emit("message", f"Riddle Bot: {random.choice(wrong_quips)} Hint: It’s not ‘{msg}’, ya joker! "
                                f"Points: {session['points']} Type /riddle for the next one.", to=request.sid)
            emit("joker", True, to=request.sid)
            emit("leaderboard", leaderboard, broadcast=True)
            session["current_riddle"]["answered"] = False
    else:
        emit("message", f"{session['username']}: {msg}", to=request.sid)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)