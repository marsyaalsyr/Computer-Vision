import cv2
import mediapipe as mp
import pydirectinput
import time
import csv
import os

# ======================================================================
# SETUP DATASET LOG (OTOMATIS UNTUK DOSEN)
# ======================================================================
nama_file_dataset = "dataset_koordinat_subway.csv"

# Jika file belum ada di folder, buat baru dan tulis judul kolomnya
if not os.path.exists(nama_file_dataset):
    with open(nama_file_dataset, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'X_Hidung', 'Y_Bahu_Rata2', 'Posisi_Sumbu', 'Status_Gerakan'])

# ======================================================================
# JALUR BYPASS BUG MEDIAPIPE PYTHON 3.12
# ======================================================================
from mediapipe.python.solutions import pose as mp_pose
from mediapipe.python.solutions import drawing_utils as mp_drawing

pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

print("Sedang mengaktifkan webcam... Harap tunggu sebentar...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

current_position = "Center"  
cooldown_time = 0.4  
last_action_time = time.time()
persentase_merunduk = 0.53  

print("======================================================================")
print("Sistem AI Pelacak Tubuh V3.4 (Dengan Fitur Auto-Save Dataset) Siap!")
print("======================================================================")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        cap = cv2.VideoCapture(0)
        continue

    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb_frame)

    # 1. Gambar Garis Batas Kuning Vertikal (Kiri & Kanan)
    cv2.line(frame, (int(width * 0.35), 0), (int(width * 0.35), height), (0, 255, 255), 2)
    cv2.line(frame, (int(width * 0.65), 0), (int(width * 0.65), height), (0, 255, 255), 2)

    # 2. Gambar Garis Batas Ungu Horizontal (Merunduk)
    cv2.line(frame, (0, int(height * persentase_merunduk)), (width, int(height * persentase_merunduk)), (255, 0, 255), 2)
    cv2.putText(frame, "BATAS MERUNDUK", (10, int(height * persentase_merunduk) - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

    if results.pose_landmarks:
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        landmarks = results.pose_landmarks.landmark
        
        nose_x = int(landmarks[mp_pose.PoseLandmark.NOSE].x * width)
        left_shoulder_y = int(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y * height)
        right_shoulder_y = int(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y * height)
        avg_shoulder_y = (left_shoulder_y + right_shoulder_y) // 2

        # 3. Gambar Garis Batas Hijau Horizontal (Lompat)
        cv2.line(frame, (0, avg_shoulder_y), (width, avg_shoulder_y), (0, 255, 0), 2)
        cv2.putText(frame, "BATAS LOMPAT (ANGKAT TANGAN)", (width - 250, avg_shoulder_y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        left_wrist_y = int(landmarks[mp_pose.PoseLandmark.LEFT_WRIST].y * height)
        right_wrist_y = int(landmarks[mp_pose.PoseLandmark.RIGHT_WRIST].y * height)

        # --- LOGIKA PENERJEMAH GERAKAN & PENCATAT DATASET ---
        current_time = time.time()
        if current_time - last_action_time > cooldown_time:
            
            status_sekarang = "Normal"

            # Gerakan 1: LOMPAT
            if left_wrist_y < avg_shoulder_y or right_wrist_y < avg_shoulder_y:
                pydirectinput.keyDown('up')
                time.sleep(0.05)  
                pydirectinput.keyUp('up')
                cv2.putText(frame, "LOMPAT (PANAH ATAS)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                status_sekarang = "Lompat"
                last_action_time = current_time

            # Gerakan 2: MERUNDUK
            elif avg_shoulder_y > (height * persentase_merunduk): 
                pydirectinput.keyDown('down')
                time.sleep(0.05)
                pydirectinput.keyUp('down')
                cv2.putText(frame, "MERUNDUK (PANAH BAWAH)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                status_sekarang = "Merunduk"
                last_action_time = current_time

            # Gerakan 3: KIRI
            elif nose_x < int(width * 0.35):
                if current_position != "Left":
                    pydirectinput.keyDown('left')
                    time.sleep(0.05)
                    pydirectinput.keyUp('left')
                    current_position = "Left"
                    status_sekarang = "Geser Kiri"
                    last_action_time = current_time
            
            # Gerakan 4: KANAN
            elif nose_x > int(width * 0.65):
                if current_position != "Right":
                    pydirectinput.keyDown('right')
                    time.sleep(0.05)
                    pydirectinput.keyUp('right')
                    current_position = "Right"
                    status_sekarang = "Geser Kanan"
                    last_action_time = current_time
            
            else:
                current_position = "Center"
            
            # JIKA ADA GERAKAN AKTIF, CATAT KE FILE DATASET CSV
            if status_sekarang != "Normal":
                waktu_log = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(nama_file_dataset, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([waktu_log, nose_x, avg_shoulder_y, current_position, status_sekarang])

    else:
        cv2.putText(frame, "PASTIKAN KAMERA MENYALA & MUNDUR SEBENTAR", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.putText(frame, f"Posisi Tubuh: {current_position}", (50, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    cv2.imshow("AI Body Tracker - Subway Surfers Emulator", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Sistem AI dimatikan. File dataset aman tersimpan.")