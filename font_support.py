"""Bundled, OFL-licensed fonts shared by the two Auto Video editors."""
import ctypes
import ctypes.util
import os
from pathlib import Path
from tkinter import font as tkfont

FONT_DIR = Path(__file__).resolve().parent / 'fonts'
BUNDLED_FAMILIES = ('Be Vietnam Pro', 'Kanit', 'Anton', 'Lobster', 'Pacifico', 'Pattaya')
_REGISTERED = False

def register_fonts():
    """Register for this process; no admin rights or system font changes."""
    global _REGISTERED
    if _REGISTERED:
        return
    files = sorted(FONT_DIR.glob('*.ttf'))
    if not files:
        raise RuntimeError('Thiếu thư mục fonts. Hãy giải nén toàn bộ bộ công cụ.')
    if os.name == 'nt':
        add_font = ctypes.windll.gdi32.AddFontResourceExW
        add_font.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        add_font.restype = ctypes.c_int
        for path in files:
            if not add_font(str(path), 0x10, None):  # FR_PRIVATE
                raise RuntimeError(f'Không thể nạp phông chữ: {path.name}')
    else:
        library = ctypes.util.find_library('fontconfig')
        if not library:
            raise RuntimeError('Cần cài các tệp trong fonts vào hệ thống trước khi mở công cụ.')
        fc = ctypes.CDLL(library)
        fc.FcConfigGetCurrent.restype = ctypes.c_void_p
        fc.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        fc.FcConfigAppFontAddFile.restype = ctypes.c_int
        fc.FcConfigBuildFonts.argtypes = [ctypes.c_void_p]
        fc.FcConfigBuildFonts.restype = ctypes.c_int
        config = fc.FcConfigGetCurrent()
        for path in files:
            if not fc.FcConfigAppFontAddFile(config, os.fsencode(path)):
                raise RuntimeError(f'Không thể nạp phông chữ: {path.name}')
        if not fc.FcConfigBuildFonts(config):
            raise RuntimeError('Không thể cập nhật danh sách phông chữ.')
    _REGISTERED = True

def available_fonts(root):
    """Only offer families actually visible to Tk; never offer phantom fonts."""
    installed = set(tkfont.families(root))
    preferred = [name for name in BUNDLED_FAMILIES if name in installed]
    others = sorted((name for name in installed if name not in preferred
                     and not name.startswith('@') and not any(c in name for c in ',\n\r')),
                    key=str.casefold)
    return preferred + others

def _filter_path(path):
    # Escape both FFmpeg's option and filtergraph parsers, without a shell.
    value = Path(path).as_posix()
    option = ''.join('\\' + c if c in "\\':" else c for c in value)
    return ''.join('\\' + c if c in "\\'[],;" else c for c in option)

def subtitle_filter(ass_file):
    return f'subtitles=filename={_filter_path(ass_file)}:fontsdir={_filter_path(FONT_DIR)}'
