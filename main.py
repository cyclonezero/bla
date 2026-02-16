

from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.align import Align
from rich.traceback import install
from rich.table import Table
import time, signal
import json
import urllib.request
from pathlib import Path
import subprocess
import os
import sys
from typing import Optional

install()

# Configure console for UTF-8 support on Windows
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

console = Console(legacy_windows=False)

def loadpassword():
    PASSWORD = os.getenv("MY_SECRET")
    if "MY_SECRET" in os.environ:
        del os.environ["MY_SECRET"]
    return PASSWORD


GAMES = [
    {"key": "1", "name": "Vua Thoát Hiểm", "desc": "Trí tuệ + phản xạ", "ver_key": "vth"},
    {"key": "2", "name": "VTD Mobile", "desc": "Đua thời gian - Điện thoại", "ver_key": "vtd_mobile"},
    {"key": "3", "name": "VTD PC", "desc": "Đua thời gian - Máy tính", "ver_key": "vtd_pc"},
]

BASE_DIR = Path(__file__).resolve().parent
if "LTOOL_ROOT" in os.environ:
    BASE_DIR = Path(os.environ["LTOOL_ROOT"])
DATA_DIR = BASE_DIR / ".data" if "LTOOL_ROOT" in os.environ else Path(__file__).resolve().parent / ".data"

# Ensure .data exists
if not DATA_DIR.exists():
    DATA_DIR.mkdir(exist_ok=True)
VERSION_SOURCE_URL = "https://raw.githubusercontent.com/cyclonezero/bla/main/version.json"
GITHUB_BASE_URL = "https://raw.githubusercontent.com/cyclonezero/bla/main/"
PASSWORD_GUARD = "cocaidaubuoiditmemaylaovclmtỉmaduoccunghayphetdaychu=)))laochomemcrackdauboiditmemay"
_VERSION_CACHE = {}

_NEEDS_REDRAW = False
def _on_winch(signum, frame):
    global _NEEDS_REDRAW
    _NEEDS_REDRAW = True

try:
    signal.signal(signal.SIGWINCH, _on_winch)
except Exception:
    pass


def _fetch_remote_version_data() -> dict:
    try:
        with urllib.request.urlopen(VERSION_SOURCE_URL, timeout=5) as response:
            content = response.read().decode('utf-8')
            return json.loads(content)
    except Exception:
        return {}


def load_version_data(force_refresh: bool = False) -> dict:
    global _VERSION_CACHE
    if _VERSION_CACHE and not force_refresh:
        return _VERSION_CACHE
    data = _fetch_remote_version_data()
    if not data:
        console.print(Panel("Không tải được version từ GitHub.", border_style="red"))
        data = {"game_version": {}}
    _VERSION_CACHE = data
    return data


def get_game_meta(ver_key: str) -> dict:
    data = load_version_data()
    return data.get("game_version", {}).get(ver_key, {})


def _prepare_password_env(env: dict) -> dict:
    env = env.copy()
    env["MY_SECRET"] = PASSWORD_GUARD
    env = env.copy()
    env["MY_SECRET"] = PASSWORD_GUARD
    env["LTOOL_ROOT"] = str(BASE_DIR) # Pass root to child processes
    return env
    return env


def ensure_password_gate() -> None:
    expected = (PASSWORD_GUARD or "").strip()
    if not expected or expected == "NHAP_PASSWORD_TAI_DAY":
        console.print(Panel("Có cái con cặc địt mẹ mầy!!", border_style="red"))
        sys.exit(1)
    loaded = loadpassword()
    if not loaded:
        console.print(Panel("Đéo được đâu!!", border_style="red"))
        sys.exit(1)
    if loaded.strip() != expected:
        console.print(Panel("Có cái đầu bùi =))", border_style="red"))
        sys.exit(1)


