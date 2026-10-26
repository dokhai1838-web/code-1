import sys, subprocess, tempfile, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from font_support import subtitle_filter, BUNDLED_FAMILIES
import imageio_ffmpeg
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
r=subprocess.run([ffmpeg,'-hide_banner','-filters'],capture_output=True,text=True)
assert ' subtitles ' in r.stdout, 'Bundled FFmpeg missing subtitles'
print('imageio FFmpeg subtitles supported')
with tempfile.TemporaryDirectory(prefix="font test ' dấu ,:",dir='/tmp') as directory:
 p=Path(directory)/"phụ đề's, test.ass"
 hashes=[]
 for family in BUNDLED_FAMILIES:
  p.write_text(f'''[Script Info]
ScriptType: v4.00+
PlayResX: 640
PlayResY: 360
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{family},32,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1,0,5,10,10,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Tiếng Việt: Đậm nét • Cảm xúc
''',encoding='utf-8')
  r=subprocess.run([ffmpeg,'-hide_banner','-f','lavfi','-i','color=c=black:s=640x360:d=0.2','-vf',subtitle_filter(p),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True)
  log=r.stderr.decode(errors='replace')
  if r.returncode: print(log); raise SystemExit(r.returncode)
  selections=[l for l in log.splitlines() if 'fontselect:' in l]
  assert selections, log
  assert 'Glyph ' not in log, log
  hashes.append(hashlib.sha256(r.stdout).hexdigest())
  print(family, selections[0])
 assert len(set(hashes))==len(hashes), 'Fonts must render distinctly'
print('PASS: all six fonts render distinctly with Vietnamese and escaped paths')
