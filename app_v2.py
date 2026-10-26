import os
import re
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox
import imageio_ffmpeg
from font_support import register_fonts, available_fonts, subtitle_filter

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def standardize_media(ffmpeg_exe, input_path, output_path, is_image, target_preset, zoom=100, x_off=0, y_off=0):
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
        
        self.title("Auto Video Tool - Pro Edition")
        self.geometry("950x850") 
        
        self.ffmpeg_process = None
        self.last_output_dir = ""
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1) 
        
        # ==========================================
        # TAB VIEW
        # ==========================================
        self.tabview = ctk.CTkTabview(self.main_frame)
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
        self.ent_video = ctk.CTkEntry(self.frame_vid, placeholder_text="Chọn NHIỀU file cùng lúc")
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
        ctk.CTkButton(self.frame_txt_label, text="Tải từ file .txt", width=110, height=24, command=self.load_text_file).pack(side="right", padx=5)
        
        self.txt_content = ctk.CTkTextbox(self.tab_main, height=90)
        self.txt_content.grid(row=4, column=0, padx=15, pady=5, sticky="ew")
        
        lbl_settings = ctk.CTkLabel(self.tab_main, text="CÀI ĐẶT ĐẦU RA", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_settings.grid(row=5, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.frame_settings = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.frame_settings.grid(row=6, column=0, padx=10, pady=0, sticky="ew")
        self.frame_settings.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.frame_settings, text="Preset/Tỷ lệ:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.preset_var = ctk.StringVar(value="Facebook/Reels (9:16) - Fill Center")
        self.combo_preset = ctk.CTkComboBox(self.frame_settings, width=250, values=["Facebook/Reels (9:16) - Fill Center", "YouTube (16:9)", "Giữ Nguyên Nguồn"], variable=self.preset_var)
        self.combo_preset.grid(row=0, column=1, padx=5, sticky="w")
        
        ctk.CTkLabel(self.frame_settings, text="Chế độ lặp:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.loop_var = ctk.BooleanVar(value=True)
        self.chk_loop = ctk.CTkCheckBox(self.frame_settings, text="Cuốn chiếu (Lặp) video nền để che kín Voice", variable=self.loop_var)
        self.chk_loop.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(self.frame_settings, text="Tốc độ nền:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.speed_var = ctk.StringVar(value="1.0x (Bình thường)")
        self.combo_speed = ctk.CTkComboBox(self.frame_settings, width=200, values=["0.5x (Rất chậm)", "0.75x (Chậm)", "1.0x (Bình thường)", "1.25x (Nhanh)", "1.5x (Nhanh hơn)", "2.0x (Rất nhanh)"], variable=self.speed_var)
        self.combo_speed.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        
        ctk.CTkLabel(self.frame_settings, text="Thư mục xuất:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.ent_output = ctk.CTkEntry(self.frame_settings, placeholder_text="Chọn thư mục chứa video kết quả...")
        self.ent_output.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.frame_settings, text="Chọn Folder", width=110, command=self.browse_out_dir).grid(row=3, column=2, padx=5, pady=5)

    def setup_tab_zoom(self):
        lbl_title = ctk.CTkLabel(self.tab_zoom, text="ĐIỀU CHỈNH KHUNG HÌNH (XÓA LOGO/WATERMARK)", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_title.grid(row=0, column=0, padx=10, pady=(15, 10), sticky="w")
        
        frame = ctk.CTkFrame(self.tab_zoom, fg_color="transparent")
        frame.grid(row=1, column=0, padx=20, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)
        
        self.lbl_zoom_val = ctk.CTkLabel(frame, text="Phóng to (Zoom): 100%", width=150, anchor="w")
        self.lbl_zoom_val.grid(row=0, column=0, padx=10, pady=15, sticky="w")
        self.zoom_var = ctk.DoubleVar(value=100)
        self.slider_zoom = ctk.CTkSlider(frame, from_=100, to=200, variable=self.zoom_var, command=lambda v: self.lbl_zoom_val.configure(text=f"Phóng to (Zoom): {int(v)}%"))
        self.slider_zoom.grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        
        self.lbl_x_val = ctk.CTkLabel(frame, text="Dịch Trái/Phải (X): 0", width=150, anchor="w")
        self.lbl_x_val.grid(row=1, column=0, padx=10, pady=15, sticky="w")
        self.x_var = ctk.DoubleVar(value=0)
        self.slider_x = ctk.CTkSlider(frame, from_=-50, to=50, variable=self.x_var, command=lambda v: self.lbl_x_val.configure(text=f"Dịch Trái/Phải (X): {int(v)}"))
        self.slider_x.grid(row=1, column=1, padx=10, pady=15, sticky="ew")
        
        self.lbl_y_val = ctk.CTkLabel(frame, text="Dịch Lên/Xuống (Y): 0", width=150, anchor="w")
        self.lbl_y_val.grid(row=2, column=0, padx=10, pady=15, sticky="w")
        self.y_var = ctk.DoubleVar(value=0)
        self.slider_y = ctk.CTkSlider(frame, from_=-50, to=50, variable=self.y_var, command=lambda v: self.lbl_y_val.configure(text=f"Dịch Lên/Xuống (Y): {int(v)}"))
        self.slider_y.grid(row=2, column=1, padx=10, pady=15, sticky="ew")
        
        lbl_hint = ctk.CTkLabel(self.tab_zoom, text="* Mẹo: Kéo Zoom lên 105% - 110% rồi kéo thanh Y xuống dưới (hoặc lên trên)\nđể cắt bỏ logo của TikTok/Capcut ở góc viền màn hình.", text_color="gray", justify="left")
        lbl_hint.grid(row=2, column=0, padx=20, pady=20, sticky="w")

    def setup_tab_text(self):
        lbl_title = ctk.CTkLabel(self.tab_text, text="TÙY CHỈNH PHÔNG CHỮ & HIỂN THỊ", font=ctk.CTkFont(size=15, weight="bold"))
        lbl_title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
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
                                        variable=self.font_var, state="readonly")
        self.font_combo.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # 2. Cỡ chữ
        self.lbl_size_val = ctk.CTkLabel(frame, text="Cỡ chữ: 22")
        self.lbl_size_val.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.size_var = ctk.DoubleVar(value=22)
        self.slider_size = ctk.CTkSlider(frame, from_=10, to=100, variable=self.size_var, command=lambda v: self.lbl_size_val.configure(text=f"Cỡ chữ: {int(v)}"))
        self.slider_size.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # 3. Phông nền Toggle
        ctk.CTkLabel(frame, text="Phông nền:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.bg_enable_var = ctk.BooleanVar(value=True)
        self.chk_bg = ctk.CTkCheckBox(frame, text="Bật phông nền", variable=self.bg_enable_var, command=self.toggle_bg_settings)
        self.chk_bg.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # 4. Màu nền
        self.lbl_bg_color = ctk.CTkLabel(frame, text="Màu nền (Mã HEX):")
        self.lbl_bg_color.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.bg_color_var = ctk.StringVar(value="000000") # Mặc định đen
        self.ent_bg_color = ctk.CTkEntry(frame, textvariable=self.bg_color_var, width=100)
        self.ent_bg_color.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        # 5. Độ mờ nền
        self.lbl_bg_opacity = ctk.CTkLabel(frame, text="Độ mờ (Opacity): 60%")
        self.lbl_bg_opacity.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.bg_opacity_var = ctk.DoubleVar(value=60)
        self.slider_bg_opacity = ctk.CTkSlider(frame, from_=0, to=100, variable=self.bg_opacity_var, command=lambda v: self.lbl_bg_opacity.configure(text=f"Độ mờ (Opacity): {int(v)}%"))
        self.slider_bg_opacity.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        # 6. Chiều rộng nền (Padding X)
        self.lbl_bg_width = ctk.CTkLabel(frame, text="Chiều rộng nền: 10")
        self.lbl_bg_width.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.bg_width_var = ctk.DoubleVar(value=10)
        self.slider_bg_width = ctk.CTkSlider(frame, from_=0, to=50, variable=self.bg_width_var, command=lambda v: self.lbl_bg_width.configure(text=f"Chiều rộng nền: {int(v)}"))
        self.slider_bg_width.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        # 7. Chiều cao nền (Padding Y)
        self.lbl_bg_height = ctk.CTkLabel(frame, text="Chiều cao nền: 10")
        self.lbl_bg_height.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.bg_height_var = ctk.DoubleVar(value=10)
        self.slider_bg_height = ctk.CTkSlider(frame, from_=0, to=50, variable=self.bg_height_var, command=lambda v: self.lbl_bg_height.configure(text=f"Chiều cao nền: {int(v)}"))
        self.slider_bg_height.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        
        # 8. Di chuyển ngang
        self.lbl_pos_x = ctk.CTkLabel(frame, text="Di chuyển ngang (X): 50%")
        self.lbl_pos_x.grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.pos_x_var = ctk.DoubleVar(value=50)
        self.slider_pos_x = ctk.CTkSlider(frame, from_=0, to=100, variable=self.pos_x_var, command=lambda v: self.lbl_pos_x.configure(text=f"Di chuyển ngang (X): {int(v)}%"))
        self.slider_pos_x.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
        
        # 9. Di chuyển dọc
        self.lbl_pos_y = ctk.CTkLabel(frame, text="Di chuyển dọc (Y): 85%")
        self.lbl_pos_y.grid(row=8, column=0, padx=10, pady=5, sticky="w")
        self.pos_y_var = ctk.DoubleVar(value=85)
        self.slider_pos_y = ctk.CTkSlider(frame, from_=0, to=100, variable=self.pos_y_var, command=lambda v: self.lbl_pos_y.configure(text=f"Di chuyển dọc (Y): {int(v)}%"))
        self.slider_pos_y.grid(row=8, column=1, padx=10, pady=5, sticky="ew")

        self.font_sample = ctk.CTkLabel(frame, text="Tiếng Việt: Đậm nét • Cảm xúc • Sáng tạo",
                                       font=(self.font_var.get(), 22, "bold"), wraplength=390)
        self.font_sample.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.font_var.trace_add("write", self.on_font_change)
        ctk.CTkLabel(frame, text="Font kèm sẵn: Be Vietnam Pro, Kanit, Anton,\nLobster, Pacifico, Pattaya. Các font khác lấy từ máy.",
                     text_color="gray", justify="left").grid(row=10, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        lbl_hint = ctk.CTkLabel(self.tab_text, text="* Mẹo: Kéo thanh X và Y để đặt vị trí text tự do giống trên Capcut.", text_color="gray", justify="left")
        lbl_hint.grid(row=2, column=0, padx=20, pady=10, sticky="w")

    def toggle_bg_settings(self):
        state = "normal" if self.bg_enable_var.get() else "disabled"
        self.slider_bg_opacity.configure(state=state)
        self.ent_bg_color.configure(state=state)
        self.slider_bg_width.configure(state=state)
        self.slider_bg_height.configure(state=state)


    def on_font_change(self, *args):
        self.font_sample.configure(font=(self.font_var.get(), 22, "bold"))

    def setup_action_section(self):
        self.frame_action = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frame_action.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.frame_action.grid_columnconfigure(0, weight=1)
        self.frame_action.grid_columnconfigure(1, weight=1)
        self.frame_action.grid_columnconfigure(2, weight=1)
        
        self.btn_run = ctk.CTkButton(self.frame_action, text="▶ TẠO VIDEO", font=ctk.CTkFont(size=15, weight="bold"), height=40, fg_color="#2ecc71", hover_color="#27ae60", command=self.start_process)
        self.btn_run.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.btn_cancel = ctk.CTkButton(self.frame_action, text="■ HỦY", font=ctk.CTkFont(size=15, weight="bold"), height=40, fg_color="#e74c3c", hover_color="#c0392b", state="disabled", command=self.cancel_process)
        self.btn_cancel.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.btn_open_folder = ctk.CTkButton(self.frame_action, text="Mở Thư Mục Kết Quả", font=ctk.CTkFont(size=15, weight="bold"), height=40, fg_color="#3498db", hover_color="#2980b9", state="disabled", command=self.open_output_folder)
        self.btn_open_folder.grid(row=0, column=2, padx=5, sticky="ew")
        
        self.progressbar = ctk.CTkProgressBar(self.main_frame)
        self.progressbar.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.progressbar.set(0)
        
        self.lbl_status = ctk.CTkLabel(self.main_frame, text="Trạng thái: Đang chờ...", font=ctk.CTkFont(size=12, slant="italic"))
        self.lbl_status.grid(row=3, column=0, padx=15, sticky="w")
        
        self.log_box = ctk.CTkTextbox(self.main_frame, height=100, state="disabled", font=("Consolas", 12))
        self.log_box.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

    # --- HANDLERS ---
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
            
    def browse_voice(self):
        f = filedialog.askopenfilename(filetypes=[("Audio files", "*.mp3 *.wav *.m4a *.aac")])
        if f: self.ent_voice.delete(0, 'end'); self.ent_voice.insert(0, f)
            
    def browse_out_dir(self):
        d = filedialog.askdirectory()
        if d: self.ent_output.delete(0, 'end'); self.ent_output.insert(0, d)
        
    def load_text_file(self):
        f = filedialog.askopenfilename(title="Chọn file Text", filetypes=[("Text files", "*.txt")])
        if f:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    content = file.read()
                self.txt_content.delete("1.0", "end")
                self.txt_content.insert("1.0", content)
                self.log("Đã tải Text từ file thành công.")
            except Exception as e:
                messagebox.showerror("Lỗi đọc file", str(e))

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            os.startfile(self.last_output_dir)

    def get_auto_filename(self, out_dir):
        idx = 1
        while True:
            name = f"video_{idx:03d}.mp4"
            path = os.path.join(out_dir, name)
            if not os.path.exists(path):
                return path
            idx += 1

    def cancel_process(self):
        if self.ffmpeg_process:
            self.log("[CANCEL] Đang ép buộc dừng FFmpeg...")
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

    def start_process(self):
        vid_string = self.ent_video.get()
        voc = self.ent_voice.get()
        out_dir = self.ent_output.get()
        txt = self.txt_content.get("1.0", "end-1c").strip()
        preset = self.preset_var.get()
        
        zoom_val = int(self.zoom_var.get())
        x_val = int(self.x_var.get())
        y_val = int(self.y_var.get())
        
        if not all([vid_string, voc, out_dir, txt]):
            messagebox.showerror("Lỗi", "Vui lòng điền đủ 4 trường: Video, Voice, Text và Thư mục xuất!")
            return
            
        vid_list = [v.strip() for v in vid_string.split(";") if v.strip()]
        for v in vid_list:
            if not os.path.exists(v): return messagebox.showerror("Lỗi", f"Không tìm thấy file:\n{v}")
            
        if not os.path.exists(voc): return messagebox.showerror("Lỗi", "Không tìm thấy file Voice!")
            
        out_file = self.get_auto_filename(out_dir)
        self.last_output_dir = out_dir
        
        self.btn_run.configure(state="disabled", text="⏳ ĐANG RENDER...")
        self.btn_cancel.configure(state="normal")
        self.btn_open_folder.configure(state="disabled")
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()
        
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        
        font_name = self.font_var.get()
        font_size = int(self.size_var.get())
        
        bg_enabled = self.bg_enable_var.get()
        opacity_pct = int(self.bg_opacity_var.get())
        bg_hex = self.bg_color_var.get().strip().lstrip('#')
        if len(bg_hex) != 6:
            bg_hex = "000000"
            
        alpha_val = int(255 * (1 - opacity_pct / 100))
        alpha_hex = f"{alpha_val:02X}"
        bgr_hex = bg_hex[4:6] + bg_hex[2:4] + bg_hex[0:2]
        ass_bg_color = f"&H{alpha_hex}{bgr_hex}"
        
        border_style = 3 if bg_enabled else 1
        
        pos_x = int(self.pos_x_var.get() / 100.0 * 384)
        pos_y = int(self.pos_y_var.get() / 100.0 * 288)
        padding_x = int(self.bg_width_var.get())
        padding_y = int(self.bg_height_var.get())
        
        tags = f"\\pos({pos_x},{pos_y})"
        if bg_enabled:
            tags += f"\\xbord{padding_x}\\ybord{padding_y}"
        else:
            tags += f"\\bord3"
            
        def task():
            needs_cleanup_merged = False
            temp_files = []
            concat_txt, merged_vid = "", ""
            try:
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                
                # BƯỚC 1: XỬ LÝ NHÓM FILE NỀN
                if len(vid_list) > 1 or vid_list[0].lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    self.log(f"[BƯỚC 1] Đang chuẩn hóa và gộp {len(vid_list)} file nền...")
                    for i, v in enumerate(vid_list):
                        ext = v.lower().split('.')[-1]
                        is_image = ext in ['jpg', 'jpeg', 'png', 'webp']
                        tmp_out = f"temp_vid_{i}.mp4"
                        self.log(f"-> Đang xử lý: {os.path.basename(v)}")
                        standardize_media(ffmpeg_exe, v, tmp_out, is_image, preset, zoom=zoom_val, x_off=x_val, y_off=y_val)
                        temp_files.append(tmp_out)
                        
                    concat_txt = "concat_list.txt"
                    with open(concat_txt, "w", encoding="utf-8") as f:
                        for t in temp_files:
                            f.write(f"file '{t}'\n")
                    
                    merged_vid = "temp_merged.mp4"
                    self.log("-> Đang gộp thành chuỗi video gốc...")
                    subprocess.run([ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", merged_vid])
                    
                    final_vid_input = merged_vid
                    needs_cleanup_merged = True
                else:
                    self.log("[BƯỚC 1] Sử dụng 1 Video gốc.")
                    final_vid_input = vid_list[0]
                
                voice_dur = self.get_duration(voc)
                self.log(f"[BƯỚC 2] Phân tích Voice: {voice_dur:.1f}s")
                
                # BƯỚC 3: RENDER
                ass_file = "temp_style.ass"
                txt_formatted = txt.replace('\n', '\\N')
                final_text = f"{{{tags}}}{txt_formatted}"
                
                ass_style = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MainStyle,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,{ass_bg_color},-1,0,0,0,100,100,0,0,{border_style},0,0,5,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,1:00:00.00,MainStyle,,0,0,0,,{final_text}
"""
                with open(ass_file, "w", encoding="utf-8") as f:
                    f.write(ass_style)
                
                self.log("[BƯỚC 3] Tính toán Pipeline FFmpeg...")
                
                vf_filters = []
                
                speed_str = self.speed_var.get()
                speed_val = 1.0
                if "0.5x" in speed_str: speed_val = 0.5
                elif "0.75x" in speed_str: speed_val = 0.75
                elif "1.25x" in speed_str: speed_val = 1.25
                elif "1.5x" in speed_str: speed_val = 1.5
                elif "2.0x" in speed_str: speed_val = 2.0
                
                if speed_val != 1.0:
                    pts = 1.0 / speed_val
                    vf_filters.append(f"setpts={pts}*PTS")
                
                # Nếu video gốc là video đơn lẻ, ta phải scale và zoom ở đây. Nếu đã concat thì nó đã scale rồi.
                if not needs_cleanup_merged:
                    w, h = 0, 0
                    if "9:16" in preset:
                        w, h = 1080, 1920
                    elif "16:9" in preset:
                        w, h = 1920, 1080
                        
                    if w > 0:
                        z = zoom_val / 100.0
                        scale_w = int(w * z)
                        scale_h = int(h * z)
                        px = 0.5 + (x_val / 100.0)
                        py = 0.5 + (y_val / 100.0)
                        vf_filters.append(f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase")
                        vf_filters.append(f"crop={w}:{h}:(in_w-{w})*{px}:(in_h-{h})*{py}")
                
                vf_filters.append(subtitle_filter(ass_file))
                vf_string = ",".join(vf_filters)
                
                cmd = [ffmpeg_exe, "-y"]
                
                if self.loop_var.get():
                    cmd.extend(["-stream_loop", "-1"])
                    
                cmd.extend([
                    "-i", final_vid_input,
                    "-i", voc,
                    "-vf", vf_string,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    "-fflags", "+shortest",
                    out_file
                ])
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                self.log(f"[BƯỚC 4] Đang Render Video hoàn chỉnh... (Có thể mất 1-3 phút)")
                self.ffmpeg_process = subprocess.Popen(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.ffmpeg_process.communicate()
                
                if os.path.exists(ass_file): os.remove(ass_file)
                if needs_cleanup_merged:
                    for t in temp_files: 
                        if os.path.exists(t): os.remove(t)
                    if os.path.exists(concat_txt): os.remove(concat_txt)
                    if os.path.exists(merged_vid): os.remove(merged_vid)
                
                self.progressbar.stop()
                self.progressbar.configure(mode="determinate")
                
                if self.ffmpeg_process.returncode == 0:
                    self.progressbar.set(1)
                    self.log(f"✅ THÀNH CÔNG! Đã lưu: {out_file}")
                    self.btn_open_folder.configure(state="normal")
                    messagebox.showinfo("Thành công", f"Render hoàn tất!\nNơi lưu: {out_file}")
                elif self.ffmpeg_process.returncode in (1, -15):
                    self.log("🛑 ĐÃ HỦY Render.")
                    if os.path.exists(out_file): os.remove(out_file)
                else:
                    self.log(f"❌ LỖI RENDER! Mã: {self.ffmpeg_process.returncode}")
                    messagebox.showerror("Lỗi", "Có lỗi xảy ra trong FFmpeg.")
                    
            except Exception as e:
                self.progressbar.stop()
                self.log(f"❌ Lỗi Exception: {str(e)}")
            finally:
                self.ffmpeg_process = None
                self.btn_run.configure(state="normal", text="▶ TẠO VIDEO")
                self.btn_cancel.configure(state="disabled")
                
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    app = AutoVideoApp()
    app.mainloop()
