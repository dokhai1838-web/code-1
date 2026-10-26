import os
import sys
import subprocess
import argparse
import imageio_ffmpeg

def create_video(video_path, voice_path, text_content, output_path):
    print(f"\n[INFO] Đang xử lý Video: {video_path}")
    print(f"[INFO] Âm thanh: {voice_path}")
    
    # Lấy đường dẫn FFmpeg ngầm
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Xử lý text (đổi \n thành \N cho chuẩn Subtitle .ass)
    text_content = text_content.replace('\n', '\\N')
    
    # Định dạng Style chữ (Nền đen mờ 60%, chữ trắng)
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
    
    # Lệnh FFmpeg
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
    
    print("[INFO] Đang Render... Vui lòng đợi.\n")
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    
    if os.path.exists(ass_filename):
        os.remove(ass_filename)
        
    if result.returncode == 0:
        print(f"✅ THÀNH CÔNG! Video đã lưu tại: {output_path}")
    else:
        print(f"❌ LỖI RỒI! Chi tiết lỗi từ FFmpeg:\n{result.stderr}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool tự động ghép Video + Voice + Text (Terminal)")
    parser.add_argument("-v", "--video", default="video.mp4", help="Đường dẫn file video nền")
    parser.add_argument("-a", "--audio", default="voice.mp3", help="Đường dẫn file voice/audio")
    parser.add_argument("-t", "--textfile", default="text.txt", help="Đường dẫn file txt chứa chữ")
    parser.add_argument("-o", "--output", default="output.mp4", help="Tên video đầu ra")
    
    args = parser.parse_args()
    
    # Kiểm tra file có tồn tại không
    if not os.path.exists(args.video):
        print(f"❌ Lỗi: Không tìm thấy file '{args.video}'")
        sys.exit(1)
    if not os.path.exists(args.audio):
        print(f"❌ Lỗi: Không tìm thấy file '{args.audio}'")
        sys.exit(1)
        
    # Đọc nội dung file text
    text_data = ""
    if os.path.exists(args.textfile):
        with open(args.textfile, "r", encoding="utf-8") as f:
            text_data = f.read().strip()
    else:
        print(f"❌ Lỗi: Không tìm thấy file '{args.textfile}'")
        print("💡 Gợi ý: Hãy tạo một file tên là text.txt rồi viết nội dung vào đó.")
        sys.exit(1)
        
    if not text_data:
        print(f"❌ Lỗi: File '{args.textfile}' đang trống rỗng!")
        sys.exit(1)
        
    create_video(args.video, args.audio, text_data, args.output)
