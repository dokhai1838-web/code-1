import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import subprocess
import imageio_ffmpeg

def create_video_process(video_path, voice_path, text_content, output_path, update_status_callback):
    try:
        update_status_callback("⏳ Đang xử lý FFmpeg... Vui lòng đợi...")
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Tự động thay thế dấu xuống dòng của ô Text thành mã \N của Subtitle
        text_content = text_content.replace('\n', '\\N')
        
        ass_style = f"""[Script Info]
ScriptType: v4.00+
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MainStyle,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,3,10,0,2,20,20,150,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,1:00:00.00,MainStyle,,0,0,0,,{text_content}
"""
        ass_filename = "temp_subtitle.ass"
        with open(ass_filename, "w", encoding="utf-8") as f:
            f.write(ass_style)
            
        ffmpeg_cmd = [
            ffmpeg_exe,
            "-y",
            "-i", video_path,
            "-i", voice_path,
            "-vf", f"subtitles={ass_filename}",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
        
        # Ẩn cửa sổ Console đen của cmd trên Windows khi chạy ngầm FFmpeg
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(ffmpeg_cmd, startupinfo=startupinfo, capture_output=True, text=True)
        
        # Xóa file text tạm sau khi làm xong
        if os.path.exists(ass_filename):
            os.remove(ass_filename)
            
        if result.returncode == 0:
            update_status_callback("✅ XONG! Video đã được tạo thành công.")
            messagebox.showinfo("Thành công", f"Đã tạo video hoàn tất!\nNơi lưu: {output_path}")
        else:
            update_status_callback("❌ Có lỗi xảy ra trong quá trình render.")
            messagebox.showerror("Lỗi FFmpeg", result.stderr)
            
    except Exception as e:
        update_status_callback("❌ Đã xảy ra lỗi.")
        messagebox.showerror("Lỗi phần mềm", str(e))

class VideoToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Video Tool - Ghép Chữ và Voice")
        self.root.geometry("650x550")
        
        # --- CÁC THÀNH PHẦN GIAO DIỆN ---
        
        # 1. Video Select
        tk.Label(root, text="1. Chọn Video Nền (.mp4):", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        frame1 = tk.Frame(root)
        frame1.pack(fill="x", padx=20)
        self.entry_video = tk.Entry(frame1, width=70)
        self.entry_video.pack(side="left", padx=(0, 10))
        tk.Button(frame1, text="Tải File...", command=self.browse_video).pack(side="left")
        
        # 2. Audio Select
        tk.Label(root, text="2. Chọn File Âm Thanh (.mp3, .wav):", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        frame2 = tk.Frame(root)
        frame2.pack(fill="x", padx=20)
        self.entry_voice = tk.Entry(frame2, width=70)
        self.entry_voice.pack(side="left", padx=(0, 10))
        tk.Button(frame2, text="Tải File...", command=self.browse_voice).pack(side="left")
        
        # 3. Text Input
        tk.Label(root, text="3. Nội Dung Text Hiển Thị (Bạn có thể Enter để xuống dòng tự do):", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.text_content = tk.Text(root, height=6, width=75, font=("Arial", 10))
        self.text_content.pack(padx=20)
        
        # 4. Output Select
        tk.Label(root, text="4. Nơi Lưu Video Mới (Kết quả):", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        frame3 = tk.Frame(root)
        frame3.pack(fill="x", padx=20)
        self.entry_output = tk.Entry(frame3, width=70)
        self.entry_output.pack(side="left", padx=(0, 10))
        tk.Button(frame3, text="Chọn Chỗ Lưu...", command=self.browse_output).pack(side="left")
        
        # 5. Action Button
        self.btn_run = tk.Button(root, text="🚀 BẮT ĐẦU TẠO VIDEO", font=("Arial", 14, "bold"), bg="#ff4757", fg="white", command=self.start_process, height=2, width=30)
        self.btn_run.pack(pady=30)
        
        # 6. Status
        self.lbl_status = tk.Label(root, text="Trạng thái: Sẵn sàng", fg="blue", font=("Arial", 10, "italic"))
        self.lbl_status.pack()

    def browse_video(self):
        filename = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov")])
        if filename:
            self.entry_video.delete(0, tk.END)
            self.entry_video.insert(0, filename)
            
    def browse_voice(self):
        filename = filedialog.askopenfilename(filetypes=[("Audio files", "*.mp3 *.wav *.m4a")])
        if filename:
            self.entry_voice.delete(0, tk.END)
            self.entry_voice.insert(0, filename)
            
    def browse_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 file", "*.mp4")])
        if filename:
            self.entry_output.delete(0, tk.END)
            self.entry_output.insert(0, filename)
            
    def update_status(self, text):
        self.lbl_status.config(text=text)
        self.root.update_idletasks()

    def start_process(self):
        video = self.entry_video.get()
        voice = self.entry_voice.get()
        out = self.entry_output.get()
        txt = self.text_content.get("1.0", tk.END).strip()
        
        if not video or not voice or not out:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn đầy đủ Video, Âm thanh và Nơi lưu!")
            return
            
        if not txt:
            messagebox.showwarning("Thiếu thông tin", "Nội dung Text đang để trống!")
            return
            
        # Vô hiệu hóa nút bấm để tránh click nhiều lần
        self.btn_run.config(state=tk.DISABLED, text="Đang xử lý...")
        
        # Chạy thuật toán render ngầm ở 1 luồng khác (Thread) để giao diện không bị giật lagg
        def task():
            create_video_process(video, voice, txt, out, self.update_status)
            self.btn_run.config(state=tk.NORMAL, text="🚀 BẮT ĐẦU TẠO VIDEO")
            
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoToolApp(root)
    root.mainloop()
