from flask import Flask, render_template, session, request, redirect, jsonify
import sqlite3
import time
import cv2
import google.generativeai as genai
import json
import re



app = Flask(__name__)
app.secret_key = 'supersecretkey'

genai.configure(api_key="AIzaSyCG0bleD2eLRcNVkqnuD0kMwbGaIzAFEHo")
model = genai.GenerativeModel("gemini-2.5-flash")
DB_PATH = "autism_data.db"


@app.route("/list-models")
def list_models():
    models = genai.list_models()
    output = ""
    for m in models:
        output += m.name + "<br>"
    return output


@app.route("/test-ai")
def test_ai():
    response = model.generate_content("Say hello in a friendly way")
    return response.text

# ---------------- DB CONNECTION ----------------
import sqlite3
import os

def get_db_connection():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "autism_data.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
# ---------------- HOME / LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        name = request.form.get('name', 'Child')  # default name

        if not phone:
            return "❌ Phone number required", 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔍 Check if user exists
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        existing_user = cursor.fetchone()

        if not existing_user:
            cursor.execute(
                "INSERT INTO users (name, phone) VALUES (?, ?)",
                (name, phone)
            )
            conn.commit()
        conn.close()

        session['user_phone'] = phone
        return redirect('/dashboard')

    return render_template('index.html')


