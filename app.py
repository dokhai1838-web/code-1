import os
import re
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageTk, ImageDraw
import imageio_ffmpeg
from font_support import register_fonts, available_fonts, subtitle_filter
import textwrap
import math

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def standardize_media(ffmpeg_exe, input_path, output_path, is_image, target_preset, zoom=100, x_off=0, y_off=0, use_gpu=True):
    vf = []
    w, h = 0, 0
    if "9:16" in target_preset:
        w, h = 1080, 1920
    elif "16:9" in target_preset:
        w, h = 1920, 1080
        
    if w > 0:
        z = zoom / 100.0
        scale_w = int(w * z)
        scale_h = int(h * z)
        px = 0.5 + (x_off / 100.0)
        py = 0.5 + (y_off / 100.0)
        
        vf.append(f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase")
        vf.append(f"crop={w}:{h}:(in_w-{w})*{px}:(in_h-{h})*{py}")
        
    cmd = [ffmpeg_exe, "-y"]
    if is_image:
        cmd.extend(["-loop", "1", "-framerate", "30", "-t", "4"])
    cmd.extend(["-i", input_path])
    if vf:
        cmd.extend(["-vf", ",".join(vf)])
    if use_gpu:
        cmd.extend(["-c:v", "h264_nvenc", "-preset", "p1", "-r", "30", "-pix_fmt", "yuv420p", "-an", output_path])
    else:
        cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-r", "30", "-pix_fmt", "yuv420p", "-an", output_path])
    
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(cmd, startupinfo=startupinfo, capture_output=True)

class AutoVideoApp(ctk.CTk):
    def __init__(self):
        register_fonts()
        super().__init__()
        
        self.title("Auto Video Tool - Live Preview & Batch Mode")
        self.geometry("1300x850") 
        
        self.ffmpeg_process = None
        self.last_output_dir = ""
        self.preview_image_raw = None
        self.preview_photo = None
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.is_running = False
        self.text_x = 0.5
        self.text_y = 0.8
        
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)
        
        self.frame_left = ctk.CTkFrame(self)
        self.frame_left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.frame_left.grid_columnconfigure(0, weight=1)
        self.frame_left.grid_rowconfigure(0, weight=1) 
        
        self.frame_right = ctk.CTkFrame(self, width=400)
        self.frame_right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.frame_right.grid_columnconfigure(0, weight=1)
        
        lbl_preview = ctk.CTkLabel(self.frame_right, text="MÀN HÌNH PREVIEW TĨNH", font=ctk.CTkFont(size=15, weight="bold"), text_color="#f1c40f")
        lbl_preview.grid(row=0, column=0, pady=15)
        
        self.canvas_w, self.canvas_h = 360, 640
        self.canvas = Canvas(self.frame_right, width=self.canvas_w, height=self.canvas_h, bg="#1a1a1a", highlightthickness=2, highlightbackground="#3498db")
        self.canvas.grid(row=1, column=0, pady=5)
        
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        
        lbl_hint_drag = ctk.CTkLabel(self.frame_right, text="🖱️ Mẹo: Kéo thả chuột vào màn hình đen ở trên\nđể Dịch chuyển khung hình (Pan) cực nhanh!\n\n🎬 Để xem có khớp nhạc hay không, hãy bấm XEM NHÁP", text_color="#bdc3c7", justify="center")
        lbl_hint_drag.grid(row=2, column=0, pady=15)
        
        self.tabview = ctk.CTkTabview(self.frame_left)
        self.tabview.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        self.tab_main = self.tabview.add("1. Dữ Liệu & Cài Đặt Chung")
        self.tab_zoom = self.tabview.add("2. Zoom & Cắt Cúp Khung Hình")
        self.tab_text = self.tabview.add("3. Tùy Chỉnh Chữ (Style)")
        
        self.setup_tab_main()
        self.setup_tab_zoom()
        self.setup_tab_text()
        self.setup_action_section()

    def setup_tab_main(self):
        lbl_input = ctk.CTkLabel(self.tab_main, text="NGUỒN DỮ LIỆU", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_input.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="w")
        
        self.frame_vid = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.frame_vid.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.frame_vid.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.frame_vid, text="Video / Ảnh nền:").grid(row=0, column=0, padx=5, sticky="w")
        self.ent_video = ctk.CTkEntry(self.frame_vid, placeholder_text="Có thể chọn nhiều file...")
        self.ent_video.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(self.frame_vid, text="Chọn Các File", width=110, command=self.browse_video).grid(row=0, column=2, padx=5)
        
        self.frame_voice = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.frame_voice.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.frame_voice.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.frame_voice, text="File Voice:").grid(row=0, column=0, padx=5, sticky="w")
        self.ent_voice = ctk.CTkEntry(self.frame_voice, placeholder_text="Chọn 1 file âm thanh")
        self.ent_voice.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(self.frame_voice, text="Chọn File", width=110, command=self.browse_voice).grid(row=0, column=2, padx=5)
        
        self.frame_txt_label = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.frame_txt_label.grid(row=3, column=0, padx=10, pady=(5, 0), sticky="ew")
        ctk.CTkLabel(self.frame_txt_label, text="Nội Dung Text Hiển Thị:").pack(side="left", padx=5)
        
        self.show_text_var = ctk.BooleanVar(value=True)
        self.chk_show_text = ctk.CTkCheckBox(self.frame_txt_label, text="Hiển thị", variable=self.show_text_var, width=60, command=self.update_preview)
        self.chk_show_text.pack(side="left", padx=10)
        
        ctk.CTkButton(self.frame_txt_label, text="Tải từ file .txt", width=110, height=24, command=self.load_text_file).pack(side="right", padx=5)
        self.combo_text_line = ctk.CTkComboBox(self.frame_txt_label, width=200, values=["Nhập thủ công"], command=self.on_select_text_line)
        self.combo_text_line.pack(side="right", padx=10)
        
        self.txt_content = ctk.CTkTextbox(self.tab_main, height=70)
        self.txt_content.grid(row=4, column=0, padx=15, pady=5, sticky="ew")
        self.txt_content.bind("<KeyRelease>", self.update_preview)
        
        lbl_settings = ctk.CTkLabel(self.tab_main, text="CÀI ĐẶT ĐẦU RA", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_settings.grid(row=5, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.frame_settings = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.frame_settings.grid(row=6, column=0, padx=10, pady=0, sticky="ew")
        self.frame_settings.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.frame_settings, text="Preset/Tỷ lệ:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.preset_var = ctk.StringVar(value="Facebook/Reels (9:16) - Fill Center")
        self.combo_preset = ctk.CTkComboBox(self.frame_settings, width=250, values=["Facebook/Reels (9:16) - Fill Center", "YouTube (16:9)", "Giữ Nguyên Nguồn"], variable=self.preset_var, command=self.update_preview)
        self.combo_preset.grid(row=0, column=1, padx=5, sticky="w")
        
        ctk.CTkLabel(self.frame_settings, text="Chế độ xử lý:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.batch_mode_var = ctk.StringVar(value="⚡ AUTO MATCHING (Khớp theo tiền tố 1, 2, 3...)")
        self.combo_batch = ctk.CTkComboBox(self.frame_settings, width=320, values=[
            "⚡ AUTO MATCHING (Khớp theo tiền tố 1, 2, 3...)", 
            "🔄 Cuốn chiếu Tuần tự (Video 1+Voice 1, Video 2+Voice 2)",
            "Gộp Tất Cả Các File Nền thành 1 Video", 
            "Làm Hàng Loạt (Cùng Text/Voice cho Mọi Nền)"
        ], variable=self.batch_mode_var)
        self.combo_batch.grid(row=1, column=1, padx=5, sticky="w")
        
        ctk.CTkLabel(self.frame_settings, text="Cuốn chiếu:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.loop_var = ctk.BooleanVar(value=True)
        self.chk_loop = ctk.CTkCheckBox(self.frame_settings, text="Lặp đi lặp lại video nền để che kín Voice", variable=self.loop_var)
        self.chk_loop.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(self.frame_settings, text="Tốc độ nền:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.speed_var = ctk.StringVar(value="1.0x (Bình thường)")
        self.combo_speed = ctk.CTkComboBox(self.frame_settings, width=200, values=["0.5x (Rất chậm)", "0.75x (Chậm)", "1.0x (Bình thường)", "1.25x (Nhanh)", "1.5x (Nhanh hơn)", "2.0x (Rất nhanh)"], variable=self.speed_var)
        self.combo_speed.grid(row=3, column=1, padx=5, pady=2, sticky="w")
        
        self.gpu_var = ctk.BooleanVar(value=True)
        self.chk_gpu = ctk.CTkCheckBox(self.frame_settings, text="🚀 Tăng tốc bằng GPU (NVIDIA NVENC)", variable=self.gpu_var)
        self.chk_gpu.grid(row=3, column=2, padx=5, pady=2, sticky="w")
        
        ctk.CTkLabel(self.frame_settings, text="Thư mục xuất:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.ent_output = ctk.CTkEntry(self.frame_settings, placeholder_text="Chọn thư mục chứa video kết quả...")
        self.ent_output.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.frame_settings, text="Chọn Folder", width=110, command=self.browse_out_dir).grid(row=4, column=2, padx=5, pady=5)

    def setup_tab_zoom(self):
        lbl_title = ctk.CTkLabel(self.tab_zoom, text="ĐIỀU CHỈNH KHUNG HÌNH", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_title.grid(row=0, column=0, padx=10, pady=(15, 10), sticky="w")
        
        frame = ctk.CTkFrame(self.tab_zoom, fg_color="transparent")
        frame.grid(row=1, column=0, padx=20, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)
        
        self.lbl_zoom_val = ctk.CTkLabel(frame, text="Phóng to (Zoom): 100%", width=150, anchor="w")
        self.lbl_zoom_val.grid(row=0, column=0, padx=10, pady=15, sticky="w")
        self.zoom_var = ctk.DoubleVar(value=100)
        self.slider_zoom = ctk.CTkSlider(frame, from_=100, to=200, variable=self.zoom_var, command=self.on_zoom_change)
        self.slider_zoom.grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        
        self.lbl_x_val = ctk.CTkLabel(frame, text="Dịch Trái/Phải (X): 0", width=150, anchor="w")
        self.lbl_x_val.grid(row=1, column=0, padx=10, pady=15, sticky="w")
        self.x_var = ctk.DoubleVar(value=0)
        self.slider_x = ctk.CTkSlider(frame, from_=-50, to=50, variable=self.x_var, command=self.on_xy_change)
        self.slider_x.grid(row=1, column=1, padx=10, pady=15, sticky="ew")
        
        self.lbl_y_val = ctk.CTkLabel(frame, text="Dịch Lên/Xuống (Y): 0", width=150, anchor="w")
        self.lbl_y_val.grid(row=2, column=0, padx=10, pady=15, sticky="w")
        self.y_var = ctk.DoubleVar(value=0)
        self.slider_y = ctk.CTkSlider(frame, from_=-50, to=50, variable=self.y_var, command=self.on_xy_change)
        self.slider_y.grid(row=2, column=1, padx=10, pady=15, sticky="ew")

    def setup_tab_text(self):
        lbl_title = ctk.CTkLabel(self.tab_text, text="TÙY CHỈNH PHÔNG CHỮ & HIỂN THỊ", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_title.grid(row=0, column=0, padx=10, pady=(15, 10), sticky="w")
        
        self.scroll_text = ctk.CTkScrollableFrame(self.tab_text, fg_color="transparent")
        self.scroll_text.grid(row=1, column=0, padx=10, sticky="nsew")
        self.tab_text.grid_rowconfigure(1, weight=1)
        self.tab_text.grid_columnconfigure(0, weight=1)
        
        frame = self.scroll_text
        
        # 1. Phông chữ
        ctk.CTkLabel(frame, text="Phông chữ (Font):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.font_choices = available_fonts(self)
        self.font_var = ctk.StringVar(value="Be Vietnam Pro" if "Be Vietnam Pro" in self.font_choices else self.font_choices[0])
        self.font_combo = ctk.CTkComboBox(frame, width=250, values=self.font_choices,
                                        variable=self.font_var, state="readonly", command=self.update_preview)
        self.font_combo.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # 2. Cỡ chữ
        self.lbl_size_val = ctk.CTkLabel(frame, text="Cỡ chữ: 22")
        self.lbl_size_val.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.size_var = ctk.DoubleVar(value=22)
        self.slider_size = ctk.CTkSlider(frame, from_=10, to=100, variable=self.size_var, command=self.on_size_change)
        self.slider_size.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # 3. Vị trí
        ctk.CTkLabel(frame, text="Vị trí (Di chuột):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(frame, text="👆 KÉO THẢ chữ trên màn hình đen bên phải!", text_color="#2ecc71", font=ctk.CTkFont(weight="bold")).grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # 4. Phông nền Toggle
        ctk.CTkLabel(frame, text="Phông nền:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.bg_enable_var = ctk.BooleanVar(value=True)
        self.chk_bg = ctk.CTkCheckBox(frame, text="Bật phông nền", variable=self.bg_enable_var, command=self.toggle_bg_settings)
        self.chk_bg.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        # 5. Màu nền
        self.lbl_bg_color = ctk.CTkLabel(frame, text="Màu nền (Mã HEX):")
        self.lbl_bg_color.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.bg_color_var = ctk.StringVar(value="000000") # Mặc định đen
        self.ent_bg_color = ctk.CTkEntry(frame, textvariable=self.bg_color_var, width=100)
        self.ent_bg_color.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.ent_bg_color.bind("<KeyRelease>", self.update_preview)
        
        # 6. Độ mờ nền
        self.lbl_bg_opacity = ctk.CTkLabel(frame, text="Độ mờ (Opacity): 60%")
        self.lbl_bg_opacity.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.bg_opacity_var = ctk.DoubleVar(value=60)
        self.slider_bg_opacity = ctk.CTkSlider(frame, from_=0, to=100, variable=self.bg_opacity_var, command=self.on_opacity_change)
        self.slider_bg_opacity.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        
        # 7. Chiều rộng nền (Padding X)
        self.lbl_bg_width = ctk.CTkLabel(frame, text="Chiều rộng nền: 10")
        self.lbl_bg_width.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.bg_width_var = ctk.DoubleVar(value=10)
        self.slider_bg_width = ctk.CTkSlider(frame, from_=0, to=50, variable=self.bg_width_var, command=self.on_bg_padding_change)
        self.slider_bg_width.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # 8. Chiều cao nền (Padding Y)
        self.lbl_bg_height = ctk.CTkLabel(frame, text="Chiều cao nền: 10")
        self.lbl_bg_height.grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.bg_height_var = ctk.DoubleVar(value=10)
        self.slider_bg_height = ctk.CTkSlider(frame, from_=0, to=50, variable=self.bg_height_var, command=self.on_bg_padding_change)
        self.slider_bg_height.grid(row=7, column=1, padx=10, pady=5, sticky="ew")

        # 9. Bo góc nền (Radius)
        self.lbl_bg_radius = ctk.CTkLabel(frame, text="Bo góc nền: 15")
        self.lbl_bg_radius.grid(row=8, column=0, padx=10, pady=5, sticky="w")
        self.bg_radius_var = ctk.DoubleVar(value=15)
        self.slider_bg_radius = ctk.CTkSlider(frame, from_=0, to=100, variable=self.bg_radius_var, command=self.on_bg_padding_change)
        self.slider_bg_radius.grid(row=8, column=1, padx=10, pady=5, sticky="ew")

        self.font_sample = ctk.CTkLabel(frame, text="Tiếng Việt: Đậm nét • Cảm xúc • Sáng tạo",
                                       font=(self.font_var.get(), 22, "bold"), wraplength=390)
        self.font_sample.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.font_var.trace_add("write", self.on_font_change)
        ctk.CTkLabel(frame, text="Font kèm sẵn: Be Vietnam Pro, Kanit, Anton,\nLobster, Pacifico, Pattaya. Các font khác lấy từ máy.",
                     text_color="gray", justify="left").grid(row=10, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    def on_font_change(self, *args):
        self.font_sample.configure(font=(self.font_var.get(), 22, "bold"))
        self.update_preview()

    def setup_action_section(self):
        self.frame_action = ctk.CTkFrame(self.frame_left, fg_color="transparent")
        self.frame_action.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.frame_action.grid_columnconfigure(0, weight=1)
        self.frame_action.grid_columnconfigure(1, weight=1)
        self.frame_action.grid_columnconfigure(2, weight=1)
        self.frame_action.grid_columnconfigure(3, weight=1)
        
        self.btn_preview = ctk.CTkButton(self.frame_action, text="🎬 XEM NHÁP", font=ctk.CTkFont(size=14, weight="bold"), height=40, fg_color="#f39c12", hover_color="#d35400", command=self.start_preview)
        self.btn_preview.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.btn_run = ctk.CTkButton(self.frame_action, text="▶ TẠO VIDEO XỊN", font=ctk.CTkFont(size=14, weight="bold"), height=40, fg_color="#2ecc71", hover_color="#27ae60", command=self.start_process)
        self.btn_run.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.btn_cancel = ctk.CTkButton(self.frame_action, text="■ HỦY", font=ctk.CTkFont(size=14, weight="bold"), height=40, fg_color="#e74c3c", hover_color="#c0392b", state="disabled", command=self.cancel_process)
        self.btn_cancel.grid(row=0, column=2, padx=5, sticky="ew")
        
        self.btn_open_folder = ctk.CTkButton(self.frame_action, text="Mở Thư Mục Kết Quả", font=ctk.CTkFont(size=14, weight="bold"), height=40, fg_color="#3498db", hover_color="#2980b9", state="disabled", command=self.open_output_folder)
        self.btn_open_folder.grid(row=0, column=3, padx=5, sticky="ew")
        
        self.progressbar = ctk.CTkProgressBar(self.frame_left)
        self.progressbar.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.progressbar.set(0)
        
        self.lbl_status = ctk.CTkLabel(self.frame_left, text="Trạng thái: Đang chờ...", font=ctk.CTkFont(size=12, slant="italic"))
        self.lbl_status.grid(row=3, column=0, padx=15, sticky="w")
        
        self.log_box = ctk.CTkTextbox(self.frame_left, height=100, state="disabled", font=("Consolas", 12))
        self.log_box.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

    # --- UI EVENT HANDLERS ---
    def on_zoom_change(self, v):
        self.lbl_zoom_val.configure(text=f"Phóng to (Zoom): {int(v)}%")
        self.update_preview()
        
    def on_xy_change(self, v):
        self.lbl_x_val.configure(text=f"Dịch Trái/Phải (X): {int(self.x_var.get())}")
        self.lbl_y_val.configure(text=f"Dịch Lên/Xuống (Y): {int(self.y_var.get())}")
        self.update_preview()

    def on_size_change(self, v):
        self.lbl_size_val.configure(text=f"Cỡ chữ: {int(v)}")
        self.update_preview()
        
    def on_opacity_change(self, v):
        self.lbl_bg_opacity.configure(text=f"Độ mờ (Opacity): {int(v)}%")
        self.update_preview()
        
    def on_bg_padding_change(self, v):
        self.lbl_bg_width.configure(text=f"Chiều rộng nền: {int(self.bg_width_var.get())}")
        self.lbl_bg_height.configure(text=f"Chiều cao nền: {int(self.bg_height_var.get())}")
        self.lbl_bg_radius.configure(text=f"Bo góc nền: {int(self.bg_radius_var.get())}")
        self.update_preview()

    def toggle_bg_settings(self):
        state = "normal" if self.bg_enable_var.get() else "disabled"
        self.slider_bg_opacity.configure(state=state)
        self.ent_bg_color.configure(state=state)
        self.slider_bg_width.configure(state=state)
        self.slider_bg_height.configure(state=state)
        self.slider_bg_radius.configure(state=state)
        self.update_preview()
        
    def get_ass_rounded_rect(self, w, h, r):
        if r <= 0:
            return f"{{\\p1}}m 0 0 l {w} 0 l {w} {h} l 0 {h}{{\\p0}}"
        r = min(r, w//2, h//2)
        c = int(0.55228 * r)
        return f"{{\\p1}}m {r} 0 l {w-r} 0 b {w-r+c} 0 {w} {r-c} {w} {r} l {w} {h-r} b {w} {h-r+c} {w-r+c} {h} {w-r} {h} l {r} {h} b {r-c} {h} 0 {h-r+c} 0 {h-r} l 0 {r} b 0 {r-c} {r-c} 0 {r} 0{{\\p0}}"
        
    def get_wrapped_text(self, txt, preset, font_size):
        if "9:16" in preset: w, h_ref = 1080, 1920
        elif "16:9" in preset: w, h_ref = 1920, 1080
        else: w, h_ref = 1080, 1080
        
        canvas_h_ref = 640 if "9:16" in preset else 360
        if "9:16" not in preset and "16:9" not in preset: canvas_h_ref = 480
        
        real_font_size = int(font_size * (h_ref / canvas_h_ref))
        
        if not hasattr(self, 'wrap_width_ratio'):
            self.wrap_width_ratio = (w - 150) / w
            
        wrap_pixel_width = self.wrap_width_ratio * w
        chars_per_line = max(5, int(wrap_pixel_width / (real_font_size * 0.55)))
        
        final_lines = []
        for line in txt.split('\n'):
            if line.strip():
                wrapped = textwrap.wrap(line, width=chars_per_line)
                final_lines.extend(wrapped)
        return "\n".join(final_lines), real_font_size

    def on_drag_start(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["item"] = "video"
        
        # Kiểm tra xem người dùng click vào Text hay Video
        items = self.canvas.find_withtag("current")
        for item in items:
            tags = self.canvas.gettags(item)
            if "text_resize_handle" in tags:
                self.drag_data["item"] = "text_resize"
                self.drag_data["start_size"] = self.size_var.get()
                cx = self.text_x * self.canvas_w
                cy = self.text_y * self.canvas_h
                dist = math.hypot(event.x - cx, event.y - cy)
                self.drag_data["start_dist"] = max(1, dist)
                break
            elif "text_wrap_handle" in tags:
                self.drag_data["item"] = "text_wrap"
                cx = self.text_x * self.canvas_w
                self.drag_data["start_wrap_ratio"] = getattr(self, 'wrap_width_ratio', 0.8)
                self.drag_data["start_dist_x"] = max(1, abs(event.x - cx))
                break
            elif "text_front" in tags or "text_bg" in tags or "text_shadow" in tags or "text_border" in tags:
                self.drag_data["item"] = "text"
                break

    def on_drag_motion(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        
        if self.drag_data.get("item") == "text_resize":
            cx = self.text_x * self.canvas_w
            cy = self.text_y * self.canvas_h
            current_dist = math.hypot(event.x - cx, event.y - cy)
            
            ratio = current_dist / self.drag_data["start_dist"]
            new_size = self.drag_data["start_size"] * ratio
            new_size = max(10, min(200, new_size))
            
            self.size_var.set(new_size)
            self.on_size_change(new_size)
        elif self.drag_data.get("item") == "text_wrap":
            cx = self.text_x * self.canvas_w
            current_dist_x = abs(event.x - cx)
            
            new_wrap_ratio = (current_dist_x * 2) / self.canvas_w
            new_wrap_ratio = max(0.1, min(2.0, new_wrap_ratio))
            
            self.wrap_width_ratio = new_wrap_ratio
            self.update_preview()
        elif self.drag_data.get("item") == "text":
            # Di chuyển Text
            tx = self.text_x * self.canvas_w + dx
            ty = self.text_y * self.canvas_h + dy
            
            tx = max(0, min(self.canvas_w, tx))
            ty = max(0, min(self.canvas_h, ty))
            
            self.text_x = tx / self.canvas_w
            self.text_y = ty / self.canvas_h
            
            self.update_preview()
        else:
            # Di chuyển Video nền
            new_x = self.x_var.get() - (dx * 0.4)
            new_y = self.y_var.get() - (dy * 0.4)
            
            new_x = max(-50, min(50, new_x))
            new_y = max(-50, min(50, new_y))
            
            self.x_var.set(new_x)
            self.y_var.set(new_y)
            self.on_xy_change(0)

    def extract_preview_frame(self, filepath):
        def task():
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            out_img = "temp_preview_frame.jpg"
            if os.path.exists(out_img): os.remove(out_img)
            
            cmd = [ffmpeg_exe, "-y", "-i", filepath, "-vframes", "1", "-q:v", "2", out_img]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, startupinfo=startupinfo, capture_output=True)
            
            if os.path.exists(out_img):
                try:
                    self.preview_image_raw = Image.open(out_img).copy()
                    self.after(0, self.update_preview)
                except:
                    pass
        threading.Thread(target=task, daemon=True).start()

    def update_preview(self, *args):
        self.canvas.delete("all")
        preset = self.preset_var.get()
        
        if "9:16" in preset: self.canvas_w, self.canvas_h = 360, 640
        elif "16:9" in preset: self.canvas_w, self.canvas_h = 640, 360
        else: self.canvas_w, self.canvas_h = 480, 480
            
        self.canvas.configure(width=self.canvas_w, height=self.canvas_h)
        
        if self.preview_image_raw:
            img_w, img_h = self.preview_image_raw.size
            ratio_w = self.canvas_w / img_w
            ratio_h = self.canvas_h / img_h
            base_ratio = max(ratio_w, ratio_h)
            
            zoom = self.zoom_var.get() / 100.0
            final_ratio = base_ratio * zoom
            
            new_w = int(img_w * final_ratio)
            new_h = int(img_h * final_ratio)
            
            scaled_img = self.preview_image_raw.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            x_off = self.x_var.get() 
            y_off = self.y_var.get() 
            
            max_shift_x = max(0, (new_w - self.canvas_w) / 2)
            max_shift_y = max(0, (new_h - self.canvas_h) / 2)
            
            shift_x = -(x_off / 50.0) * max_shift_x
            shift_y = -(y_off / 50.0) * max_shift_y
            
            cx = self.canvas_w / 2 + shift_x
            cy = self.canvas_h / 2 + shift_y
            
            self.preview_photo = ImageTk.PhotoImage(scaled_img)
            self.canvas.create_image(cx, cy, image=self.preview_photo, tags="video")
            
        txt = self.txt_content.get("1.0", "end-1c").strip()
        if txt and self.show_text_var.get():
            font_name = self.font_var.get()
            font_size = int(self.size_var.get())
            
            wrapped_txt, _ = self.get_wrapped_text(txt, preset, font_size)
            
            tx = self.text_x * self.canvas_w
            ty = self.text_y * self.canvas_h
                
            bg_enabled = self.bg_enable_var.get()
            pad_x = int(self.bg_width_var.get())
            pad_y = int(self.bg_height_var.get())
            
            # Vẽ thử text ẩn để lấy bounding box
            t_id = self.canvas.create_text(tx, ty, text=wrapped_txt, font=(font_name, -font_size, "bold"), justify="center", width=9999)
            bbox = self.canvas.bbox(t_id)
            self.canvas.delete(t_id)
            
            if bbox:
                text_pixel_w = bbox[2] - bbox[0]
                text_pixel_h = bbox[3] - bbox[1]
                # Lưu tỷ lệ chiều rộng/cao thực tế của text so với canvas
                self.text_w_ratio = text_pixel_w / self.canvas_w
                self.text_h_ratio = text_pixel_h / self.canvas_h
                
                x1, y1, x2, y2 = bbox[0]-pad_x, bbox[1]-pad_y, bbox[2]+pad_x, bbox[3]+pad_y
                if bg_enabled:
                    bg_hex = self.bg_color_var.get().strip().lstrip('#')
                    if len(bg_hex) != 6: bg_hex = "000000"
                    
                    bg_w_px = max(1, int(x2 - x1))
                    bg_h_px = max(1, int(y2 - y1))
                    r_val = int(self.bg_radius_var.get())
                    
                    # Tạo ảnh PIL với kênh Alpha
                    img = Image.new("RGBA", (bg_w_px, bg_h_px), (0,0,0,0))
                    draw = ImageDraw.Draw(img)
                    
                    r_col = int(bg_hex[0:2], 16)
                    g_col = int(bg_hex[2:4], 16)
                    b_col = int(bg_hex[4:6], 16)
                    alpha = int((self.bg_opacity_var.get() / 100) * 255)
                    
                    draw.rounded_rectangle((0, 0, bg_w_px-1, bg_h_px-1), radius=r_val, fill=(r_col, g_col, b_col, alpha))
                    
                    self.box_photo = ImageTk.PhotoImage(img)
                    self.canvas.create_image(x1 + bg_w_px/2, y1 + bg_h_px/2, image=self.box_photo, tags="text_bg")
                
                # Khung viền đứt nét để dễ căn chỉnh & Handle kéo thả (Resize)
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="white", dash=(4, 4), tags="text_border")
                r = 8
                self.canvas.create_oval(x2-r, y2-r, x2+r, y2+r, fill="white", outline="#3498db", width=2, tags="text_resize_handle")
                self.canvas.create_line(x2-4, y2-4, x2+4, y2+4, fill="#3498db", width=2, tags="text_resize_handle")
                self.canvas.create_line(x2-4, y2+4, x2+4, y2-4, fill="#3498db", width=2, tags="text_resize_handle")
                
                # Nút điều chỉnh chiều rộng chữ (Wrap Handle)
                hy = (y1 + y2) / 2
                self.canvas.create_rectangle(x2-3, hy-8, x2+3, hy+8, fill="white", outline="#3498db", width=2, tags="text_wrap_handle")
                self.canvas.create_rectangle(x1-3, hy-8, x1+3, hy+8, fill="white", outline="#3498db", width=2, tags="text_wrap_handle")
            
            self.canvas.create_text(tx+2, ty+2, text=wrapped_txt, font=(font_name, -font_size, "bold"), fill="black", justify="center", width=9999, tags="text_shadow")
            self.canvas.create_text(tx, ty, text=wrapped_txt, font=(font_name, -font_size, "bold"), fill="white", justify="center", width=9999, tags="text_front")

    # --- GENERAL LOGIC ---
    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"> {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.lbl_status.configure(text=text)

    def browse_video(self):
        files = filedialog.askopenfilenames(title="Chọn Video hoặc Ảnh nền", filetypes=[("Media files", "*.mp4 *.mov *.avi *.mkv *.jpg *.jpeg *.png *.webp")])
        if files: 
            self.ent_video.delete(0, 'end')
            self.ent_video.insert(0, ";".join(files))
            self.extract_preview_frame(files[0])
            
    def browse_voice(self):
        files = filedialog.askopenfilenames(title="Chọn File Voice (Có thể chọn nhiều)", filetypes=[("Audio files", "*.mp3 *.wav *.m4a *.aac")])
        if files: 
            self.ent_voice.delete(0, 'end')
            self.ent_voice.insert(0, ";".join(files))
            
    def browse_out_dir(self):
        d = filedialog.askdirectory()
        if d: self.ent_output.delete(0, 'end'); self.ent_output.insert(0, d)
        
    def load_text_file(self):
        f = filedialog.askopenfilename(title="Chọn file Text", filetypes=[("Text files", "*.txt")])
        if f:
            try:
                with open(f, 'r', encoding='utf-8') as file: content = file.read()
                
                # Split content into lines and ignore empty lines
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                if not lines:
                    messagebox.showerror("Lỗi", "File text trống!")
                    return
                
                self.loaded_texts = lines
                
                # Build dropdown options
                dropdown_values = []
                for i, line in enumerate(lines):
                    preview = line[:25] + "..." if len(line) > 25 else line
                    dropdown_values.append(f"Dòng {i+1}: {preview}")
                
                self.combo_text_line.configure(values=dropdown_values)
                self.combo_text_line.set(dropdown_values[0])
                self.on_select_text_line(dropdown_values[0])
                
                self.log(f"Đã tải {len(lines)} câu text. Hãy chọn câu muốn dùng ở mục thả xuống!")
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))

    def on_select_text_line(self, selected_val):
        if not hasattr(self, 'loaded_texts'): return
        try:
            match = re.match(r"Dòng (\d+):", selected_val)
            if match:
                idx = int(match.group(1)) - 1
                raw_text = self.loaded_texts[idx]
                
                # Tự động xóa các tiền tố như "1|", "2|" ở đầu dòng
                clean_text = re.sub(r'^\d+\|', '', raw_text).strip()
                
                self.txt_content.delete("1.0", "end")
                self.txt_content.insert("1.0", clean_text)
                self.update_preview()
        except:
            pass

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            os.startfile(self.last_output_dir)

    def cancel_process(self):
        self.is_running = False
        if self.ffmpeg_process:
            self.log("🛑 Đang dừng FFmpeg...")
            self.ffmpeg_process.terminate()

    def get_duration(self, file_path):
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ffmpeg_exe, "-i", file_path]
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(cmd, startupinfo=startupinfo, capture_output=True, text=True)
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", result.stderr)
        if match:
            h, m, s = match.groups()
            return float(h) * 3600 + float(m) * 60 + float(s)
        return 0.0

    def start_preview(self):
        self.run_pipeline_thread(is_draft=True)
        
    def start_process(self):
        self.run_pipeline_thread(is_draft=False)
        
    def run_pipeline_thread(self, is_draft=False):
        vid_string = self.ent_video.get()
        voc = self.ent_voice.get()
        out_dir = self.ent_output.get()
        txt = self.txt_content.get("1.0", "end-1c").strip()
        preset = self.preset_var.get()
        batch_mode = self.batch_mode_var.get()
        
        zoom_val = int(self.zoom_var.get())
        x_val = int(self.x_var.get())
        y_val = int(self.y_var.get())
        
        if not all([vid_string, voc, out_dir]):
            messagebox.showerror("Lỗi", "Vui lòng điền đủ các trường: Video, Voice, và Thư mục xuất!")
            return
            
        if self.show_text_var.get() and not txt:
            messagebox.showerror("Lỗi", "Vui lòng nhập Text hoặc tắt nút 'Hiển thị'!")
            return
            
        vid_list = [v.strip() for v in vid_string.split(";") if v.strip()]
        for v in vid_list:
            if not os.path.exists(v): return messagebox.showerror("Lỗi", f"Không tìm thấy file:\n{v}")
        if not os.path.exists(voc): return messagebox.showerror("Lỗi", "Không tìm thấy file Voice!")
            
        self.last_output_dir = out_dir
        self.btn_run.configure(state="disabled")
        self.btn_preview.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.btn_open_folder.configure(state="disabled")
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.is_running = True
        
        def task():
            try:
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                
                if is_draft:
                    self.log("[XEM NHÁP] Đang tạo video nháp siêu tốc (chất lượng thấp)...")
                    draft_file = os.path.join(out_dir, "draft_preview.mp4")
                    voc_first = voc.split(";")[0].strip()
                    self.render_single_unit(ffmpeg_exe, [vid_list[0]], voc_first, txt, preset, zoom_val, x_val, y_val, draft_file, True)
                    
                    if self.is_running and os.path.exists(draft_file):
                        self.log("✅ Đã tạo Nháp xong! Đang mở Video...")
                        os.startfile(draft_file)
                else:
                    if "AUTO MATCHING" in batch_mode:
                        self.log("[AUTO MATCHING] Phân tích nhóm theo tiền tố (1.1, 1.mp3, 1|...)")
                        voc_list = [v.strip() for v in voc.split(";") if v.strip()]
                        
                        group_vids = {}
                        for v in vid_list:
                            base = os.path.basename(v)
                            match = re.match(r"^(\d+)", base)
                            if match:
                                g = match.group(1)
                                if g not in group_vids: group_vids[g] = []
                                group_vids[g].append(v)
                                
                        group_vocs = {}
                        for v in voc_list:
                            base = os.path.basename(v)
                            match = re.match(r"^(\d+)", base)
                            if match: group_vocs[match.group(1)] = v
                            
                        group_txts = {}
                        if hasattr(self, 'loaded_texts'):
                            for line in self.loaded_texts:
                                match = re.match(r"^(\d+)\|", line)
                                if match:
                                    clean = re.sub(r'^\d+\|', '', line).strip()
                                    group_txts[match.group(1)] = clean
                                    
                        # Sắp xếp các video trong mỗi nhóm (để 1.1 render trước 1.2)
                        for g in group_vids:
                            group_vids[g].sort()
                            
                        # Tìm các nhóm hợp lệ (có đủ ít nhất Vid + Voice)
                        common_keys = sorted(list(group_vids.keys()), key=lambda x: int(x))
                        
                        self.log(f"-> Tìm thấy {len(common_keys)} nhóm hợp lệ để Render!")
                        for idx, g in enumerate(common_keys):
                            if not self.is_running: break
                            vids = group_vids[g]
                            voice = group_vocs.get(g, voc_list[0]) # Fallback nếu ko có
                            text = group_txts.get(g, txt)          # Fallback nếu ko có
                            
                            self.log(f"\n--- Đang xử lý Nhóm {g} ({idx+1}/{len(common_keys)}) - Có {len(vids)} biến thể ---")
                            
                            for v in vids:
                                if not self.is_running: break
                                base_name = os.path.splitext(os.path.basename(v))[0]
                                out_file = os.path.join(out_dir, f"{base_name}.mp4")
                                
                                self.log(f" -> Tạo biến thể: {base_name}.mp4")
                                self.render_single_unit(ffmpeg_exe, [v], voice, text, preset, zoom_val, x_val, y_val, out_file, False)
                            
                    elif "Cuốn chiếu Tuần tự" in batch_mode and len(vid_list) > 0:
                        self.log(f"[TUẦN TỰ] Render {len(vid_list)} cặp tuần tự.")
                        voc_list = [v.strip() for v in voc.split(";") if v.strip()]
                        
                        txt_list = []
                        if hasattr(self, 'loaded_texts'):
                            txt_list = [re.sub(r'^\d+\|', '', line).strip() for line in self.loaded_texts if line.strip()]
                        if not txt_list:
                            txt_list = [txt]
                            
                        for i, v in enumerate(vid_list):
                            if not self.is_running: break
                            
                            voice = voc_list[i] if i < len(voc_list) else voc_list[-1]
                            text = txt_list[i] if i < len(txt_list) else txt_list[-1]
                            
                            self.log(f"\n--- Đang xử lý Video {i+1}/{len(vid_list)} ---")
                            
                            base_name = os.path.splitext(os.path.basename(v))[0]
                            out_file = os.path.join(out_dir, f"{base_name}.mp4")
                            
                            self.render_single_unit(ffmpeg_exe, [v], voice, text, preset, zoom_val, x_val, y_val, out_file, False)

                    elif "Làm Hàng Loạt" in batch_mode and len(vid_list) > 0:
                        self.log(f"[HÀNG LOẠT] Render {len(vid_list)} video độc lập.")
                        voc_first = voc.split(";")[0].strip()
                        for i, v in enumerate(vid_list):
                            if not self.is_running: break
                            self.log(f"\n--- Đang xử lý Video {i+1}/{len(vid_list)} ---")
                            
                            base_name = os.path.splitext(os.path.basename(v))[0]
                            out_file = os.path.join(out_dir, f"{base_name}.mp4")
                            
                            self.render_single_unit(ffmpeg_exe, [v], voc_first, txt, preset, zoom_val, x_val, y_val, out_file, False)
                    else:
                        self.log(f"[GỘP VIDEO] Nối {len(vid_list)} file thành 1 video duy nhất.")
                        voc_first = voc.split(";")[0].strip()
                        
                        base_name = os.path.splitext(os.path.basename(vid_list[0]))[0]
                        out_file = os.path.join(out_dir, f"{base_name}_merged.mp4")
                        
                        self.render_single_unit(ffmpeg_exe, vid_list, voc_first, txt, preset, zoom_val, x_val, y_val, out_file, False)
                
                self.progressbar.stop()
                self.progressbar.configure(mode="determinate")
                
                if self.is_running:
                    self.progressbar.set(1)
                    self.log("✅ HOÀN TẤT QUÁ TRÌNH RENDER!")
                    self.btn_open_folder.configure(state="normal")
                    if not is_draft:
                        messagebox.showinfo("Thành công", "Render hoàn tất!\nVui lòng bấm 'Mở Thư Mục Kết Quả'")
                    
            except Exception as e:
                self.progressbar.stop()
                self.log(f"❌ Lỗi: {str(e)}")
            finally:
                self.ffmpeg_process = None
                self.is_running = False
                self.btn_run.configure(state="normal")
                self.btn_preview.configure(state="normal")
                self.btn_cancel.configure(state="disabled")
                
        threading.Thread(target=task, daemon=True).start()

    def render_single_unit(self, ffmpeg_exe, vid_list, voc, txt, preset, zoom_val, x_val, y_val, out_file, is_draft):
        needs_cleanup_merged = False
        temp_files = []
        concat_txt, merged_vid = "", ""
        ass_file = "temp_style.ass"
        
        try:
            if len(vid_list) > 1 or vid_list[0].lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                self.log(f"-> Chuẩn hóa {len(vid_list)} file...")
                for i, v in enumerate(vid_list):
                    if not self.is_running: return
                    ext = v.lower().split('.')[-1]
                    is_image = ext in ['jpg', 'jpeg', 'png', 'webp']
                    tmp_out = f"temp_vid_{i}.mp4"
                    standardize_media(ffmpeg_exe, v, tmp_out, is_image, preset, zoom=zoom_val, x_off=x_val, y_off=y_val, use_gpu=self.gpu_var.get())
                    temp_files.append(tmp_out)
                    
                concat_txt = "concat_list.txt"
                with open(concat_txt, "w", encoding="utf-8") as f:
                    for t in temp_files: f.write(f"file '{t}'\n")
                
                merged_vid = "temp_merged.mp4"
                subprocess.run([ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", merged_vid])
                final_vid_input = merged_vid
                needs_cleanup_merged = True
            else:
                final_vid_input = vid_list[0]
            
            
            vf_filters = []
            speed_str = self.speed_var.get()
            speed_val = 1.0
            if "0.5x" in speed_str: speed_val = 0.5
            elif "0.75x" in speed_str: speed_val = 0.75
            elif "1.25x" in speed_str: speed_val = 1.25
            elif "1.5x" in speed_str: speed_val = 1.5
            elif "2.0x" in speed_str: speed_val = 2.0
            if speed_val != 1.0: vf_filters.append(f"setpts={1.0/speed_val}*PTS")
            
            if not needs_cleanup_merged:
                w, h = 0, 0
                if "9:16" in preset: w, h = 1080, 1920
                elif "16:9" in preset: w, h = 1920, 1080
                    
                if w > 0:
                    scale_w = int(w * (zoom_val / 100.0))
                    scale_h = int(h * (zoom_val / 100.0))
                    px = 0.5 + (x_val / 100.0)
                    py = 0.5 + (y_val / 100.0)
                    vf_filters.append(f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase")
                    vf_filters.append(f"crop={w}:{h}:(in_w-{w})*{px}:(in_h-{h})*{py}")
            else:
                w, h = 1080, 1920
                if "16:9" in preset: w, h = 1920, 1080
                elif "9:16" not in preset: w, h = 1080, 1080
            
            font_name = self.font_var.get()
            font_size = int(self.size_var.get())
                
            wrapped_txt, real_font_size = self.get_wrapped_text(txt, preset, font_size)
            
            # Tính toán vị trí pixel chính xác dựa trên tọa độ Drag thả
            pos_x = int(self.text_x * w)
            pos_y = int(self.text_y * h)
            
            txt_formatted = wrapped_txt.replace('\n', '\\N')
            
            bg_enabled = self.bg_enable_var.get()
            opacity_pct = int(self.bg_opacity_var.get())
            bg_hex = self.bg_color_var.get().strip().lstrip('#')
            if len(bg_hex) != 6: bg_hex = "000000"
            
            bgr_hex = bg_hex[4:6] + bg_hex[2:4] + bg_hex[0:2]
            alpha_val = int(255 - (opacity_pct / 100.0 * 255))
            alpha_hex = f"{alpha_val:02X}"
            
            border_style = 1
            tags = f"\\pos({pos_x},{pos_y})"
            final_text = f"{{{tags}}}{txt_formatted}"
            
            ass_style = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 1
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MainStyle,{font_name},{real_font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,{border_style},3,0,5,20,20,0,1
Style: BoxStyle,Arial,10,&H{alpha_hex}{bgr_hex},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            if self.show_text_var.get() and txt:
                if bg_enabled and wrapped_txt:
                    lines = wrapped_txt.split('\n')
                    line_count = len(lines)
                    max_chars = max([len(l) for l in lines]) if lines else 0
                    
                    pad_x = int(self.bg_width_var.get())
                    pad_y = int(self.bg_height_var.get())
                    
                    canvas_h_ref = 640 if "9:16" in preset else 360
                    if "9:16" not in preset and "16:9" not in preset: canvas_h_ref = 480
                    pad_x_real = int(pad_x * (h / canvas_h_ref))
                    pad_y_real = int(pad_y * (h / canvas_h_ref))
                    
                    # Đồng bộ chính xác 100% kích thước khung viền từ Live Preview sang Video Output
                    if hasattr(self, 'text_w_ratio'):
                        box_w = int(self.text_w_ratio * w + pad_x_real * 2)
                        box_h = int(self.text_h_ratio * h + pad_y_real * 2)
                    else:
                        box_w = int(max_chars * real_font_size * 0.55 + pad_x_real * 2 + 10)
                        box_h = int(line_count * real_font_size * 1.25 + pad_y_real * 2 + 10)
                        
                    box_x = int(pos_x - box_w / 2)
                    box_y = int(pos_y - box_h / 2)
                    
                    radius_ui = int(self.bg_radius_var.get())
                    radius_real = int(radius_ui * (h / canvas_h_ref))
                    ass_drawing = self.get_ass_rounded_rect(box_w, box_h, radius_real)
                    
                    ass_style += f"Dialogue: 0,0:00:00.00,1:00:00.00,BoxStyle,,0,0,0,,{{\\pos({box_x},{box_y})}}{ass_drawing}\n"

                ass_style += f"Dialogue: 1,0:00:00.00,1:00:00.00,MainStyle,,0,0,0,,{final_text}\n"

                with open(ass_file, "w", encoding="utf-8") as f: f.write(ass_style)
                
                vf_filters.append(subtitle_filter(ass_file))
            
            # Nếu là bản nháp, ta scale nhỏ lại bằng FFmpeg filter để encode cho siêu nhanh
            if is_draft:
                if "9:16" in preset: vf_filters.append("scale=360:640")
                elif "16:9" in preset: vf_filters.append("scale=640:360")
                
            cmd = [ffmpeg_exe, "-y"]
            if self.loop_var.get(): cmd.extend(["-stream_loop", "-1"])
                
            cmd.extend([
                "-i", final_vid_input,
                "-i", voc,
                "-vf", ",".join(vf_filters),
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-map", "0:v:0", "-map", "1:a:0"
            ])
            
            if is_draft:
                if self.gpu_var.get():
                    cmd.extend(["-c:v", "h264_nvenc", "-preset", "p1", "-c:a", "aac", "-b:a", "96k"])
                else:
                    cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "35", "-c:a", "aac", "-b:a", "96k"])
            else:
                if self.gpu_var.get():
                    cmd.extend([
                        "-c:v", "h264_nvenc", 
                        "-preset", "p4", 
                        "-b:v", "10M", 
                        "-maxrate", "12M", 
                        "-bufsize", "24M",
                        "-profile:v", "high", 
                        "-level", "4.1",
                        "-r", "30",
                        "-g", "60", 
                        "-keyint_min", "60",
                        "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", 
                        "-color_primaries", "bt709", 
                        "-color_trc", "bt709",
                        "-movflags", "+faststart",
                        "-c:a", "aac", 
                        "-b:a", "192k", 
                        "-ar", "48000", 
                        "-ac", "2"
                    ])
                else:
                    cmd.extend([
                        "-c:v", "libx264", 
                        "-preset", "fast", 
                        "-b:v", "10M", 
                        "-maxrate", "12M", 
                        "-bufsize", "24M",
                        "-profile:v", "high", 
                        "-level", "4.1",
                        "-r", "30",
                        "-g", "60", 
                        "-keyint_min", "60",
                        "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", 
                        "-color_primaries", "bt709", 
                        "-color_trc", "bt709",
                        "-movflags", "+faststart",
                        "-c:a", "aac", 
                        "-b:a", "192k", 
                        "-ar", "48000", 
                        "-ac", "2"
                    ])
                
            cmd.extend(["-shortest", "-fflags", "+shortest", out_file])
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            self.log(f"-> Bắt đầu Render (Xuất ra {os.path.basename(out_file)})...")
            self.ffmpeg_process = subprocess.Popen(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Đọc output để báo tiến độ live
            while True:
                line = self.ffmpeg_process.stdout.readline()
                if not line: break
                if "time=" in line:
                    match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", line)
                    if match:
                        self.lbl_status.configure(text=f"Tiến độ Render: Đã xử lý {match.group(1)}...")
            
            self.ffmpeg_process.wait()
            
        finally:
            if os.path.exists(ass_file): os.remove(ass_file)
            if needs_cleanup_merged:
                for t in temp_files: 
                    if os.path.exists(t): os.remove(t)
                if os.path.exists(concat_txt): os.remove(concat_txt)
                if os.path.exists(merged_vid): os.remove(merged_vid)

if __name__ == "__main__":
    app = AutoVideoApp()
    app.mainloop()
