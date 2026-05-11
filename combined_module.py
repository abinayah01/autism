import cv2
import mediapipe as mp
import numpy as np
import sqlite3
import time
import csv
import os

# ---------------- INIT ----------------
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# ---------------- PATHS ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "autism_data.db")

timestamp_str = time.strftime("%Y-%m-%d_%H-%M-%S")
CSV_PATH = os.path.join(BASE_DIR, f"behavior_report_{timestamp_str}.csv")

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS behavior_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    focus TEXT,
    head TEXT,
    smile TEXT,
    emotion TEXT
)
""")
conn.commit()

# ---------- CLEAR PREVIOUS SESSION DATA ----------
#cursor.execute("DELETE FROM behavior_log")
#conn.commit()
#print("🧹 Previous session data cleared")


# ---------------- CAMERA ----------------
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Camera not accessible")
    exit()

# ---------- CLEAR OLD DATA ----------
CLEAR_OLD_DATA = True   # change manually if needed

if CLEAR_OLD_DATA:
    cursor.execute("DELETE FROM behavior_log")
    conn.commit()
    print("🧹 Old data cleared")


# ---------------- VARIABLES ----------------
sad_counter = 0
SAD_THRESHOLD = 20
last_save_time = 0

# ---------------- LANDMARK INDEXES ----------------
NOSE = 1
FACE_TOP = 10
FACE_BOTTOM = 152
LEFT_MOUTH = 61
RIGHT_MOUTH = 291
LEFT_FACE = 234
RIGHT_FACE = 454

# ---------------- FUNCTION ----------------
def get_point(landmarks, idx, w, h):
    lm = landmarks[idx]
    return int(lm.x * w), int(lm.y * h)

# ---------------- MAIN LOOP ----------------
print("🔹 Camera started. Click the camera window and press Q to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    focus_status = "No Face"
    head_status = "CENTER"
    smile_status = "NO"
    emotion = "CALM 😐"

    if results.multi_face_landmarks:
        lm = results.multi_face_landmarks[0].landmark

        nose_x, nose_y = get_point(lm, NOSE, w, h)

        face_top_y = get_point(lm, FACE_TOP, w, h)[1]
        face_bottom_y = get_point(lm, FACE_BOTTOM, w, h)[1]
        face_center_y = (face_top_y + face_bottom_y) // 2

        if abs(nose_x - (w // 2)) < w * 0.10:
            focus_status = "Focused"
        else:
            focus_status = "Looking Away"

        if nose_y > face_center_y + 10:
            head_status = "DOWN"
        elif nose_y < face_center_y - 10:
            head_status = "UP"
        else:
            head_status = "CENTER"

        lm_left_mouth = get_point(lm, LEFT_MOUTH, w, h)
        lm_right_mouth = get_point(lm, RIGHT_MOUTH, w, h)
        lm_left_face = get_point(lm, LEFT_FACE, w, h)
        lm_right_face = get_point(lm, RIGHT_FACE, w, h)

        mouth_width = np.linalg.norm(np.array(lm_left_mouth) - np.array(lm_right_mouth))
        face_width = np.linalg.norm(np.array(lm_left_face) - np.array(lm_right_face))

        smile_ratio = mouth_width / face_width
        smile_status = "YES" if smile_ratio > 0.40 else "NO"

        if focus_status == "Looking Away" and head_status == "DOWN":
            sad_counter += 1
        else:
            sad_counter = 0

        if smile_status == "YES":
            emotion = "HAPPY 🙂"
        elif sad_counter >= SAD_THRESHOLD:
            emotion = "SAD 😞"
        else:
            emotion = "CALM 😐"

        cv2.circle(frame, (nose_x, nose_y), 4, (0, 255, 0), -1)

    # ---------------- SAVE TO DB (2 sec) ----------------
    if time.time() - last_save_time > 2:
        cursor.execute("""
        INSERT INTO behavior_log (timestamp, focus, head, smile, emotion)
        VALUES (?, ?, ?, ?, ?)
        """, (
            time.strftime("%Y-%m-%d %H:%M:%S"),
            focus_status,
            head_status,
            smile_status,
            emotion
        ))
        conn.commit()
        last_save_time = time.time()

        # 🔥 HERE: PRINT DB CONTENT (LAST 5 ROWS)
        print("\n📊 DATABASE CONTENT (Last 5 rows):")
        cursor.execute("SELECT * FROM behavior_log ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(row)

    # ---------------- UI ----------------
    cv2.putText(frame, f"Focus   : {focus_status}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, f"Head    : {head_status}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    cv2.putText(frame, f"Smile   : {smile_status}", (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
    cv2.putText(frame, f"Emotion : {emotion}", (20, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(frame, "Press Q to Quit", (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    cv2.imshow("Autism Assistive System Demo", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == ord('Q'):
        print("🛑 Q pressed. Exiting...")
        break

# ---------------- CLEANUP ----------------
cap.release()
cv2.destroyAllWindows()
cv2.waitKey(1) 
face_mesh.close()

# ---------------- CSV EXPORT ----------------
cursor.execute("SELECT * FROM behavior_log")
rows = cursor.fetchall()

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["ID", "Timestamp", "Focus", "Head", "Smile", "Emotion"])
    writer.writerows(rows)


print(f"📂 CSV saved at: {CSV_PATH}")


conn.close()
print("🔹 Program closed cleanly.")
