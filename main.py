import cv2
import mediapipe as mp
import pydirectinput
import time
import csv
import os
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFont

# Set CustomTkinter theme and mode
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SubwaySurfersAIApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window settings
        self.title("AI Subway Surfers Controller & Motion Tracker")
        self.width = 1020
        self.height = 560
        self.center_window(self.width, self.height)
        self.resizable(False, False)
        
        # Threading/State Variables
        self.lock = threading.Lock()
        self.is_running = False
        self.latest_frame = None
        self.current_position = "Center"
        self.status_sekarang = "Normal"
        
        self.nama_file_dataset = "dataset_koordinat_subway.csv"
        self.log_count = self.get_csv_rows(self.nama_file_dataset)
        self.persentase_merunduk = 0.53
        
        # Setup GUI Grid Layout (1 row, 2 columns: column 0 sidebar, column 1 camera view)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0) # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1) # Camera takes rest of space
        
        # Create Sidebar Frame
        self.sidebar_frame = ctk.CTkFrame(self, width=320, corner_radius=15, fg_color="#18191D")
        self.sidebar_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        
        # Create Camera View Frame
        self.camera_frame = ctk.CTkFrame(self, width=640, height=480, corner_radius=15, fg_color="#18191D")
        self.camera_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        
        self.setup_sidebar()
        self.setup_camera_view()
        
        # Handle Close Window
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def get_csv_rows(self, filename):
        if not os.path.exists(filename):
            return 0
        try:
            with open(filename, mode='r') as f:
                return sum(1 for line in f) - 1 # Exclude header
        except Exception:
            return 0

    def setup_sidebar(self):
        # 1. App Header
        self.title_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="SUBWAY SURFERS", 
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color="#3498db"
        )
        self.title_label.pack(pady=(25, 0), padx=20, anchor="w")
        
        self.subtitle_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="AI Motion Tracker Controller", 
            font=ctk.CTkFont(family="Inter", size=13),
            text_color="#8a8a8a"
        )
        self.subtitle_label.pack(pady=(2, 20), padx=20, anchor="w")
        
        # Horizontal Separator
        self.separator = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#2c2c2e")
        self.separator.pack(fill="x", padx=20, pady=(0, 20))
        
        # 2. Control Button
        self.btn_control = ctk.CTkButton(
            self.sidebar_frame, 
            text="MULAI AI TRACKER", 
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60",
            text_color="#ffffff",
            height=48,
            corner_radius=10,
            command=self.toggle_tracker
        )
        self.btn_control.pack(fill="x", padx=20, pady=(0, 20))
        
        # 3. Settings / Slider Frame
        self.settings_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#202126", corner_radius=10)
        self.settings_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.slider_title = ctk.CTkLabel(
            self.settings_frame, 
            text=f"Sensitivitas Merunduk: {self.persentase_merunduk:.2f}",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#e1e1e1"
        )
        self.slider_title.pack(pady=(12, 4), padx=15, anchor="w")
        
        self.slider_duck = ctk.CTkSlider(
            self.settings_frame,
            from_=0.3,
            to=0.7,
            number_of_steps=40,
            command=self.on_slider_move
        )
        self.slider_duck.set(self.persentase_merunduk)
        self.slider_duck.pack(fill="x", padx=15, pady=(0, 12))
        
        # 4. Status Panel Frame
        self.status_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#202126", corner_radius=10)
        self.status_frame.pack(fill="both", expand=True, padx=20, pady=(0, 25))
        
        self.status_header = ctk.CTkLabel(
            self.status_frame, 
            text="MONITOR STATUS", 
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color="#8a8a8a"
        )
        self.status_header.pack(pady=(12, 10), padx=15, anchor="w")
        
        # Status Items
        self.lbl_status = self.create_status_row(self.status_frame, "Status Pelacak:", "STANDBY")
        self.val_status = self.lbl_status[1]
        self.val_status.configure(text_color="gray")
        
        self.lbl_position = self.create_status_row(self.status_frame, "Posisi Sumbu:", "-")
        self.val_position = self.lbl_position[1]
        
        self.lbl_gesture = self.create_status_row(self.status_frame, "Gerakan Aktif:", "-")
        self.val_gesture = self.lbl_gesture[1]
        
        self.lbl_csv = self.create_status_row(self.status_frame, "Log CSV:", f"{self.log_count} baris")
        self.val_csv = self.lbl_csv[1]

    def create_status_row(self, parent, label_text, val_text):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=6)
        
        lbl = ctk.CTkLabel(
            row, 
            text=label_text, 
            font=ctk.CTkFont(family="Inter", size=13),
            text_color="#a8a8a8"
        )
        lbl.pack(side="left")
        
        val = ctk.CTkLabel(
            row, 
            text=val_text, 
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#ffffff"
        )
        val.pack(side="right")
        return lbl, val

    def setup_camera_view(self):
        # A container inside camera_frame to hold the actual label
        self.camera_label = tk.Label(self.camera_frame, bg="#111215")
        self.camera_label.pack(fill="both", expand=True, padx=2, pady=2)
        self.show_placeholder()

    def show_placeholder(self):
        placeholder = Image.new("RGB", (640, 480), color="#111215")
        draw = ImageDraw.Draw(placeholder)
        
        text1 = "Kamera Dinonaktifkan"
        text2 = "Klik tombol 'Mulai AI Tracker' untuk menjalankan pelacakan"
        
        # Simple cross camera design/icon using ImageDraw
        draw.ellipse((270, 160, 370, 260), outline="#2a2b30", width=4)
        draw.line((295, 210, 345, 210), fill="#2a2b30", width=6)
        draw.line((320, 185, 320, 235), fill="#2a2b30", width=6)
        
        try:
            font1 = ImageFont.truetype("arial.ttf", 22)
            font2 = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font1 = ImageFont.load_default()
            font2 = ImageFont.load_default()
            
        draw.text((320, 290), text1, fill="#ffffff", anchor="mm", font=font1)
        draw.text((320, 330), text2, fill="#7f8c8d", anchor="mm", font=font2)
        
        img_tk = ImageTk.PhotoImage(image=placeholder)
        self.camera_label.configure(image=img_tk)
        self.camera_label.image = img_tk

    def on_slider_move(self, val):
        self.persentase_merunduk = float(val)
        self.slider_title.configure(text=f"Sensitivitas Merunduk: {self.persentase_merunduk:.2f}")

    def toggle_tracker(self):
        if not self.is_running:
            # Check if previous thread is alive (just in case)
            if hasattr(self, 'thread') and self.thread.is_alive():
                return
            
            # Start
            self.is_running = True
            self.btn_control.configure(
                text="BERHENTI AI TRACKER", 
                fg_color="#e74c3c",
                hover_color="#c0392b"
            )
            
            # Start Thread
            self.thread = threading.Thread(target=self.worker_loop, daemon=True)
            self.thread.start()
            
            # Start GUI loop
            self.after(15, self.update_gui)
        else:
            # Stop
            self.is_running = False
            self.btn_control.configure(
                text="MULAI AI TRACKER", 
                fg_color="#2ecc71",
                hover_color="#27ae60"
            )
            # GUI will reset values automatically in update_gui when is_running is False

    def update_gui(self):
        if self.is_running:
            with self.lock:
                frame = self.latest_frame
                position = self.current_position
                status = self.status_sekarang
                logs = self.log_count
                
            if frame is not None:
                img = Image.fromarray(frame)
                img_tk = ImageTk.PhotoImage(image=img)
                self.camera_label.configure(image=img_tk)
                self.camera_label.image = img_tk
                
            self.val_status.configure(text="AKTIF", text_color="#2ecc71")
            self.val_position.configure(
                text=position, 
                text_color="#3498db" if position == "Center" else "#f1c40f"
            )
            
            # Dynamic colors for active gestures
            gesture_color = "#ffffff"
            if status == "Lompat":
                gesture_color = "#2ecc71"
            elif status == "Merunduk":
                gesture_color = "#e74c3c"
            elif status in ["Geser Kiri", "Geser Kanan"]:
                gesture_color = "#f39c12"
                
            self.val_gesture.configure(text=status, text_color=gesture_color)
            self.val_csv.configure(text=f"{logs} baris", text_color="#ffffff")
            
            self.after(15, self.update_gui)
        else:
            self.val_status.configure(text="STANDBY", text_color="gray")
            self.val_position.configure(text="-", text_color="gray")
            self.val_gesture.configure(text="-", text_color="gray")
            with self.lock:
                logs = self.log_count
            self.val_csv.configure(text=f"{logs} baris", text_color="gray")
            self.show_placeholder()

    def worker_loop(self):
        # Local Imports inside the thread to avoid issues
        from mediapipe.python.solutions import pose as mp_pose
        from mediapipe.python.solutions import drawing_utils as mp_drawing
        
        # Initialize Pose Model
        pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        # Open Camera (Attempt CAP_DSHOW first for Windows)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
            
        if not cap.isOpened():
            # Failed to open camera
            with self.lock:
                self.status_sekarang = "Kamera Error"
                self.current_position = "-"
            self.is_running = False
            # Show pop-up message (must run in main thread, but simple Tkinter messagebox is fine or we schedule it)
            self.after(100, lambda: messagebox.showerror("Koneksi Kamera Gagal", "Tidak dapat mendeteksi atau membuka webcam. Harap periksa koneksi kamera Anda."))
            return
            
        cooldown_time = 0.4
        last_action_time = time.time()
        current_position_local = "Center"
        
        # Ensure CSV exists
        if not os.path.exists(self.nama_file_dataset):
            with open(self.nama_file_dataset, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Timestamp', 'X_Hidung', 'Y_Bahu_Rata2', 'Posisi_Sumbu', 'Status_Gerakan'])

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                cap = cv2.VideoCapture(0)
                time.sleep(0.5)
                continue
                
            frame = cv2.flip(frame, 1)
            height, width, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb_frame)
            
            # Read current duck percentage from GUI setting
            current_persentase_merunduk = self.persentase_merunduk
            
            # 1. Gambar Garis Batas Kuning Vertikal (Kiri & Kanan)
            cv2.line(frame, (int(width * 0.35), 0), (int(width * 0.35), height), (0, 255, 255), 2)
            cv2.line(frame, (int(width * 0.65), 0), (int(width * 0.65), height), (0, 255, 255), 2)
        
            # 2. Gambar Garis Batas Ungu Horizontal (Merunduk)
            cv2.line(frame, (0, int(height * current_persentase_merunduk)), (width, int(height * current_persentase_merunduk)), (255, 0, 255), 2)
            cv2.putText(frame, "BATAS MERUNDUK", (10, int(height * current_persentase_merunduk) - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
                        
            status_sekarang_local = "Normal"
            
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
                    
                    # Gerakan 1: LOMPAT
                    if left_wrist_y < avg_shoulder_y or right_wrist_y < avg_shoulder_y:
                        try:
                            pydirectinput.keyDown('up')
                            time.sleep(0.05)  
                            pydirectinput.keyUp('up')
                        except Exception:
                            pass
                        cv2.putText(frame, "LOMPAT (PANAH ATAS)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                        status_sekarang_local = "Lompat"
                        last_action_time = current_time
        
                    # Gerakan 2: MERUNDUK
                    elif avg_shoulder_y > (height * current_persentase_merunduk): 
                        try:
                            pydirectinput.keyDown('down')
                            time.sleep(0.05)
                            pydirectinput.keyUp('down')
                        except Exception:
                            pass
                        cv2.putText(frame, "MERUNDUK (PANAH BAWAH)", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                        status_sekarang_local = "Merunduk"
                        last_action_time = current_time
        
                    # Gerakan 3: KIRI
                    elif nose_x < int(width * 0.35):
                        if current_position_local != "Left":
                            try:
                                pydirectinput.keyDown('left')
                                time.sleep(0.05)
                                pydirectinput.keyUp('left')
                            except Exception:
                                pass
                            current_position_local = "Left"
                            status_sekarang_local = "Geser Kiri"
                            last_action_time = current_time
                    
                    # Gerakan 4: KANAN
                    elif nose_x > int(width * 0.65):
                        if current_position_local != "Right":
                            try:
                                pydirectinput.keyDown('right')
                                time.sleep(0.05)
                                pydirectinput.keyUp('right')
                            except Exception:
                                pass
                            current_position_local = "Right"
                            status_sekarang_local = "Geser Kanan"
                            last_action_time = current_time
                    
                    else:
                        current_position_local = "Center"
                    
                    # JIKA ADA GERAKAN AKTIF, CATAT KE FILE DATASET CSV
                    if status_sekarang_local != "Normal":
                        waktu_log = time.strftime("%Y-%m-%d %H:%M:%S")
                        with open(self.nama_file_dataset, mode='a', newline='') as file:
                            writer = csv.writer(file)
                            writer.writerow([waktu_log, nose_x, avg_shoulder_y, current_position_local, status_sekarang_local])
                        with self.lock:
                            self.log_count += 1
            else:
                cv2.putText(frame, "PASTIKAN KAMERA MENYALA & MUNDUR SEBENTAR", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
            cv2.putText(frame, f"Posisi Tubuh: {current_position_local}", (50, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            # Convert OpenCV frame (BGR) to RGB for Tkinter compatibility
            rgb_display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            with self.lock:
                self.latest_frame = rgb_display_frame
                self.current_position = current_position_local
                self.status_sekarang = status_sekarang_local
                
        cap.release()

    def on_closing(self):
        # Stop thread loop
        self.is_running = False
        # Wait for thread to exit
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.destroy()

if __name__ == "__main__":
    app = SubwaySurfersAIApp()
    app.mainloop()