def fetch_and_save_game_script(script_name: str) -> Optional[Path]:
    """
    Tải script từ GitHub và lưu vào thư mục ẩn .data
    Trả về đường dẫn file đã lưu để execute.
    """
    if not script_name:
        return None
    
    url = f"{GITHUB_BASE_URL}{script_name}"
    target_path = DATA_DIR / script_name
    
    try:
        # console.print(f"[dim]Đang tải {script_name} về {DATA_DIR}...[/dim]")
        with urllib.request.urlopen(url, timeout=15) as response:
            code = response.read().decode('utf-8')
            
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(code)
            
        return target_path
    except Exception as exc:
        console.print(Panel(f"Không tải được {script_name}: {exc}", border_style="red"))
        # If file exists, try to reuse old version
        if target_path.exists():
            console.print("[yellow]Sử dụng phiên bản cũ đã tải...[/yellow]")
            return target_path
        return None


# ======== THEME SYSTEM ========
THEME = "modern_cyan"   # Modern sleek theme with cyan gradients

def _get_theme_colors():
    if THEME == "modern_cyan":
        return {
            "colors": ["bright_cyan", "cyan", "bright_blue"],
            "border": "bright_cyan",
            "subtitle": "bright_cyan",
            "title": "bright_cyan",
        }
    elif THEME == "cyberpunk":
        return {
            "colors": ["bright_magenta", "bright_blue", "bright_cyan"],
            "border": "bright_magenta",
            "subtitle": "bright_blue",
            "title": "bright_magenta",
        }
    elif THEME == "hacker_blue":
        return {
            "colors": ["bright_blue", "blue", "bright_blue"],
            "border": "bright_blue",
            "subtitle": "bright_blue",
            "title": "bright_blue",
        }
    else:  # default fallback
        return {
            "colors": ["bright_yellow", "bright_cyan", "yellow"],
            "border": "bright_yellow",
            "subtitle": "white",
            "title": "yellow",
        }




# ======== BANNER ADAPTIVE ========
def make_banner():
    theme = _get_theme_colors()
    width = console.size.width or 80

    wide_ascii = r"""
  _      _____ ___   ___  _     
 | |    |_   _/ _ \ / _ \| |    
 | |      | || | | | | | | |    
 | |___   | || |_| | |_| | |___ 
 |_____|  |_| \___/ \___/|_____|
    """

    compact_title = f" LTOOL - Premium Game Suite "

    # Kiểm tra độ rộng
    art = Text()
    
    if width >= 70:
        lines = wide_ascii.strip("\n").split("\n")
        for line in lines:
            trimmed = line.rstrip()
            max_len = width - 10
            if len(trimmed) > max_len:
                trimmed = trimmed[:max_len]
            
            # Apply gradient-style colors for modern look
            if "╗" in trimmed or "╔" in trimmed:
                art.append(trimmed, style="bold bright_cyan")
            elif "╚" in trimmed or "╝" in trimmed:
                art.append(trimmed, style="bold bright_blue")
            else:
                art.append(trimmed, style="bold cyan")
            art.append("\n")

        subtitle_text = Text(">> Advanced Gaming Platform ", style=f"bold {theme['subtitle']}")

        panel_width = min(width - 4, max(40, len(lines[0]) + 10))
    else:
        # Bản nhỏ khi terminal hẹp
        art.append(compact_title, style=f"bold {theme['title']}")
        art.append("\n")
        subtitle_text = Text(">> Advanced Gaming Platform", style=theme["subtitle"])
        panel_width = max(30, width - 4)

    return Panel(
        Align.center(art),
        padding=(0, 2),
        subtitle=subtitle_text,
        subtitle_align="center",
        expand=False,
        width=panel_width,
        box=box.HEAVY,
        border_style="bright_cyan"
    )