# ---------------- OPEN-CV LEVEL DETECTION ----------------
def run_opencv_model():
    import mediapipe as mp
    import numpy as np
    import cv2
    import time

    mp_face = mp.solutions.face_mesh
    face_mesh = mp_face.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    conn = get_db_connection()
    cursor = conn.cursor()

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("❌ Camera not accessible")
        return

    sad_counter = 0
    SAD_THRESHOLD = 20
    last_save_time = 0

    # Landmark indices
    NOSE = 1
    FACE_TOP = 10
    FACE_BOTTOM = 152
    LEFT_MOUTH = 61
    RIGHT_MOUTH = 291
    LEFT_FACE = 234
    RIGHT_FACE = 454

    def get_point(landmarks, idx, w, h):
        lm = landmarks[idx]
        return int(lm.x * w), int(lm.y * h)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        # Default values
        focus_status = "No Face"
        head_status = "CENTER"
        smile_status = "NO"
        emotion_status = "CALM 😐"

        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark

            # Focus calculation
            nose_x, nose_y = get_point(lm, NOSE, w, h)
            face_top_y = get_point(lm, FACE_TOP, w, h)[1]
            face_bottom_y = get_point(lm, FACE_BOTTOM, w, h)[1]
            face_center_y = (face_top_y + face_bottom_y) // 2

            focus_status = "Focused" if abs(nose_x - (w // 2)) < w * 0.10 else "Looking Away"

            # Head direction
            if nose_y > face_center_y + 10:
                head_status = "DOWN"
            elif nose_y < face_center_y - 10:
                head_status = "UP"

            # Smile detection
            lm_left_mouth = get_point(lm, LEFT_MOUTH, w, h)
            lm_right_mouth = get_point(lm, RIGHT_MOUTH, w, h)
            lm_left_face = get_point(lm, LEFT_FACE, w, h)
            lm_right_face = get_point(lm, RIGHT_FACE, w, h)

            mouth_width = np.linalg.norm(np.array(lm_left_mouth) - np.array(lm_right_mouth))
            face_width = np.linalg.norm(np.array(lm_left_face) - np.array(lm_right_face))

            smile_ratio = mouth_width / face_width
            smile_status = "YES" if smile_ratio > 0.40 else "NO"

            # Emotion detection
            if focus_status == "Looking Away" and head_status == "DOWN":
                sad_counter += 1
            else:
                sad_counter = 0

            if smile_status == "YES":
                emotion_status = "HAPPY 🙂"
            elif sad_counter >= SAD_THRESHOLD:
                emotion_status = "SAD 😞"

        # Save behavior every 2 seconds
        if time.time() - last_save_time > 2:
            cursor.execute("""
                INSERT INTO behavior_log (timestamp, focus, head, smile, emotion)
                VALUES (?, ?, ?, ?, ?)
            """, (
                time.strftime("%Y-%m-%d %H:%M:%S"),
                focus_status, head_status, smile_status, emotion_status
            ))
            conn.commit()
            last_save_time = time.time()

        # ---------------- DISPLAY TEXT ON FRAME ----------------
        cv2.putText(frame, f"Focus: {focus_status}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"Head: {head_status}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(frame, f"Smile: {smile_status}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(frame, f"Emotion: {emotion_status}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)

        # Show camera
        cv2.imshow("Level Identification", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()
    conn.close()


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")


# ---------------- LEVEL IDENTIFICATION ----------------
@app.route("/start-session")
def level_identification():

    try:
        print("Camera starting...")

        run_opencv_model()

        print("Camera closed")

        return redirect("/analysis")

    except Exception as e:
        print("ERROR:", e)
        return "Camera error"
# ---------------- ANALYSIS ----------------
@app.route("/analysis")
def analysis():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all session data
    cursor.execute("SELECT * FROM behavior_log")
    rows = cursor.fetchall()

    conn.close()

    total = len(rows)

    if total == 0:
        return render_template(
            "analysis.html",
            analysis={"focus": 0, "head": 0, "smile": 0, "emotion": 0},
            interpretation="No session data found.",
            recommendations=["Start a session first."]
        )

    # Count metrics
    focused_count = sum(1 for row in rows if row["focus"] == "Focused")
    smile_count = sum(1 for row in rows if row["smile"] == "YES")
    happy_count = sum(1 for row in rows if "HAPPY" in row["emotion"])
    head_center_count = sum(1 for row in rows if row["head"] == "CENTER")

    # Convert to percentage
    analysis_data = {
        "focus": int((focused_count / total) * 100),
        "head": int((head_center_count / total) * 100),
        "smile": int((smile_count / total) * 100),
        "emotion": int((happy_count / total) * 100)
    }

    # Simple interpretation logic
    if analysis_data["focus"] > 70:
        interpretation = "Excellent focus observed."
    elif analysis_data["focus"] > 40:
        interpretation = "Moderate focus level."
    else:
        interpretation = "Needs improvement in attention."

    recommendations = [
        "Encourage eye contact exercises",
        "Use shorter learning sessions",
        "Reinforce positive emotions"
    ]

    return render_template(
        "analysis.html",
        analysis=analysis_data,
        interpretation=interpretation,
        recommendations=recommendations,
        time=time
    )
# ---------------- OTHER MODULE ROUTES ----------------
def get_analysis_data():
    return {
        "eye_contact": 78,
        "attention": 85,
        "engagement": 92
        }
@app.route("/generate-scenario")
def generate_scenario():
    try:
        prompt = """
        Generate a VERY SHORT social situation for a 5-8 year old child.
        Maximum 2 short sentences.
        Very simple English.

        Return ONLY JSON:
        {
         "scenario": "...",
         "optionA": "...",
         "optionB": "...",
         "optionC": "...",
         "correctAnswer": "A or B or C"
        }
        """

        response = model.generate_content(prompt)

        raw_text = response.text.strip()
        cleaned_text = re.sub(r"```json|```", "", raw_text).strip()

        data = json.loads(cleaned_text)

        return jsonify(data)

    except Exception as e:
        print("Error:", e)

        return jsonify({
            "scenario": "You are playing with a toy.",
            "optionA": "Keep playing.",
            "optionB": "Share the toy.",
            "optionC": "Walk away."
        })
@app.route("/evaluate-answer", methods=["POST"])
def evaluate_answer():
    try:
        data = request.json
        user_input = data.get("answer")
        correct_answer = data.get("correctAnswer")

        prompt = f"""
The correct answer is: "{correct_answer}"
The child answered: "{user_input}"

If the child is correct:
Say one short happy sentence.

If the child is wrong:
Say one short gentle sentence asking them to try again.

Rules:
- Only 1 short sentence.
- Maximum 10 words.
- Very simple words.
"""

        response = model.generate_content(prompt)
        ai_reply = response.text.strip()

        return jsonify({"reply": ai_reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"reply": "Good try! Try again."})
    # Voice Chat
@app.route('/ai-chat', methods=['POST'])
def ai_chat():
    message = request.json['message']

    prompt = f"""
    You are a friendly AI assistant helping autistic children learn emotions and social skills.

    Rules:
    - Use simple English
    - Maximum 2 short sentences
    - Be kind and encouraging
    - Do not give medical advice

    Child said: "{message}"
    """

    try:
        response = model.generate_content(prompt)
        return jsonify({"reply": response.text})
    except Exception:
        return jsonify({"reply": "I am happy you are talking to me 😊"})


@app.route('/eye-training')
def eye_training():
    return redirect('/learning')

@app.route('/learning')
def learning():
    analysis = get_analysis_data()
    return render_template("learning.html", analysis=analysis)


@app.route("/speech")
def speech():
    return render_template("speech.html")


@app.route("/emotion")
def emotion():
    return render_template("emotion.html")


@app.route("/focus")
def focus():
    return render_template("focus.html")

@app.route('/ai-trainer')
def ai_trainer():
    return render_template("aitrainer.html")



@app.route("/weekly")
def weekly():
    return render_template("weekly.html")


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)