# ----------- NEW GAME MENU (LIST) ----------------
# This function renders a decorative single-column game list (doesn't affect banner or logic)
def make_game_list():
    """
    Trả về Panel chứa Table danh sách game kiểu "menu" đẹp, responsive.
    Designed to visually replace make_game_cards without affecting other logic.
    """
    width = console.size.width or 80

    table = Table.grid(padding=(0,1))
    table.add_column(justify="center", ratio=0)
    table.add_column(justify="left", ratio=1)

    # Header row inside a thin panel
    header = Text("=== LTOOL GAME MENU ===", style="bold bright_cyan")

    version_data = load_version_data()
    game_versions = version_data.get("game_version", {})

    for g in GAMES:
        ver_info = game_versions.get(g.get("ver_key", ""), {})
        ver = ver_info.get("version", "?")
        trang_thai = ver_info.get("trang_thai", None)

        # show version/status inline in title inside brackets, non-bold
        idx = Text(f" {g['key']} ", style="white")

        state_str = "UNKNOWN"
        if trang_thai is True:
            state_str = "ON"
        elif trang_thai is False:
            state_str = "OFF"

        bracket = f"[v{ver} | {state_str}]"
        title = Text.assemble((g['name'], "bold bright_white"), " ", (bracket, "dim white"), "\n", (g['desc'], "italic cyan"))

        table.add_row(idx, title)

    # Footer with shortcut hints
    footer = Text("=== [0] Exit ===", style="bold bright_magenta")

    panel = Panel(
        Align.center(table),
        title=header,
        subtitle=footer,
        padding=(1,2),
        box=box.HEAVY,
        border_style="bright_cyan",
        width=min(width-4, 70)
    )
    return panel


# ----------- MOCK GAME FLOW ------------------------
def show_game_flow(game):
    meta = get_game_meta(game.get("ver_key", ""))
    if not meta:
        console.print(Panel(f"Game {game['name']} chưa được cấu hình trong version.json", border_style="red"))
        Prompt.ask("Nhấn Enter để quay lại menu...", default="")
        return

    if not meta.get("trang_thai", False):
        console.print(Panel(f"{game['name']} đang tạm khóa.", border_style="yellow"))
        Prompt.ask("Nhấn Enter để quay lại menu...", default="")
        return

    script_name = meta.get("name")
    if not script_name:
        console.print(Panel("Không tìm thấy tên file cần chạy.", border_style="red"))
        Prompt.ask("Nhấn Enter để quay lại menu...", default="")
        return

    # Tải code và lưu vào .data
    game_path = fetch_and_save_game_script(script_name)
    if not game_path:
        Prompt.ask("Nhấn Enter để quay lại menu...", default="")
        return

    console.clear()
    console.print(Panel(f"Đang chạy {script_name}...", title=game['name'], border_style="bright_green"))

    # Backup environment
    env_backup = os.environ.copy()
    try:
        # Set environment variables cho game
        os.environ["MY_SECRET"] = PASSWORD_GUARD
        os.environ["LTOOL_ROOT"] = str(BASE_DIR)
        
        # Chạy game bằng subprocess để isolate tốt hơn và hỗ trợ input/output tốt hơn
        # Tuy nhiên user yêu cầu chạy thẳng, và các game này là python script.
        # Run using subprocess inside the CURRENT console window
        
        cmd = [sys.executable, str(game_path)]
        subprocess.call(cmd, cwd=BASE_DIR) # Run with CWD as ROOT specificed by user requirement (configs in root)
        
        console.print(Panel(f"{game['name']} đã kết thúc.", border_style="green"))
        
    except KeyboardInterrupt:
        console.print("[yellow]Đã dừng theo yêu cầu người dùng.[/]")
    except Exception as exc:
        console.print(Panel(f"Lỗi khi chạy game: {exc}", border_style="red"))
    finally:
        # Khôi phục environment về trạng thái ban đầu
        os.environ.clear()
        os.environ.update(env_backup)
        Prompt.ask("Nhấn Enter để quay lại menu...", default="")



def make_interactive_game_list(selected_index: int = 0):
    """
    Trả về Panel chứa Table danh sách game với mũi tên chọn.
    selected_index: index của game đang được chọn
    """
    width = console.size.width or 80

    table = Table.grid(padding=(0,1))
    table.add_column(justify="center", ratio=0)  # Arrow column
    table.add_column(justify="center", ratio=0)  # Number column
    table.add_column(justify="left", ratio=1)    # Game info column

    header = Text("=== LTOOL GAME MENU ===", style="bold bright_cyan")

    version_data = load_version_data()
    game_versions = version_data.get("game_version", {})

    for idx, g in enumerate(GAMES):
        ver_info = game_versions.get(g.get("ver_key", ""), {})
        ver = ver_info.get("version", "?")
        trang_thai = ver_info.get("trang_thai", None)

        if idx == selected_index:
            arrow = Text(" >>> ", style="bold bright_green")
        else:
            arrow = Text("     ", style="white")

        # Number
        num = Text(f" {g['key']} ", style="white")

        state_str = "UNKNOWN"
        if trang_thai is True:
            state_str = "ON"
        elif trang_thai is False:
            state_str = "OFF"

        bracket = f"[v{ver} | {state_str}]"
        
        # Highlight selected game
        if idx == selected_index:
            title = Text.assemble(
                (g['name'], "bold bright_yellow"), 
                " ", 
                (bracket, "dim yellow"), 
                "\n", 
                (g['desc'], "italic bright_cyan")
            )
        else:
            title = Text.assemble(
                (g['name'], "bold bright_white"), 
                " ", 
                (bracket, "dim white"), 
                "\n", 
                (g['desc'], "italic cyan")
            )

        table.add_row(arrow, num, title)

    # Footer with controls hint
    footer = Text("=== [↑↓] Di chuyển | [Enter] Chọn | [0] Thoát ===", style="bold bright_magenta")

    panel = Panel(
        Align.center(table),
        title=header,
        subtitle=footer,
        padding=(1,2),
        box=box.HEAVY,
        border_style="bright_cyan",
        width=min(width-4, 80)
    )
    return panel


def get_key_input():
    """Đọc input từ bàn phím, hỗ trợ arrow keys"""
    import msvcrt
    
    if msvcrt.kbhit():
        first_char = msvcrt.getch()
        
        # Check for special keys (arrows, etc)
        if first_char in (b'\x00', b'\xe0'):
            second_char = msvcrt.getch()
            # Arrow keys
            if second_char == b'H':  # Up arrow
                return 'up'
            elif second_char == b'P':  # Down arrow
                return 'down'
        # Regular keys
        elif first_char == b'\r':  # Enter
            return 'enter'
        elif first_char == b'0':  # 0 key
            return 'exit'
        elif first_char in (b'\x1b', b'\x03'):  # Esc or Ctrl+C
            return 'exit'
    
    return None


def select_game_interactive():
    """Interactive game selection with arrow keys"""
    selected_index = 0
    
    while True:
        console.clear()
        console.print(make_banner())
        console.print()
        console.print(make_interactive_game_list(selected_index))
        console.print()
        console.print("[dim]Sử dụng phím ↑↓ để di chuyển, Enter để chọn...[/dim]")
        
        # Wait for key input
        import time
        while True:
            key = get_key_input()
            if key:
                break
            time.sleep(0.05)  # Small delay to reduce CPU usage
        
        if key == 'up':
            selected_index = (selected_index - 1) % len(GAMES)
        elif key == 'down':
            selected_index = (selected_index + 1) % len(GAMES)
        elif key == 'enter':
            return GAMES[selected_index]
        elif key == 'exit':
            return None


def main():
    # ensure_password_gate()
    global _NEEDS_REDRAW
    while True:
        load_version_data(force_refresh=True)
        
        # Interactive game selection
        selected_game = select_game_interactive()
        
        if selected_game is None:
            console.print("[yellow]Thoát...[/]")
            break
        
        # Run selected game
        show_game_flow(selected_game)
        
        if _NEEDS_REDRAW:
            _NEEDS_REDRAW = False
            continue


if __name__ == "__main__":
    # ensure_password_gate()
    main()

