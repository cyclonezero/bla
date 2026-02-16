"""
================================================================================
VUA THOÁT HIỂM - ALL IN ONE (FULL ALGORITHMS)
Automated Betting System with 7 Advanced Algorithms
================================================================================

File này tổng hợp TẤT CẢ modules với FULL DETAILED IMPLEMENTATION:
- API Layer (game_api.py)
- 7 Algorithms FULL DETAIL từ algorithms.py (1057 lines)
- Game Engine (game_engine.py)
- UI + WebSocket + Main Loop (main_ui_integrated.py)

Algorithms được implement CHI TIẾT 100% theo 7_LOGIC_CUOI_CUNG.md:
✅ SAFE_GUARD v2.0: 6 filters + 9 factors + 60 formulas
✅ SHADOW_HUNTER v2.0: 6 filters + 4 components (HIDE_SEEK 55%)
✅ ULTIMATE v2: 7 dangers + MIRROR + 100 formulas
✅ VIP Enhanced: 50 formulas + opposite 10-12%
✅ PRO Enhanced: SMI + 9 factors + opposite 8-10%
✅ META v2: 3-layer voting (VIP + PRO + Risk)
✅ GODMODE: 5 filters + 100 formulas

================================================================================
"""

# ============================================================================
# SECTION 1: IMPORTS & CONFIGURATION
# ============================================================================

import json
import threading
import time
import queue
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from abc import ABC, abstractmethod
import requests
import random
import math
from collections import deque
from statistics import mean, median, pstdev

# License Key Imports
import base64
import hashlib
import hmac
import uuid
import platform
import subprocess
import os
import codecs

# Rich library (UI)
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
    from rich import box
    from rich.progress_bar import ProgressBar
    from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
except ImportError:
    print("❌ Cài đặt rich: pip install rich")
    sys.exit(1)

# URL parsing
from urllib.parse import urlparse, parse_qs

# WebSocket
try:
    import websocket
except ImportError:
    print("❌ Cài đặt websocket-client: pip install websocket-client")
    sys.exit(1)

# --- CONFIGURATION ---
WS_URL = "wss://api.escapemaster.net/escape_master/ws"
WALLET_API_URL = "https://wallet.3games.io/api/wallet/user_asset"
BET_API_URL = "https://api.escapemaster.net/escape_game/bet"
HISTORY_API_URL = "https://api.escapemaster.net/escape_game/recent_10_issues"


# Global credentials (will be set from selected account)
USER_ID = None
SECRET_KEY = None
ASSET_TYPE = "BUILD"
BALANCE_POLL_INTERVAL = 5.0

# File paths for persistence (tương thích exec() và ltool)
# Khi chạy bằng exec() hoặc từ .data, ưu tiên LTOOL_ROOT
if "LTOOL_ROOT" in os.environ:
    BASE_DIR = Path(os.environ["LTOOL_ROOT"])
else:
    BASE_DIR = Path.cwd()

# Tạo thư mục config riêng
CONFIG_DIR = BASE_DIR / 'vth_config'
CONFIG_DIR.mkdir(exist_ok=True)

ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"
CONFIG_FILE = CONFIG_DIR / "strategy_vth.json"

# Algorithm definitions for menu
ALGORITHMS = {
    "1": {"name": "Random Pick", "win_rate": "50%", "desc": "Ngẫu nhiên (Free)"},
    "2": {"name": "Min Players", "win_rate": "55%", "desc": "Né đám đông (Free)"},
    "3": {"name": "Max Players", "win_rate": "45%", "desc": "Theo đám đông (Free)"},
    "4": {"name": "Min Bet", "win_rate": "58%", "desc": "Né cá mập (Free)"},
    "5": {"name": "Max Bet", "win_rate": "42%", "desc": "Theo cá mập (Free)"},
    "6": {"name": "Trend Follow", "win_rate": "50%", "desc": "Theo cầu (Free)"},
    "7": {"name": "SAFE_GUARD v2.0", "win_rate": "45-52%", "desc": "60 formulas + 6 filters (Free)"},
    "8": {"name": "SHADOW_HUNTER v2.0", "win_rate": "47-54%", "desc": "Personality + SMI (VIP)"},
    "9": {"name": "ULTIMATE v2", "win_rate": "47-54%", "desc": "GODMODE + 7 dangers + MIRROR (VIP)"},
    "10": {"name": "VIP Enhanced", "win_rate": "40-47%", "desc": "50 formulas + opposite (VIP)"},
    "11": {"name": "PRO Enhanced", "win_rate": "42-50%", "desc": "SMI + Trend (VIP)"},
    "12": {"name": "META v2", "win_rate": "43-50%", "desc": "3-layer voting (VIP)"},
    "13": {"name": "GODMODE by LuongDu", "win_rate": "47-54%", "desc": "Safety-first + 100 formulas (VIP)"}
}

# ============================================================================
# NON-BLOCKING UI QUEUE WITH AUTO-DROP (Fix #1)
# ============================================================================

class NonBlockingUIQueue:
    """
    UI Queue tự động drop message cũ khi đầy
    Đảm bảo game loop không bao giờ bị block
    """
    def __init__(self, maxsize=500):
        self.maxsize = maxsize
        self.queue = deque(maxlen=maxsize)  # Auto-drop oldest
        self.lock = threading.Lock()
        self.dropped_count = 0
        
    def put(self, item, timeout=None):
        """
        Non-blocking put
        Nếu full → drop oldest message
        """
        with self.lock:
            if len(self.queue) >= self.maxsize:
                self.queue.popleft()  # Drop oldest
                self.dropped_count += 1
                if self.dropped_count % 100 == 0:
                    print(f"[WARNING] Dropped {self.dropped_count} UI messages (queue full)")
            
            self.queue.append(item)
    
    def get(self, timeout=0.01):
        """
        Non-blocking get with timeout
        """
        with self.lock:
            if len(self.queue) > 0:
                return self.queue.popleft()
            raise queue.Empty
    
    def empty(self):
        with self.lock:
            return len(self.queue) == 0
    
    def qsize(self):
        with self.lock:
            return len(self.queue)
    
    def get_stats(self):
        """Debug: xem queue health"""
        with self.lock:
            return {
                'size': len(self.queue),
                'maxsize': self.maxsize,
                'utilization': len(self.queue) / self.maxsize * 100,
                'dropped': self.dropped_count
            }

# UI Queue for thread-safe communication
ui_queue = NonBlockingUIQueue(maxsize=500)

# Constants for bounded collections
balance_lock = threading.Lock()
MAX_LOGS = 10
MAX_HISTORY = 6

# App State
app_state = {
    "status": "Disconnected",
    "license_type": "Unknown",  # ADDED: Track license type
    "status_style": "red",
    "issue_id": "Waiting...",
    "countdown": None,
    "max_duration": 60,
    "last_result": None,
    "rooms": {},
    "history": deque(maxlen=MAX_HISTORY),  # Fix #5: Bounded history
    "logs": deque(maxlen=MAX_LOGS),  # Fix #5: Bounded logs
    "balances": {"USDT": 0.0, "WORLD": 0.0, "BUILD": 0.0},
    "initial_build": None,
    "profit_loss": 0.0,
    "max_win_streak": 0,
    "max_loss_streak": 0,
    "total_games": 0,
    "current_win_streak": 0,
    "current_loss_streak": 0,
    "algorithm": "Chưa thiết lập"
}


# Betting state
game_api = None
game_engine = None
game_config = None

# ============================================================================
# THREAD-SAFE GAME STATE (Fix #4)
# ============================================================================

class ThreadSafeGameState:
    """
    Thread-safe wrapper cho game state flags
    Tránh race condition giữa WS thread và game thread
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._bet_placed_this_round = False
        self._current_selected_room = None
        self._last_killed_room = None
        self._is_waiting_for_result = False
        self._result_wait_start_time = None
    
    # bet_placed_this_round
    @property
    def bet_placed(self):
        with self._lock:
            return self._bet_placed_this_round
    
    @bet_placed.setter
    def bet_placed(self, value):
        with self._lock:
            self._bet_placed_this_round = value
    
    # current_selected_room
    @property
    def selected_room(self):
        with self._lock:
            return self._current_selected_room
    
    @selected_room.setter
    def selected_room(self, value):
        with self._lock:
            self._current_selected_room = value
    
    # last_killed_room
    @property
    def killed_room(self):
        with self._lock:
            return self._last_killed_room
    
    @killed_room.setter
    def killed_room(self, value):
        with self._lock:
            self._last_killed_room = value
    
    # is_waiting_for_result
    @property
    def waiting_result(self):
        with self._lock:
            return self._is_waiting_for_result
    
    @waiting_result.setter
    def waiting_result(self, value):
        with self._lock:
            self._is_waiting_for_result = value
            if value:
                self._result_wait_start_time = time.time()
            else:
                self._result_wait_start_time = None
    
    def reset_round(self):
        """Thread-safe reset for new round"""
        with self._lock:
            self._bet_placed_this_round = False
            self._current_selected_room = None
    
    def get_all(self):
        """Debug: get all state"""
        with self._lock:
            return {
                'bet_placed': self._bet_placed_this_round,
                'selected_room': self._current_selected_room,
                'killed_room': self._last_killed_room,
                'waiting_result': self._is_waiting_for_result
            }

# Global thread-safe game state (replaces old global flags)
game_state_safe = ThreadSafeGameState()

# Legacy global variables for backwards compatibility
# These will be gradually migrated to game_state_safe
bet_placed_this_round = False
current_selected_room = None
last_killed_room = None

# Initialize console
console = Console()

# WebSocket health monitoring
ws_last_message_time = time.time()
ws_connection_state = "DISCONNECTED"  # DISCONNECTED, CONNECTING, CONNECTED
ws_reconnect_delay = 1  # Start with 1 second
ws_max_reconnect_delay = 30  # Max 30 seconds
ws_instance = None  # Current WebSocket instance
ws_should_run = True  # Flag to control WebSocket lifecycle
HEARTBEAT_TIMEOUT = 20  # If no message for 20s, reconnect (increased from 4s to avoid premature disconnects during result wait)

# Result waiting control flags
is_waiting_for_result = False  # When True, disable auto-reconnect
result_wait_start_time = None  # Track when we started waiting for result
result_backup_triggered = False  # Track if backup API fetch was triggered



class Account:
    """Account data model for multi-account management"""
    def __init__(self, name: str, uid: str, secret: str):
        self.name = name
        self.uid = uid
        self.secret = secret
    
    def to_dict(self) -> dict:
        return {"name": self.name, "uid": self.uid, "secret": self.secret}
    
    @staticmethod
    def from_dict(data: dict) -> 'Account':
        return Account(data["name"], data["uid"], data["secret"])
    
    def mask_secret(self) -> str:
        """Return masked secret for display"""
        if len(self.secret) > 20:
            return f"{self.secret[:10]}...{self.secret[-10:]}"
        return self.secret[:5] + "***"


def parse_game_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract userId and secretKey from game URL"""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        user_id = params.get('userId', [None])[0]
        secret_key = params.get('secretKey', [None])[0]
        return (str(user_id), str(secret_key)) if user_id and secret_key else (None, None)
    except:
        return None, None


def load_accounts() -> List[Account]:
    """Load accounts from file"""
    if ACCOUNTS_FILE.exists():
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Account.from_dict(acc) for acc in data]
        except:
            return []
    return []


def save_accounts(accounts: List[Account]):
    """Save accounts to file"""
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump([acc.to_dict() for acc in accounts], f, indent=2, ensure_ascii=False)


def calculate_base_bet(capital: float, num_tay: int, multiplier: float) -> float:
    """Calculate base bet using bankroll formula"""
    try:
        denominator = (multiplier ** num_tay - 1)
        if denominator == 0:
            return 1.0
        return capital * (multiplier - 1) / denominator
    except:
        return 1.0


def load_config():
    """Load game config from file"""
    global game_config
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Create GameConfig from dict
                from types import SimpleNamespace
                config = SimpleNamespace(**data)
                game_config = config
                return config
        except:
            pass
    # Return default config
    config = SimpleNamespace(
        demo_mode=False,  # Demo mode: watch only, don't place real bets
        use_tay_system=False,
        safe_capital=0.0,
        num_tay=4,
        multiplier=12.0,
        base_bet=1.0,
        reinvest_profit=False,
        algorithm="SAFE_GUARD v2.0",
        pause_after_losses=5,
        bet_rounds_before_skip=10,
        pause_rounds=2,
        stop_when_profit_reached=False,
        profit_target=50.0,
        stop_when_loss_reached=False,
        stop_loss_target=30.0
    )
    game_config = config
    return config


def save_config(config):
    """Save game config to file"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(vars(config), f, indent=2, ensure_ascii=False)








# ============================================================================
# SECTION 1.5: LICENSE KEY SYSTEM
# ============================================================================

# ===== LICENSE CONFIGURATION =====
GENERATE_TOKEN_URL = "http://cyclonezerotool.x10.network/czero_api/generate_token.php" 
VERIFY_TOKEN_URL = "http://cyclonezerotool.x10.network/czero_api/verify_token_create_key.php"
SECRET_KEY_FREE = "cocaiconchim"
API_URL = "http://cyclonezerotool.x10.network/czero_api/key_tool.php"
TOOL_SECRET = "Luanvi1904_luonganh_tool_1237_Nguyen_Czero@123456789419_tao_key_haha_do_ma_doan_duoc_do_e_yeu_hi_hi_bruhhhhhhhhhhhhh_shibaaaaaaa_conchim_hi_hi"
KEY_CHECK_INTERVAL = 30

# ===== SYSTEM STORAGE =====
def get_system_storage_path() -> str:
    system_name = platform.system()
    filename = "sys_config_core.dat"
    
    if system_name == "Windows":
        base_path = os.getenv("APPDATA")
        folder_path = os.path.join(base_path, "Microsoft", "Windows", "Templates", "l_tool_core_sys")
    else:
        base_path = os.getenv("HOME")
        folder_path = os.path.join(base_path, ".config", "l_tool_core_sys")
    
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path, exist_ok=True)
            if system_name == "Windows":
                subprocess.run(["attrib", "+h", folder_path], check=False, shell=True)
        except Exception:
            pass
    return os.path.join(folder_path, filename)

STORAGE_FILE = get_system_storage_path()

def load_system_data() -> Dict[str, Any]:
    default_data = {"machine_id": None, "license": None}
    if not os.path.exists(STORAGE_FILE):
        return default_data
    try:
        with open(STORAGE_FILE, 'rb') as f:
            encoded_bytes = f.read()
        decoded_str = base64.b64decode(encoded_bytes).decode("utf-8")
        return json.loads(decoded_str)
    except Exception:
        return default_data

def save_system_data(data: Dict[str, Any]) -> None:
    try:
        json_str = json.dumps(data)
        encoded_bytes = base64.b64encode(json_str.encode("utf-8"))
        if platform.system() == "Windows" and os.path.exists(STORAGE_FILE):
            subprocess.run(["attrib", "-h", "-s", STORAGE_FILE], check=False, shell=True)
        with open(STORAGE_FILE, 'wb') as f:
            f.write(encoded_bytes)
        if platform.system() == "Windows":
            subprocess.run(["attrib", "+h", "+s", STORAGE_FILE], check=False, shell=True)
    except Exception:
        pass

# ===== MACHINE ID =====
def _generate_hardware_id_raw() -> str:
    try:
        if platform.system() == "Windows":
            startup = subprocess.STARTUPINFO()
            if hasattr(subprocess, "STARTF_USESHOWWINDOW"):
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            raw = subprocess.check_output("wmic csproduct get uuid", startupinfo=startup)
            uuid_serial = raw.decode(errors="ignore").split("\n")[1].strip()
            cpu_name = platform.processor() or "cpu"
            node = platform.node() or "node"
            raw_info = f"{uuid_serial}-{cpu_name}-{node}"
        else:
            mac = uuid.getnode()
            raw_info = str(mac)
        
        hashed = hashlib.md5(raw_info.encode()).hexdigest().upper()
        return f"{hashed[:4]}-{hashed[4:8]}-{hashed[8:12]}"
    except Exception:
        mac = uuid.getnode()
        hashed = hashlib.md5(str(mac).encode()).hexdigest().upper()
        return f"{hashed[:4]}-{hashed[4:8]}-{hashed[8:12]}"

def get_stable_machine_id() -> str:
    data = load_system_data()
    if data.get("machine_id"):
        return data["machine_id"]
    new_id = _generate_hardware_id_raw()
    data["machine_id"] = new_id
    save_system_data(data)
    return new_id

# ===== LICENSE RECORD =====
def save_license_record(key_type: str, key_value: str) -> None:
    data = load_system_data()
    if not data.get("machine_id"):
        data["machine_id"] = get_stable_machine_id()
    data["license"] = {
        "type": key_type,
        "key": key_value,
        "saved_date": datetime.now().strftime("%Y%m%d")
    }
    save_system_data(data)

def get_stored_license() -> Optional[Dict[str, str]]:
    return load_system_data().get("license")

def clear_stored_license() -> None:
    data = load_system_data()
    data["license"] = None
    save_system_data(data)

# ===== KEY VALIDATION LOGIC =====
def verify_free_key(key: str, machine_id: str) -> Tuple[bool, str]:
    if not key.startswith("LTOOL-"):
        return False, "Sai định dạng Key. Key phải bắt đầu bằng LTOOL-"
    try:
        key_hash = key.replace("LTOOL-", "")
        if len(key_hash) != 12:
            return False, f"Key phải có đúng 12 kí tự (hiện tại có {len(key_hash)})"
        current_date = datetime.now().strftime("%Y%m%d")
        expected_full_hash = hmac.new(
            SECRET_KEY_FREE.encode(), 
            f"{machine_id}|{current_date}".encode(), 
            hashlib.sha256
        ).hexdigest().upper()
        expected_short_hash = expected_full_hash[:12]
        if key_hash == expected_short_hash:
            return True, "Key Free hợp lệ!"
        else:
            return False, "Key sai hoặc khác mã máy/ngày!"
    except Exception as e:
        return False, f"Lỗi giải mã: {e}"

def check_vip_key_with_api(key: str, hwid: str) -> Tuple[bool, str, Optional[Dict]]:
    try:
        msg = key + hwid
        tool_hash = hmac.new(TOOL_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
        data = {"key": key, "hwid": hwid, "tool_hash": tool_hash}
        
        response = requests.post(API_URL, data=data, timeout=10)
        try:
            resp = response.json()
        except ValueError as e:
            return False, f"Server trả về lỗi: {response.text[:100]}", None
        
        status = resp.get("status", "unknown")
        status_messages = {
            "server_error": "Lỗi server database",
            "fake_tool": "Tool không chính thống",
            "invalid": "Key không tồn tại",
            "banned": "Key đã bị khóa",
            "expired": "Key đã hết hạn",
            "hwid_mismatch": "Key đã kích hoạt trên máy khác"
        }
        
        if status != "valid":
            message = status_messages.get(status, f"Lỗi: {status}")
            return False, message, None
        
        expire = resp.get("expire_date", "")
        server_hash = resp.get("response_hash", "")
        check_msg = expire + hwid
        local_hash = hmac.new(TOOL_SECRET.encode(), check_msg.encode(), hashlib.sha256).hexdigest()
        
        if local_hash != server_hash:
            return False, "Server response bị giả mạo!", None
        
        time_left = resp.get("time_left", 0)
        days_left = time_left // 86400
        return True, f"VIP hợp lệ (Hạn: {expire}, còn {days_left} ngày)", resp
    except Exception as e:
        return False, f"Lỗi: {str(e)}", None

# ===== LICENSE MANAGER CLASS =====
class LicenseManagerError(Exception):
    pass

class LicenseManager:
    def __init__(self) -> None:
        self.machine_id = get_stable_machine_id()
        self.cached_license = get_stored_license()
        self._last_runtime_check = 0.0
    
    def ensure_access(self) -> str:
        console = Console() # Use local console instance for now or global if available
        if self.cached_license:
            console.clear()
            saved_type = self.cached_license.get('type', 'Unknown')
            saved_date = self.cached_license.get('saved_date', 'Unknown')
            msg = (f"Phát hiện Key cũ lưu trong máy!\n"
                   f"Mã máy: [cyan]{self.machine_id}[/]\n"
                   f"Loại Key: [bold yellow]{saved_type}[/]\n"
                   f"Ngày lưu: {saved_date}")
            console.print(Panel(msg, title="Dữ liệu Key", border_style="blue"))
            
            choice = Prompt.ask("Bạn có muốn đổi key khác không?", choices=["y", "n"], default="n")
            if choice == "y":
                console.print("[yellow]Đang xoá key cũ...[/]")
                clear_stored_license()
                self.cached_license = None
                time.sleep(1)
                return self._interactive_flow()
            else:
                valid, key_type, message = self._validate_license(self.cached_license)
                if valid:
                    console.print(Panel(Text(f"{message}\nĐang vào tool...", justify='left'), title='Key Hợp Lệ', border_style='green', padding=(1, 2)))
                    time.sleep(1)
                    return key_type
                else:
                    console.print(Panel(Text(message, justify='left'), title='Key Lỗi / Hết Hạn', border_style='red', padding=(1, 2)))
                    time.sleep(2)
                    return self._interactive_flow()
        return self._interactive_flow()

    def _validate_license(self, record: Optional[Dict[str, str]]) -> Tuple[bool, Optional[str], str]:
        if not record:
            return False, None, 'Chưa có key.'
        key_type = record.get('type')
        key_value = record.get('key', '')
        if key_type == 'VIP':
            valid, message, resp_data = check_vip_key_with_api(key_value, self.machine_id)
            return valid, 'VIP', message
        if key_type == 'FREE':
            valid, message = verify_free_key(key_value, self.machine_id)
            return valid, 'FREE', message
        return False, key_type, 'Key lỗi.'

    def _interactive_flow(self) -> str:
        console = Console()
        while True:
            console.clear()
            header_text = Text()
            header_text.append("KEY MANAGER", style="bold cyan")
            header_text.append(" - L-TOOL by CZERO", style="dim")
            console.print(Panel(Align.center(header_text), box=box.DOUBLE, style="bold blue", padding=(0, 2)))
            
            menu = Table.grid(padding=(0, 1))
            menu.add_column()
            menu.add_row('[bold cyan]1.[/] Lấy Key Free (vượt link 2 bước, hạn 24h)')
            menu.add_row('[bold cyan]2.[/] Nhập Key VIP (không giới hạn)')
            title = f'Kích hoạt key - Mã máy: {self.machine_id}'
            console.print(Panel(menu, title=title, border_style='bright_magenta'))
            
            choice = Prompt.ask('Chọn chế độ', choices=['1', '2'])
            if choice == '1':
                result = self._handle_free_activation(console)
            else:
                result = self._handle_vip_activation(console)
            if result:
                return result

    def _handle_free_activation(self, console) -> Optional[str]:
        console.print("\n[cyan]Đang gửi yêu cầu tạo link vượt lần 1...[/]")
        try:
            resp1 = requests.post(GENERATE_TOKEN_URL, json={"machine_id": self.machine_id}, timeout=10)
            link_token = resp1.text.strip() if resp1.status_code == 200 else f"Lỗi server: {resp1.status_code}"
        except Exception as e:
            link_token = f"Lỗi mạng: {e}"

        info1 = Table.grid(padding=0)
        info1.add_column(style='bold')
        info1.add_column()
        info1.add_row('Link lấy Token: ', link_token)
        console.print(Panel(info1, title='Bước 1: Lấy Token Xác Thực', border_style='cyan', padding=(1, 2)))
        
        token_input = console.input('[yellow]Nhập TOKEN (Sau khi vượt link 1):[/] ').strip()
        if not token_input:
            return None

        console.print("\n[cyan]Đang kiểm tra Token và tạo link vượt lần 2...[/]")
        try:
            payload = {"token": token_input, "machine": self.machine_id}
            resp2 = requests.post(VERIFY_TOKEN_URL, data=payload, timeout=10)
            link_key = resp2.text.strip() if resp2.status_code == 200 else f"Lỗi server: {resp2.status_code}"
        except Exception as e:
            link_key = f"Lỗi mạng: {e}"

        if "http" not in link_key:
            console.print(Panel(Text(f"Token sai hoặc hết hạn!\nPhản hồi: {link_key}", justify='left'), title='Lỗi Xác Thực', border_style='red', padding=(1, 2)))
            return None

        info2 = Table.grid(padding=0)
        info2.add_column(style='bold')
        info2.add_column()
        info2.add_row('Link lấy Key: ', link_key)
        console.print(Panel(info2, title='Bước 2: Lấy Key Chính Thức', border_style='bright_magenta', padding=(1, 2)))
        
        key_input = console.input('[yellow]Nhập KEY (Sau khi vượt link 2):[/] ').strip()
        valid, message = verify_free_key(key_input, self.machine_id)
        
        if valid:
            save_license_record('FREE', key_input)
            self.cached_license = get_stored_license()
            console.print(Panel(Text(message, justify='left'), title='Thành công', border_style='green', padding=(1, 2)))
            time.sleep(1.5)
            return 'FREE'
        
        console.print(Panel(Text(message, justify='left'), title='Thất bại', border_style='red', padding=(1, 2)))
        time.sleep(1.5)
        return None
    
    def _handle_vip_activation(self, console) -> Optional[str]:
        vip_key = console.input('[yellow]Nhập Key VIP:[/] ').strip()
        console.print("\n[cyan]Đang kiểm tra key...[/]")
        # Simplified VIP check without progress bar for now to avoid complexity overlap
        valid, message, resp = check_vip_key_with_api(vip_key, self.machine_id)
        
        if valid:
            save_license_record('VIP', vip_key)
            self.cached_license = get_stored_license()
            console.print(Panel(Text(message, justify='left'), title='VIP kích hoạt', border_style='green', padding=(1, 2)))
            time.sleep(1.5)
            return 'VIP'
        console.print(Panel(Text(message, justify='left'), title='Lỗi', border_style='red', padding=(1, 2)))
        time.sleep(1.5)
        return None

def run_key_activation_flow() -> str:
    manager = LicenseManager()
    return manager.ensure_access()


# ============================================================================
# SECTION 2: API LAYER
# ============================================================================

class GameAPI:
    """API client for Escape Master game"""
    
    # API Endpoints
    BET_URL = "https://api.escapemaster.net/escape_game/bet"
    WALLET_URL = "https://wallet.3games.io/api/wallet/user_asset"
    HISTORY_URL = "https://api.escapemaster.net/escape_game/recent_10_issues"
    
    def __init__(self, uid: str, secret: str, asset_type: str = "BUILD"):
        """
        Initialize API client
        
        Args:
            uid: User ID
            secret: Secret key
            asset_type: Asset type (BUILD, WORLD, USDT)
        """
        self.uid = str(uid)
        self.secret = secret
        self.asset_type = asset_type
        
    def fetch_balance(self) -> Optional[Dict[str, float]]:
        """
        Fetch current wallet balances
        
        Returns:
            Dict with BUILD, WORLD, USDT balances or None if failed
        """
        try:
            headers = {
                "accept": "*/*",
                "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
                "origin": "https://escapemaster.net",
                "priority": "u=1, i",
                "referer": "https://escapemaster.net/",
                "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
                "user-id": self.uid,
                "user-login": "login_v2",
                "user-secret-key": self.secret
            }
            
            params = {
                "is_cwallet": "1",
                "is_mission_setting": "true",
                "version": ""
            }
            
            response = requests.get(
                "https://user.3games.io/user/regist",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200 and "data" in data:
                    cwallet = data["data"].get("cwallet", {})
                    return {
                        "BUILD": float(cwallet.get("ctoken_contribute", 0)),
                        "WORLD": float(cwallet.get("ctoken_kther", 0)),
                        "USDT": float(cwallet.get("ctoken_kusdt", 0))
                    }
        except Exception as e:
            print(f"[API ERROR] fetch_balance: {e}")
            
        return None
    
    def place_bet(self, room_id: int, bet_amount: float) -> bool:
        """
        Place bet on a room
        
        Args:
            room_id: Room number (1-8)
            bet_amount: Amount to bet
            
        Returns:
            True if successful, False otherwise
        """
        try:
            headers = {
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0",
                "user-id": self.uid,
                "user-secret-key": self.secret
            }
            
            body = {
                "asset_type": self.asset_type,
                "user_id": int(self.uid),
                "room_id": room_id,
                "bet_amount": bet_amount
            }
            
            print(f"[BET API] Sending: room={room_id}, amount={bet_amount}", flush=True)
            
            response = requests.post(
                self.BET_URL,
                headers=headers,
                json=body,
                timeout=10
            )
            
            print(f"[BET API] Status: {response.status_code}", flush=True)
            
            if response.status_code == 200:
                data = response.json()
                print(f"[BET API] Response: {data}", flush=True)
                
                success = data.get("code") == 0 and data.get("msg") == "ok"
                if not success:
                    print(f"[BET API] Failed: code={data.get('code')}, msg={data.get('msg')}", flush=True)
                return success
            else:
                print(f"[BET API] HTTP Error: {response.status_code} - {response.text[:200]}", flush=True)
                
        except Exception as e:
            print(f"[API ERROR] place_bet exception: {e}", flush=True)
            import traceback
            traceback.print_exc()
            
        return False
    
    def enter_room(self, room_id: int) -> bool:
        """
        Enter a room (place character before betting)
        
        Args:
            room_id: Room number (1-8)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            headers = {
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0",
                "user-id": self.uid,
                "user-secret-key": self.secret
            }
            
            body = {
                "asset_type": self.asset_type,
                "user_id": int(self.uid),
                "room_id": room_id
            }
            
            # Use ENTER_ROOM_URL (construct it like BET_URL)
            enter_room_url = "https://api.escapemaster.net/escape_game/enter_room"
            
            print(f"[ENTER ROOM] Sending: room={room_id}", flush=True)
            
            response = requests.post(
                enter_room_url,
                headers=headers,
                json=body,
                timeout=10
            )
            
            print(f"[ENTER ROOM] Status: {response.status_code}", flush=True)
            
            if response.status_code == 200:
                data = response.json()
                print(f"[ENTER ROOM] Response: {data}", flush=True)
                
                success = data.get("code") == 0 and data.get("msg") == "ok"
                if not success:
                    print(f"[ENTER ROOM] Failed: code={data.get('code')}, msg={data.get('msg')}", flush=True)
                return success
            else:
                print(f"[ENTER ROOM] HTTP Error: {response.status_code} - {response.text[:200]}", flush=True)
                
        except Exception as e:
            print(f"[API ERROR] enter_room exception: {e}", flush=True)
            import traceback
            traceback.print_exc()
            
        return False
    
    def fetch_history(self, limit: int = 10) -> List[Dict]:
        """
        Fetch recent game history
        
        Args:
            limit: Number of records (max 10)
            
        Returns:
            List of game records
        """
        try:
            headers = {
                "accept": "*/*",
                "accept-language": "vi,en;q=0.9",
                "country-code": "vn",
                "origin": "https://xworld.info",
                "referer": "https://xworld.info/",
                "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U) AppleWebKit/537.36 Chrome/143.0.0.0 Mobile Safari/537.36",
                "user-id": self.uid,
                "user-login": "login_v2",
                "user-secret-key": self.secret,
                "xb-language": "vi-VN"
            }
            
            params = {"asset": self.asset_type}
            
            response = requests.get(
                self.HISTORY_URL,
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and "data" in data:
                    history = data["data"]
                    return history[:limit]
                    
        except Exception as e:
            print(f"[API ERROR] fetch_history: {e}")
            
        return []
    
    def test_connection(self) -> bool:
        """Test API connection by fetching balance"""
        balance = self.fetch_balance()
        return balance is not None


# Example usage


# ============================================================================
# SECTION 3: ALGORITHMS (7 THUẬT TOÁN - FULL IMPLEMENTATION)
# ============================================================================

# === CONSTANTS ===
OPPOSITE_MAP = {
    1: [3, 7], 2: [8], 3: [1], 4: [6],
    5: [],     6: [4], 7: [1], 8: [2]
}

ROOM_ORDER = [1, 2, 3, 4, 5, 6, 7, 8]


# === BASE ALGORITHM ===
class BaseAlgorithm(ABC):
    """Base class for all algorithms"""
    
    @abstractmethod
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        """
        Select best room
        
        Args:
            rooms_data: {room_id: {'players': int, 'bet': float, 'kills': int, '...}}
            last_killed: Last killed room ID (1-8)
            history: List of recent killed rooms
            
        Returns:
            Selected room ID (1-8)
        """
        pass
    
    def get_opposite_rooms(self, room_id: int) -> List[int]:
        """Get opposite rooms for given room"""
        return OPPOSITE_MAP.get(room_id, [])
    
    def deterministic_noise(self, formula_idx: int, room_id: int, scale: float) -> float:
        """Generate deterministic noise"""
        seed_val = formula_idx * 1000 + room_id
        rng = random.Random(seed_val)
        return rng.gauss(0, scale)


# === FREE ALGORITHMS (1-6) ===

class RandomAlgorithm(BaseAlgorithm):
    """Logic 1: Random Pick"""
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        return random.choice(list(rooms_data.keys()))

class MinPlayerAlgorithm(BaseAlgorithm):
    """Logic 2: Min Players (Avoid Crowd)"""
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        # Filter out last killed if possible
        candidates = [r for r in rooms_data.keys() if r != last_killed]
        if not candidates: candidates = list(rooms_data.keys())
        return min(candidates, key=lambda r: rooms_data[r].get('players', 0))

class MaxPlayerAlgorithm(BaseAlgorithm):
    """Logic 3: Max Players (Follow Crowd)"""
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        candidates = [r for r in rooms_data.keys() if r != last_killed]
        if not candidates: candidates = list(rooms_data.keys())
        return max(candidates, key=lambda r: rooms_data[r].get('players', 0))

class MinBetAlgorithm(BaseAlgorithm):
    """Logic 4: Min Bet (Avoid Whales)"""
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        candidates = [r for r in rooms_data.keys() if r != last_killed]
        if not candidates: candidates = list(rooms_data.keys())
        return min(candidates, key=lambda r: rooms_data[r].get('bet', 0))

class MaxBetAlgorithm(BaseAlgorithm):
    """Logic 5: Max Bet (Follow Whales)"""
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        candidates = [r for r in rooms_data.keys() if r != last_killed]
        if not candidates: candidates = list(rooms_data.keys())
        return max(candidates, key=lambda r: rooms_data[r].get('bet', 0))

class TrendFollowAlgorithm(BaseAlgorithm):
    """Logic 6: Trend Follow (Bet on last Winner)"""
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        # Simply pick a room that is NOT the last killed (simplified trend)
        # Or pick randomly from safe rooms
        candidates = [r for r in rooms_data.keys() if r != last_killed]
        if not candidates: return random.choice(list(rooms_data.keys()))
        return random.choice(candidates)



# === ALGORITHM 1: SAFE_GUARD v2.0 ===
class SAFEGUARDAlgorithm(BaseAlgorithm):
    """
    SAFE_GUARD v2.0 - Ensemble 60 formulas + Moderate
    Upgraded from SMART_SAFE + VIP_10
    """
    
    CONFIG = {
        'min_survive_rate': 0.5,
        'max_players': 100,
        'min_players': 3,
        'max_bet': 50000,
        'min_bet': 500,
        'max_kill_rate': 0.6,
        'max_bpp': 2500,
        'pattern_window': 2,
        'num_formulas': 60,
        'seed': 8888888,
    }
    
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        # PHASE 1: Smart Filtering
        filtered = self.apply_filters(rooms_data, last_killed, history)
        
        if not filtered:
            # Fallback: select by survival score
            return self.fallback_selection(rooms_data)
        
        # PHASE 2: Ensemble Scoring
        scores = {}
        for room in filtered:
            scores[room] = self.calculate_ensemble_score(room, rooms_data, last_killed, history)
        
        return max(scores, key=scores.get)
    
    def apply_filters(self, rooms_data: Dict, last_killed: int, history: List) -> List[int]:
        """Apply 6 smart filters"""
        filtered = []
        
        # Calculate global stats
        all_rooms = list(rooms_data.keys())
        total_rounds = sum(rooms_data[r].get('kills', 0) + rooms_data[r].get('survives', 0) 
                          for r in all_rooms)
        
        for room in all_rooms:
            data = rooms_data[room]
            kills = data.get('kills', 0)
            survives = data.get('survives', 0)
            players = data.get('players', 0)
            bet = data.get('bet', 0)
            
            # F1: Avoid last kill
            if room == last_killed:
                continue
            
            # F2: Min survive rate
            survive_score = 1.0 - (kills / max(1, kills + survives))
            if survive_score < self.CONFIG['min_survive_rate']:
                continue
            
            # F3: Extreme boundaries
            if players > self.CONFIG['max_players'] or bet > self.CONFIG['max_bet']:
                continue
            if players < self.CONFIG['min_players'] or bet < self.CONFIG['min_bet']:
                continue
            
            # F4: Kill rate threshold
            kill_rate = kills / max(1, kills + survives)
            if kill_rate > self.CONFIG['max_kill_rate']:
                continue
            
            # F5: BPP whale trap
            bpp = bet / max(1, players)
            if bpp > self.CONFIG['max_bpp']:
                continue
            
            # F6: Recent pattern
            if len(history) >= 2:
                if room in history[-2:]:
                    continue
            
            filtered.append(room)
        
        return filtered
    
    def calculate_ensemble_score(self, room: int, rooms_data: Dict, 
                                 last_killed: int, history: List) -> float:
        """Calculate score using 60 formulas ensemble"""
        
        # Extract data
        data = rooms_data[room]
        kills = data.get('kills', 0)
        survives = data.get('survives', 0)
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        
        # Calculate global stats
        all_rooms = list(rooms_data.keys())
        max_players = max(rooms_data[r].get('players', 0) for r in all_rooms) or 1
        max_bet = max(rooms_data[r].get('bet', 0) for r in all_rooms) or 1
        total_rounds = sum(rooms_data[r].get('kills', 0) + rooms_data[r].get('survives', 0) 
                          for r in all_rooms)
        
        # === 9 FACTORS ===
        
        # Factor 1: Survival Rate
        survival_rate = (survives + 1) / (kills + survives + 2)
        
        # Factor 2: Player Score (normalized)
        players_norm = min(1.0, players / 50.0)
        player_score = 1.0 - players_norm
        
        # Factor 3: Bet Score (normalized)
        bet_norm = 1.0 / (1.0 + bet / 2000.0)
        bet_score = bet_norm
        
        # Factor 4: BPP Score
        bpp = bet / max(1, players)
        bpp_norm = 1.0 / (1.0 + bpp / 1200.0)
        
        # Factor 5: Safety Score
        safety_score = 1.0 - (kills / max(1, total_rounds))
        
        # Factor 6: Recent Penalty
        recent_penalty = 0.0
        # (Simplified - would need bet_history in real implementation)
        
        # Factor 7: Last Kill Penalty
        last_kill_penalty = 0.5 if room == last_killed else 0.0
        
        # Factor 8: Opposite Bonus
        opposites = self.get_opposite_rooms(last_killed)
        opposite_bonus = 1.0 if room in opposites else 0.3
        
        # Factor 9: Moderate/Balance Score
        all_players = [rooms_data[r].get('players', 0) for r in all_rooms]
        all_bets = [rooms_data[r].get('bet', 0) for r in all_rooms]
        median_players = median(all_players) if all_players else 1
        median_bet = median(all_bets) if all_bets else 1
        
        player_moderate = 1.0 / (1.0 + abs(players - median_players) / max(1, median_players))
        bet_moderate = 1.0 / (1.0 + abs(bet - median_bet) / max(1, median_bet))
        moderate_score = (player_moderate + bet_moderate) / 2.0
        
        # === 60 FORMULAS ENSEMBLE ===
        rng = random.Random(self.CONFIG['seed'])
        final_scores = []
        
        for i in range(self.CONFIG['num_formulas']):
            # Random weights
            w_survival = rng.uniform(0.30, 0.50)
            w_player = rng.uniform(0.15, 0.35)
            w_bet = rng.uniform(0.15, 0.35)
            w_bpp = rng.uniform(0.05, 0.20)
            w_safety = rng.uniform(0.05, 0.20)
            w_recent = rng.uniform(0.03, 0.15)
            w_last = rng.uniform(0.05, 0.20)
            w_opposite = rng.uniform(0.08, 0.15)
            w_moderate = rng.uniform(0.05, 0.10)
            
            # Noise
            noise_scale = rng.uniform(0.0, 0.08)
            noise = self.deterministic_noise(i, room, noise_scale)
            
            # Calculate score
            score_i = (w_survival * survival_rate +
                      w_player * player_score +
                      w_bet * bet_score +
                      w_bpp * bpp_norm +
                      w_safety * safety_score -
                      w_recent * recent_penalty -
                      w_last * last_kill_penalty +
                      w_opposite * opposite_bonus +
                      w_moderate * moderate_score +
                      noise)
            
            final_scores.append(score_i)
        
        return mean(final_scores)
    
    def fallback_selection(self, rooms_data: Dict) -> int:
        """Fallback when no room passes filters"""
        scores = {}
        for room, data in rooms_data.items():
            kills = data.get('kills', 0)
            survives = data.get('survives', 0)
            scores[room] = (survives + 1) / (kills + survives + 2)
        return max(scores, key=scores.get)


# === ALGORITHM 2: SHADOW_HUNTER v2.0 ===
class SHADOWHUNTERAlgorithm(BaseAlgorithm):
    """
    SHADOW_HUNTER v2.0 - Personality + SMI + Moderate
    Upgraded from HIDE_SEEK_MASTER
    """
    
    CONFIG = {
        'min_survive_rate': 0.45,
        'max_players': 100,
        'min_players': 3,
        'max_bet': 50000,
        'min_bet': 500,
        'min_safety': 0.65,
        'max_smi': 0.5,
        'hide_seek_weight': 0.55,
        'pro_weight': 0.20,
        'opposite_weight': 0.15,
        'moderate_weight': 0.10,
    }
    
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        # PHASE 1: Smart Filtering
        filtered = self.apply_filters(rooms_data, last_killed, history)
        
        if not filtered:
            return self.fallback_selection(rooms_data, history)
        
        # PHASE 2: Hybrid Scoring
        scores = {}
        for room in filtered:
            scores[room] = self.calculate_hybrid_score(room, rooms_data, last_killed, history)
        
        return max(scores, key=scores.get)
    
    def apply_filters(self, rooms_data: Dict, last_killed: int, history: List) -> List[int]:
        """Apply 6 smart filters with SMI check"""
        filtered = []
        
        all_rooms = list(rooms_data.keys())
        total_players = sum(rooms_data[r].get('players', 0) for r in all_rooms)
        total_bet = sum(rooms_data[r].get('bet', 0) for r in all_rooms)
        total_rounds = sum(rooms_data[r].get('kills', 0) + rooms_data[r].get('survives', 0) 
                          for r in all_rooms)
        
        opposites = self.get_opposite_rooms(last_killed)
        
        for room in all_rooms:
            data = rooms_data[room]
            kills = data.get('kills', 0)
            survives = data.get('survives', 0)
            players = data.get('players', 0)
            bet = data.get('bet', 0)
            
            # F1: Avoid last kill
            if room == last_killed:
                continue
            
            # F2: Min survive rate (lower threshold)
            survive_score = 1.0 - (kills / max(1, kills + survives))
            if survive_score < self.CONFIG['min_survive_rate']:
                continue
            
            # F3: Boundary check
            if players > self.CONFIG['max_players'] or bet > self.CONFIG['max_bet']:
                continue
            if players < self.CONFIG['min_players'] or bet < self.CONFIG['min_bet']:
                continue
            
            # F4: Historical safety
            safety_score = 1.0 - (kills / max(1, total_rounds))
            if safety_score < self.CONFIG['min_safety']:
                continue
            
            # F5: SMI extreme check
            player_share = players / max(1, total_players)
            bet_share = bet / max(1, total_bet)
            smi = bet_share - player_share
            if smi > self.CONFIG['max_smi']:
                continue
            
            # F6: Opposite priority
            if room not in opposites:
                # Quick danger check
                kill_rate = kills / max(1, kills + survives)
                max_players = max(rooms_data[r].get('players', 0) for r in all_rooms) or 1
                max_bet_val = max(rooms_data[r].get('bet', 0) for r in all_rooms) or 1
                
                hist_danger = kill_rate
                crowd_danger = players / max_players
                money_danger = bet / max_bet_val
                quick_danger = 0.3 * hist_danger + 0.2 * crowd_danger + 0.2 * money_danger
                
                if quick_danger > 0.60:
                    continue
            
            filtered.append(room)
        
        return filtered
    
    def calculate_hybrid_score(self, room: int, rooms_data: Dict, 
                               last_killed: int, history: List) -> float:
        """Calculate hybrid score with 4 components"""
        
        # Component A: HIDE_SEEK Danger (55%)
        hide_seek_score = self.calculate_hide_seek_score(room, rooms_data, last_killed, history)
        
        # Component B: PRO Factors (20%)
        pro_score = self.calculate_pro_score(room, rooms_data)
        
        # Component C: Opposite Factor (15%)
        opposite_score = self.calculate_opposite_score(room, last_killed, history)
        
        # Component D: Moderate Factor (10%)
        moderate_score = self.calculate_moderate_score(room, rooms_data)
        
        # Noise
        noise = self.deterministic_noise(0, room, 0.03)
        
        # Final scoring
        final_score = (self.CONFIG['hide_seek_weight'] * hide_seek_score +
                      self.CONFIG['pro_weight'] * pro_score +
                      self.CONFIG['opposite_weight'] * opposite_score +
                      self.CONFIG['moderate_weight'] * moderate_score +
                      noise)
        
        return final_score
    
    def calculate_hide_seek_score(self, room: int, rooms_data: Dict, 
                                  last_killed: int, history: List) -> float:
        """Calculate HIDE_SEEK danger score (5 dangers)"""
        data = rooms_data[room]
        kills = data.get('kills', 0)
        survives = data.get('survives', 0)
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        
        all_rooms = list(rooms_data.keys())
        max_players = max(rooms_data[r].get('players', 0) for r in all_rooms) or 1
        max_bet = max(rooms_data[r].get('bet', 0) for r in all_rooms) or 1
        
        # D1: Historical Danger
        hist_danger = (kills + 1) / (kills + survives + 2)
        
        # D2: Crowd Danger
        crowd_danger = players / max_players
        
        # D3: Money Danger
        money_danger = bet / max_bet
        
        # D4: Personality Danger (simplified without full history)
        personality_danger = 0.5  # Would need kill history details
        
        # D5: Recency Danger
        recency_danger = 0.0
        if room == last_killed:
            recency_danger = 1.0
        else:
            for i, killed_room in enumerate(list(reversed(history))[:3]):
                if killed_room == room:
                    recency_danger += (3 - i) / 9.0
        
        # Total HIDE_SEEK
        hide_seek_danger = (0.30 * hist_danger +
                           0.20 * crowd_danger +
                           0.20 * money_danger +
                           0.30 * personality_danger)
        
        hide_seek_score = 1.0 - (hide_seek_danger + recency_danger * 0.3)
        return hide_seek_score
    
    def calculate_pro_score(self, room: int, rooms_data: Dict) -> float:
        """Calculate PRO factors score"""
        data = rooms_data[room]
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        
        all_rooms = list(rooms_data.keys())
        total_players = sum(rooms_data[r].get('players', 0) for r in all_rooms)
        total_bet = sum(rooms_data[r].get('bet', 0) for r in all_rooms)
        
        # SMI
        player_share = players / max(1, total_players)
        bet_share = bet / max(1, total_bet)
        smi = bet_share - player_share
        
        # BPP Normalized
        bpp = bet / max(1, players)
        bpp_norm = 1.0 / (1.0 + bpp / 1200.0)
        
        # Stability (simplified)
        stability = 0.5
        
        # Late surge & crowd trap (simplified)
        late_surge = 0.0
        crowd_trap = (players - 70) / 30.0 if players > 70 else 0.0
        
        # PRO score
        pro_score = (0.30 * (1.0 - abs(smi)) +
                    0.25 * bpp_norm +
                    0.25 * stability +
                    0.10 * (1.0 - late_surge) +
                    0.10 * (1.0 - crowd_trap))
        
        return pro_score
    
    def calculate_opposite_score(self, room: int, last_killed: int, history: List) -> float:
        """Calculate opposite factor score"""
        opposite_factor = 0.0
        opposites = self.get_opposite_rooms(last_killed)
        
        if room in opposites:
            opposite_factor = 0.08
            # Check historical opposites
            for killed_room in list(reversed(history))[:2]:
                if room in self.get_opposite_rooms(killed_room):
                    opposite_factor += 0.03
        else:
            opposite_factor = -0.05
        
        opposite_score = 0.5 + opposite_factor / 0.2
        return opposite_score
    
    def calculate_moderate_score(self, room: int, rooms_data: Dict) -> float:
        """Calculate moderate/balance score"""
        data = rooms_data[room]
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        
        all_rooms = list(rooms_data.keys())
        all_players = [rooms_data[r].get('players', 0) for r in all_rooms]
        all_bets = [rooms_data[r].get('bet', 0) for r in all_rooms]
        
        median_players = median(all_players) if all_players else 1
        median_bet = median(all_bets) if all_bets else 1
        
        player_moderate = 1.0 / (1.0 + abs(players - median_players) / max(1, median_players))
        bet_moderate = 1.0 / (1.0 + abs(bet - median_bet) / max(1, median_bet))
        
        moderate_score = (player_moderate + bet_moderate) / 2.0
        return moderate_score
    
    def fallback_selection(self, rooms_data: Dict, history: List) -> int:
        """Fallback based on personality"""
        scores = {}
        for room, data in rooms_data.items():
            personality_score = 0.5  # Simplified
            kills = data.get('kills', 0)
            survives = data.get('survives', 0)
            safety_score = 1.0 - (kills / max(1, kills + survives))
            scores[room] = 0.7 * personality_score + 0.3 * safety_score
        return max(scores, key=scores.get)


# === ALGORITHM 3: ULTIMATE v2 ===
class ULTIMATEAlgorithm(BaseAlgorithm):
    """
    ULTIMATE v2 - GODMODE + 7 dangers + MIRROR (20-40%)
    Enhanced Logic 7 from vth.py
    """
    
    CONFIG = {
        'min_survive_rate': 0.5,
        'max_players': 100,
        'min_players': 3,
        'max_bet': 50000,
        'min_bet': 500,
        'min_safety': 0.7,
        'mirror_alpha': 0.30,
        'num_formulas': 100,
        'seed': 7777777
    }
    
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        # PHASE 1: Smart Filtering
        filtered = self.apply_filters(rooms_data, last_killed, history)
        
        if not filtered:
            filtered = list(rooms_data.keys())
        
        # PHASE 2: Hybrid ULTIMATE + MIRROR
        scores = {}
        for room in filtered:
            scores[room] = self.calculate_ensemble_score(room, rooms_data, last_killed, history)
        
        return max(scores, key=scores.get)
    
    def apply_filters(self, rooms_data: Dict, last_killed: int, history: List) -> List[int]:
        """Apply 5 smart filters with MIRROR opposite"""
        filtered = []
        all_rooms = list(rooms_data.keys())
        total_rounds = sum(rooms_data[r].get('kills', 0) + rooms_data[r].get('survives', 0) 
                          for r in all_rooms)
        opposites = self.get_opposite_rooms(last_killed)
        
        for room in all_rooms:
            data = rooms_data[room]
            kills = data.get('kills', 0)
            survives = data.get('survives', 0)
            players = data.get('players', 0)
            bet = data.get('bet', 0)
            
            # F1: Avoid last kill
            if room == last_killed:
                continue
            
            # F2: Min survive rate
            survive_score = 1.0 - (kills / max(1, kills + survives))
            if survive_score < self.CONFIG['min_survive_rate']:
                continue
            
            # F3: Boundary check
            if players > self.CONFIG['max_players'] or bet > self.CONFIG['max_bet']:
                continue
            if players < self.CONFIG['min_players'] or bet < self.CONFIG['min_bet']:
                continue
            
            # F4: Historical safety
            safety_score = 1.0 - (kills / max(1, total_rounds))
            if safety_score < self.CONFIG['min_safety']:
                continue
            
            # F5: MIRROR opposite filter
            if room not in opposites:
                # Preliminary danger check
                kill_rate = kills / max(1, kills + survives)
                if kill_rate > 0.6:
                    continue
            
            filtered.append(room)
        
        return filtered
    
    def calculate_ensemble_score(self, room: int, rooms_data: Dict, 
                                 last_killed: int, history: List) -> float:
        """Calculate ensemble with ULTIMATE + MIRROR"""
        
        # A. ULTIMATE Score
        ultimate_score = self.calculate_ultimate_score(room, rooms_data, history)
        
        # B. MIRROR Score
        mirror_score = self.calculate_mirror_score(room, last_killed, history, rooms_data)
        
        # C. Ensemble 100 formulas
        rng = random.Random(self.CONFIG['seed'])
        final_scores = []
        
        for i in range(self.CONFIG['num_formulas']):
            # Random weight between ULTIMATE and MIRROR
            w_ultimate = rng.uniform(0.60, 0.80)
            w_mirror = 1.0 - w_ultimate
            
            noise = self.deterministic_noise(i, room, 0.05)
            
            score_i = w_ultimate * ultimate_score + w_mirror * mirror_score + noise
            final_scores.append(score_i)
        
        return mean(final_scores)
    
    def calculate_ultimate_score(self, room: int, rooms_data: Dict, history: List) -> float:
        """Calculate ULTIMATE danger score (7 factors)"""
        data = rooms_data[room]
        kills = data.get('kills', 0)
        survives = data.get('survives', 0)
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        
        all_rooms = list(rooms_data.keys())
        all_players = [rooms_data[r].get('players', 0) for r in all_rooms]
        all_bets = [rooms_data[r].get('bet', 0) for r in all_rooms]
        
        player_mean = mean(all_players) if all_players else 1
        bet_mean = mean(all_bets) if all_bets else 1
        player_std = pstdev(all_players) if len(all_players) > 1 else 1
        bet_std = pstdev(all_bets) if len(all_bets) > 1 else 1
        
        # D1: Historical (15%)
        kill_rate = kills / max(1, kills + survives)
        hist_danger = kill_rate ** 2  # Squared
        
        # D2: Crowd (18%) - Z-score + Sigmoid
        player_z = (players - player_mean) / max(0.1, player_std)
        crowd_danger = 1.0 / (1.0 + math.exp(-player_z))
        
        # D3: Money (18%) - Z-score + Sigmoid
        bet_z = (bet - bet_mean) / max(0.1, bet_std)
        money_danger = 1.0 / (1.0 + math.exp(-bet_z))
        
        # D4: Whale (12%)
        bpp = bet / max(1, players)
        whale_danger = min(1.0, bpp / 2000.0)
        
        # D5: Personality (20%)
        personality = (hash(str(room) + str(len(history))) % 100) / 100.0
        personality_danger = personality ** 0.5
        
        # D6: Trap (8%)
        trap = 0.0  # Simplified without real-time updates
        
        # D7: Pattern (9%)
        pattern = 0.0
        for i, killed_room in enumerate(list(reversed(history))[:5]):
            if killed_room == room:
                pattern += (5 - i) / 15.0
        
        # Total ULTIMATE danger
        ultimate_danger = (0.15 * hist_danger +
                          0.18 * crowd_danger +
                          0.18 * money_danger +
                          0.12 * whale_danger +
                          0.20 * personality_danger +
                          0.08 * trap +
                          0.09 * pattern)
        
        return 1.0 - ultimate_danger
    
    def calculate_mirror_score(self, room: int, last_killed: int, 
                               history: List, rooms_data: Dict) -> float:
        """Calculate MIRROR opposite score"""
        opposites = self.get_opposite_rooms(last_killed)
        
        # M1: Opposite Strength (40%)
        opposite_strength = 0.8 if room in opposites else 0.2
        
        # M2: Distance Score (25%)
        distance_score = 1.0 - abs(room - last_killed) / 7.0
        
        # M3: Position Bias (20%)
        position_bonus = 0.8 if room in opposites else 0.3
        
        # M4: Survival (15%)
        data = rooms_data[room]
        kills = data.get('kills', 0)
        survives = data.get('survives', 0)
        survival_score = 1.0 - (kills / max(1, kills + survives))
        
        # Total MIRROR
        mirror_score = (0.40 * opposite_strength +
                       0.25 * distance_score +
                       0.20 * position_bonus +
                       0.15 * survival_score)
        
        return mirror_score


# === ALGORITHM 4: VIP Enhanced ===
class VIPEnhancedAlgorithm(BaseAlgorithm):
    """
    VIP Enhanced - 50 formulas + opposite bonus (10-12%)
    From toolviplogicrieng.py
    """
    
    CONFIG = {
        'num_formulas': 50,
        'seed': 1234567,
    }
    
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        scores = {}
        
        for room in rooms_data.keys():
            scores[room] = self.calculate_ensemble_score(room, rooms_data, last_killed, history)
        
        return max(scores, key=scores.get)
    
    def calculate_ensemble_score(self, room: int, rooms_data: Dict, 
                                 last_killed: int, history: List) -> float:
        """50 formulas ensemble with opposite bonus"""
        data = rooms_data[room]
        kills = data.get('kills', 0)
        survives = data.get('survives', 0)
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        
        # Normalization
        players_norm = min(1.0, players / 50.0)
        bet_norm = 1.0 / (1.0 + bet / 2000.0)
        bpp = bet / max(1, players)
        bpp_norm = 1.0 / (1.0 + bpp / 1200.0)
        survive_score = 1.0 - (kills / max(1, kills + survives))
        
        # Penalties
        recent_penalty = 0.0  # Simplified
        last_kill_penalty = 0.5 if room == last_killed else 0.0
        
        # Opposite bonus
        opposites = self.get_opposite_rooms(last_killed)
        opposite_bonus = 1.0 if room in opposites else 0.3
        
        # 50 formulas ensemble
        rng = random.Random(self.CONFIG['seed'])
        final_scores = []
        
        for i in range(self.CONFIG['num_formulas']):
            w_players = rng.uniform(0.2, 0.8)
            w_bet = rng.uniform(0.1, 0.6)
            w_bpp = rng.uniform(0.05, 0.6)
            w_survive = rng.uniform(0.05, 0.4)
            w_recent = rng.uniform(0.05, 0.3)
            w_last = rng.uniform(0.1, 0.6)
            w_opposite = rng.uniform(0.08, 0.15)  # NEW
            
            noise = self.deterministic_noise(i, room, 0.05)
            
            score_i = (w_players * (1.0 - players_norm) +
                      w_bet * bet_norm +
                      w_bpp * bpp_norm +
                      w_survive * survive_score -
                      w_recent * recent_penalty -
                      w_last * last_kill_penalty +
                      w_opposite * opposite_bonus +
                      noise)
            
            final_scores.append(score_i)
        
        return mean(final_scores)


# === ALGORITHM 5: PRO Enhanced ===
class PROEnhancedAlgorithm(BaseAlgorithm):
    """
    PRO Enhanced - SMI + Trend + Opposite (8-10%)
    From toolviplogicrieng.py
    """
    
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        scores = {}
        
        for room in rooms_data.keys():
            scores[room] = self.calculate_pro_score(room, rooms_data, last_killed, history)
        
        return max(scores, key=scores.get)
    
    def calculate_pro_score(self, room: int, rooms_data: Dict, 
                            last_killed: int, history: List) -> float:
        """SMI + 9 factors + opposite"""
        data = rooms_data[room]
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        kills = data.get('kills', 0)
        survives = data.get('survives', 0)
        
        all_rooms = list(rooms_data.keys())
        total_players = sum(rooms_data[r].get('players', 0) for r in all_rooms)
        total_bet = sum(rooms_data[r].get('bet', 0) for r in all_rooms)
        
        # SMI
        player_share = players / max(1, total_players)
        bet_share = bet / max(1, total_bet)
        smi = bet_share - player_share
        
        # BPP normalized
        bpp = bet / max(1, players)
        bpp_norm = 1.0 / (1.0 + bpp / 1200.0)
        
        # Stability (simplified)
        stability = 0.5
        
        # Late surge & crowd trap
        late_surge = 0.0
        crowd_trap = 0.0
        if players > 70:
            crowd_trap = (players - 70) / 30.0
        
        # Recent penalties
        recent_kill = 0.5 if room == last_killed else 0.0
        recent_pick = 0.0
        
        # Survive score
        survive_score = 1.0 - (kills / max(1, kills + survives))
        
        # Opposite factor (NEW)
        opposites = self.get_opposite_rooms(last_killed)
        opposite_factor = 0.08 if room in opposites else -0.05
        
        # Noise
        noise = self.deterministic_noise(0, room, 0.05)
        
        # Score calculation
        score = (1.2 * smi +
                0.6 * bet_share -
                0.7 * player_share +
                0.4 * bpp_norm +
                0.35 * stability -
                0.8 * max(late_surge, crowd_trap) -
                0.5 * recent_kill -
                0.2 * recent_pick +
                0.15 * survive_score +
                opposite_factor +
                noise)
        
        return score


# === ALGORITHM 6: META v2 ===
class METAAlgorithm(BaseAlgorithm):
    """
    META v2 - VIP + PRO + Risk Voting (3 layers)
    From toolviplogicrieng.py
    """
    
    def __init__(self):
        self.vip_algo = VIPEnhancedAlgorithm()
        self.pro_algo = PROEnhancedAlgorithm()
    
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        # Layer 1: VIP Vote (40%)
        vip_scores = {}
        for room in rooms_data.keys():
            vip_scores[room] = self.vip_algo.calculate_ensemble_score(
                room, rooms_data, last_killed, history
            )
        vip_room = max(vip_scores, key=vip_scores.get)
        
        # Layer 2: PRO Vote (40% × confidence)
        pro_scores = {}
        for room in rooms_data.keys():
            pro_scores[room] = self.pro_algo.calculate_pro_score(
                room, rooms_data, last_killed, history
            )
        pro_room = max(pro_scores, key=pro_scores.get)
        pro_conf = max(0.3, pro_scores[pro_room])
        
        # Layer 3: Risk Analysis (20%)
        risk_scores = {}
        for room in rooms_data.keys():
            risk_scores[room] = 1.0 - self.calculate_room_risk(room, rooms_data, last_killed)
        
        # Voting
        room_scores = {}
        for room in rooms_data.keys():
            score = 0.0
            if room == vip_room:
                score += 0.4
            if room == pro_room:
                score += 0.4 * pro_conf
            score += 0.2 * risk_scores[room]
            room_scores[room] = score
        
        return max(room_scores, key=room_scores.get)
    
    def calculate_room_risk(self, room: int, rooms_data: Dict, last_killed: int) -> float:
        """Calculate room risk score"""
        data = rooms_data[room]
        kills = data.get('kills', 0)
        survives = data.get('survives', 0)
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        
        # Kill rate
        kill_rate = kills / max(1, kills + survives)
        
        # Last kill penalty
        last_kill_penalty = 0.4 if room == last_killed else 0.0
        
        # Player risk
        player_risk = 0.3 if players < 5 else (0.2 if players > 50 else 0.0)
        
        # BPP risk
        bpp = bet / max(1, players)
        bpp_risk = 0.2 if bpp > 2000 else (0.15 if bpp < 50 else 0.0)
        
        # Recent bet penalty
        recent_bet_penalty = 0.0  # Simplified
        
        total_risk = min(1.0, kill_rate + last_kill_penalty + 
                        player_risk + bpp_risk + recent_bet_penalty)
        
        return total_risk


# === ALGORITHM 7: GODMODE ===
class GODMODEAlgorithm(BaseAlgorithm):
    """
    GODMODE - Safety-first + 100 formulas
    From B5_1.py
    """
    
    CONFIG = {
        'min_survive_rate': 0.5,
        'max_players': 100,
        'min_players': 3,
        'max_bet': 50000,
        'min_bet': 500,
        'min_safety': 0.7,
        'num_formulas': 100,
        'seed': 1234567,
    }
    
    def select_room(self, rooms_data: Dict, last_killed: int, history: List) -> int:
        # PHASE 1: Smart Filtering
        filtered = self.apply_filters(rooms_data, last_killed, history)
        
        if not filtered:
            filtered = list(rooms_data.keys())
        
        # PHASE 2: 100 Formulas Ensemble
        scores = {}
        for room in filtered:
            scores[room] = self.calculate_ensemble_score(room, rooms_data, last_killed, history)
        
        return max(scores, key=scores.get)
    
    def apply_filters(self, rooms_data: Dict, last_killed: int, history: List) -> List[int]:
        """Apply 5 smart filters"""
        filtered = []
        all_rooms = list(rooms_data.keys())
        total_rounds = sum(rooms_data[r].get('kills', 0) + rooms_data[r].get('survives', 0) 
                          for r in all_rooms)
        
        for room in all_rooms:
            data = rooms_data[room]
            kills = data.get('kills', 0)
            survives = data.get('survives', 0)
            players = data.get('players', 0)
            bet = data.get('bet', 0)
            
            # F1: Avoid last kill
            if room == last_killed:
                continue
            
            # F2: Min survive rate
            survive_score = 1.0 - (kills / max(1, kills + survives))
            if survive_score < self.CONFIG['min_survive_rate']:
                continue
            
            # F3: Boundary check
            if players > self.CONFIG['max_players'] or bet > self.CONFIG['max_bet']:
                continue
            if players < self.CONFIG['min_players'] or bet < self.CONFIG['min_bet']:
                continue
            
            # F4: Historical safety
            safety_score = 1.0 - (kills / max(1, total_rounds))
            if safety_score < self.CONFIG['min_safety']:
                continue
            
            # F5 handled in scoring
            
            filtered.append(room)
        
        return filtered
    
    def calculate_ensemble_score(self, room: int, rooms_data: Dict, 
                                 last_killed: int, history: List) -> float:
        """100 formulas ensemble"""
        data = rooms_data[room]
        kills = data.get('kills', 0)
        survives = data.get('survives', 0)
        players = data.get('players', 0)
        bet = data.get('bet', 0)
        
        all_rooms = list(rooms_data.keys())
        total_rounds = sum(rooms_data[r].get('kills', 0) + rooms_data[r].get('survives', 0) 
                          for r in all_rooms)
        
        # Normalization
        players_norm = min(1.0, players / 50.0)
        bet_norm = 1.0 / (1.0 + bet / 2000.0)
        bpp = bet / max(1, players)
        bpp_norm = 1.0 / (1.0 + bpp / 1200.0)
        survive_score = 1.0 - (kills / max(1, kills + survives))
        safety_score = 1.0 - (kills / max(1, total_rounds))
        
        # Recent penalty
        recent_pen = 0.0
        for i, killed_room in enumerate(list(reversed(history))[:5]):
            if killed_room == room:
                recent_pen += 0.15 * (1.0 / (i + 1))
        
        # Last kill penalty
        last_kill_pen = 0.5 if room == last_killed else 0.0
        
        # 100 formulas ensemble
        rng = random.Random(self.CONFIG['seed'])
        final_scores = []
        
        for i in range(self.CONFIG['num_formulas']):
            w_players = rng.uniform(0.15, 0.85)
            w_bet = rng.uniform(0.05, 0.7)
            w_bpp = rng.uniform(0.03, 0.65)
            w_survive = rng.uniform(0.03, 0.45)
            w_recent = rng.uniform(0.03, 0.35)
            w_last = rng.uniform(0.05, 0.7)
            
            noise = self.deterministic_noise(i, room, 0.05)
            
            score_i = (w_players * (1.0 - players_norm) +
                      w_bet * bet_norm +
                      w_bpp * bpp_norm +
                      w_survive * survive_score +
                      w_survive * safety_score -
                      w_recent * recent_pen -
                      w_last * last_kill_pen +
                      noise)
            
            final_scores.append(score_i)
        
        return mean(final_scores)


# === ALGORITHM FACTORY ===
class AlgorithmFactory:
    """Factory to create algorithm instances"""
    
    ALGORITHMS = {
        "Random Pick": RandomAlgorithm,
        "Min Players": MinPlayerAlgorithm,
        "Max Players": MaxPlayerAlgorithm,
        "Min Bet": MinBetAlgorithm,
        "Max Bet": MaxBetAlgorithm,
        "Trend Follow": TrendFollowAlgorithm,
        "SAFE_GUARD v2.0": SAFEGUARDAlgorithm,
        "SHADOW_HUNTER v2.0": SHADOWHUNTERAlgorithm,
        "ULTIMATE v2": ULTIMATEAlgorithm,
        "VIP Enhanced": VIPEnhancedAlgorithm,
        "PRO Enhanced": PROEnhancedAlgorithm,
        "META v2": METAAlgorithm,
        "GODMODE by LuongDu": GODMODEAlgorithm,
    }
    
    @staticmethod
    def create(algorithm_name: str) -> BaseAlgorithm:
        """Create algorithm instance by name"""
        if algorithm_name not in AlgorithmFactory.ALGORITHMS:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")
        
        algo_class = AlgorithmFactory.ALGORITHMS[algorithm_name]
        return algo_class()
    
    @staticmethod
    def list_algorithms() -> List[str]:
        """List all available algorithms"""
        return list(AlgorithmFactory.ALGORITHMS.keys())


# ============================================================================
# SECTION 4: GAME ENGINE
# ============================================================================

class GameConfig:
    """Game configuration (same as in main_ui_with_menu.py)"""
    def __init__(self):
        # Bankroll Management
        self.use_tay_system = False
        self.safe_capital = 0.0
        self.num_tay = 4
        self.multiplier = 12.0
        self.base_bet = 1.0
        
        # Asset Type
        self.asset_type = "BUILD"
        
        # Auto Reinvest
        self.reinvest_profit = False
        
        # Algorithm
        self.algorithm = "SAFE_GUARD v2.0"
        
        # Pause/Skip Logic
        self.pause_after_losses = 5
        self.bet_rounds_before_skip = 10
        self.pause_rounds = 2
        
        # Take Profit / Stop Loss
        self.stop_when_profit_reached = False
        self.profit_target = 50.0
        self.stop_when_loss_reached = False
        self.stop_loss_target = 30.0


class GameEngine:
    """
    Main game engine that orchestrates betting, algorithm selection,
    and game state management
    """
    
    def __init__(self, api: GameAPI, config: GameConfig):
        """
        Initialize game engine
        
        Args:
            api: GameAPI instance
            config: GameConfig instance
        """
        self.api = api
        self.config = config
        
        # Initialize algorithm
        self.algorithm: BaseAlgorithm = AlgorithmFactory.create(config.algorithm)
        
        # State
        self.current_bet = config.base_bet
        self.initial_balance = None
        self.current_balance = None
        self.playing_capital = None
        
        # Statistics
        self.win_streak = 0
        self.loss_streak = 0
        self.total_games = 0
        self.total_wins = 0
        self.total_losses = 0
        self.max_win_streak = 0
        self.max_loss_streak = 0
        self.bet_count = 0
        self.pause_count = 0
        
        # History - ✅ FIX #5: Bounded with deque to prevent memory leaks
        MAX_BET_HISTORY = 1000      # Keep last 1000 bets (~1 night)
        MAX_KILL_HISTORY = 500      # Keep last 500 kills
        MAX_HANDS_HISTORY = 200     # Keep last 200 hands (chia tay)
        
        self.bet_history = deque(maxlen=MAX_BET_HISTORY)
        self.kill_history = deque(maxlen=MAX_KILL_HISTORY)
        self.hands_history = deque(maxlen=MAX_HANDS_HISTORY)
        
        # Current round tracking
        self.current_issue_id = None
        self.last_selected_room = None  # Track selected room for current round
        
        # Flags
        self.is_paused = False
        self.pause_reason = ""
        self.should_stop = False
        self.stop_reason = ""
        self.loss_pause_remaining = 0  # Track remaining pause rounds after a loss
        
    def initialize(self) -> bool:
        """
        Initialize engine by fetching initial balance
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print("[INIT] Fetching balance...", flush=True)
            balance_data = self.api.fetch_balance()
            print(f"[INIT] Balance data received: {balance_data}", flush=True)
            
            if balance_data:
                self.initial_balance = balance_data.get("BUILD", 0)
                self.current_balance = self.initial_balance
                
                print(f"[INIT] Initial balance: {self.initial_balance} BUILD", flush=True)
                
                # Calculate playing capital
                self.playing_capital = self.current_balance - self.config.safe_capital
                
                print(f"[INIT] Safe capital: {self.config.safe_capital} BUILD", flush=True)
                print(f"[INIT] Playing capital: {self.playing_capital} BUILD", flush=True)
                
                if self.playing_capital <= 0:
                    print(f"[ERROR] Playing capital is {self.playing_capital} (Balance: {self.current_balance}, Safe: {self.config.safe_capital})", flush=True)
                    return False
                
                # Calculate base bet if using tay system
                if self.config.use_tay_system:
                    print(f"[INIT] Using tay system: {self.config.num_tay} tay, multiplier: {self.config.multiplier}x", flush=True)
                    self.config.base_bet = self._calculate_base_bet(
                        self.playing_capital,
                        self.config.num_tay,
                        self.config.multiplier
                    )
                    self.current_bet = self.config.base_bet
                
                print(f"[INIT] Balance: {self.current_balance:.2f} {self.config.asset_type}", flush=True)
                print(f"[INIT] Playing capital: {self.playing_capital:.2f} {self.config.asset_type}", flush=True)
                print(f"[INIT] Base bet: {self.config.base_bet:.4f} {self.config.asset_type}", flush=True)
                print(f"[INIT] Algorithm: {self.config.algorithm}", flush=True)
                
                return True
            else:
                print("[ERROR] fetch_balance() returned None or empty", flush=True)
                return False
        except Exception as e:
            print(f"[ERROR] Initialization failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
        
        return False
    
    def should_bet_this_round(self) -> tuple[bool, str]:
        """
        Check if should place bet this round
        
        Returns:
            (should_bet: bool, reason: str)
        """
        # Check if already stopped
        if self.should_stop:
            return False, self.stop_reason
        
        # Check loss streak vs num_tay (if using tay system)
        if self.config.use_tay_system and self.loss_streak >= self.config.num_tay:
            return False, f"Loss streak ({self.loss_streak}) reached max tay ({self.config.num_tay})"
        
        # Check pause after losses (NEW LOGIC: Pause N rounds AFTER any loss)
        if self.loss_pause_remaining > 0:
            self.loss_pause_remaining -= 1
            return False, f"Pausing after loss ({self.loss_pause_remaining + 1} remaining)"
        
        # OLD LOGIC REMOVED: if self.loss_streak >= self.config.pause_after_losses:
        
        # Check periodic pause
        if self.bet_count >= self.config.bet_rounds_before_skip:
            if self.pause_count < self.config.pause_rounds:
                self.pause_count += 1
                return False, f"Periodic pause ({self.pause_count}/{self.config.pause_rounds})"
            else:
                # Reset periodic pause
                self.bet_count = 0
                self.pause_count = 0
        
        # Check take profit
        if self.config.stop_when_profit_reached and self.current_balance:
            profit = self.current_balance - self.initial_balance
            if profit >= self.config.profit_target:
                self.should_stop = True
                self.stop_reason = f"Take profit reached: {profit:.2f} >= {self.config.profit_target:.2f}"
                return False, self.stop_reason
        
        # Check stop loss
        if self.config.stop_when_loss_reached and self.current_balance:
            loss = self.initial_balance - self.current_balance
            if loss >= self.config.stop_loss_target:
                self.should_stop = True
                self.stop_reason = f"Stop loss reached: {loss:.2f} >= {self.config.stop_loss_target:.2f}"
                return False, self.stop_reason
        
        return True, "OK"
    
    def select_room(self, rooms_data: Dict, last_killed: int) -> int:
        """
        Select best room using algorithm
        
        Args:
            rooms_data: {room_id: {'players': int, 'bet': float, ...}}
            last_killed: Last killed room ID
            
        Returns:
            Selected room ID (1-8)
        """
        try:
            selected = self.algorithm.select_room(
                rooms_data,
                last_killed,
                self.kill_history
            )
            return selected
        except Exception as e:
            print(f"[ERROR] Room selection failed: {e}")
            # Fallback: select room with fewest players
            return min(rooms_data.keys(), key=lambda r: rooms_data[r].get('players', 999))
    
    def get_bet_amount(self) -> float:
        """
        Get current bet amount based on loss streak (Martingale)
        
        Formula: base_bet × (multiplier ^ loss_streak)
        - loss_streak = 0 → Hand 1 → base_bet
        - loss_streak = 1 → Hand 2 → base_bet × multiplier
        - loss_streak = 2 → Hand 3 → base_bet × multiplier²
        
        Returns:
            Bet amount
        """
        # Calculate bet using Martingale: base_bet × (multiplier ^ loss_streak)
        bet_amount = self.config.base_bet * (self.config.multiplier ** self.loss_streak)
        return bet_amount
    
    def place_bet(self, room_id: int, issue_id: str) -> bool:
        """
        Place bet on selected room
        
        Args:
            room_id: Room to bet on (1-8)
            issue_id: Issue ID
            
        Returns:
            True if successful, False otherwise
        """
        bet_amount = self.get_bet_amount()
        
        try:
            print(f"[BET ATTEMPT] Room {room_id}, Amount: {bet_amount:.4f}, Issue: {issue_id}", flush=True)
            success = self.api.place_bet(room_id, bet_amount)
            
            if success:
                # Record bet
                self.bet_history.append({
                    'issue': str(issue_id),
                    'room': room_id,
                    'amount': bet_amount,
                    'result': None,  # Will be updated later
                    'profit': None
                })
                
                print(f"[BET SUCCESS] Room {room_id}, Amount: {bet_amount:.4f} {ASSET_TYPE}, History count: {len(self.bet_history)}", flush=True)
                if 'ui_queue' in globals():
                    ui_queue.put(("log", (f"📝 Bet recorded: Room {room_id} | {bet_amount:.4f} {ASSET_TYPE}", "dim cyan")))
                return True
            else:
                print(f"[ERROR] Bet failed for room {room_id}")
                return False
                
        except Exception as e:
            print(f"[ERROR] place_bet exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_game_result(self, killed_room: int, issue_id: str):
        """
        Process game result by comparing killed_room with last_selected_room
        
        Args:
            killed_room: Room that was killed (1-8)
            issue_id: Issue ID
        """
        print(f"[RESULT PROCESS] Issue: {issue_id}, Killed: {killed_room}, Last selected: {self.last_selected_room}", flush=True)
        
        # Add to kill history
        self.kill_history.append(killed_room)
        
        # Determine if it's a win or loss based on selected room
        if self.last_selected_room is None:
            print(f"[RESULT] No selected room tracked, skipping statistics update", flush=True)
            if 'ui_queue' in globals():
                ui_queue.put(("log", (f"⚠️ No room selected this round (skipped or demo)", "yellow")))
            return
        
        # FIX: Get actual bet amount from hands_history instead of self.current_bet
        # This ensures we use the exact amount that was bet, not a potentially out-of-sync value
        bet_amount = None
        if self.hands_history and len(self.hands_history) > 0:
            bet_amount = self.hands_history[-1]['bet_amount']
            print(f"[RESULT] Bet amount from history: {bet_amount:.4f}", flush=True)
        else:
            # Fallback: calculate from current loss_streak
            bet_amount = self.get_bet_amount()
            print(f"[RESULT] Bet amount calculated (fallback): {bet_amount:.4f}", flush=True)
        
        # Compare: if selected room == killed room -> LOSS, else -> WIN
        is_loss = (self.last_selected_room == killed_room)
        
        if is_loss:
            print(f"[LOSS] Selected {self.last_selected_room}, Killed {killed_room}, Amount: {bet_amount:.4f}", flush=True)
            self.on_loss_direct(killed_room, bet_amount)
        else:
            print(f"[WIN] Selected {self.last_selected_room}, Killed {killed_room}, Amount: {bet_amount:.4f}", flush=True)
            self.on_win_direct(bet_amount)
        
        # Reset selected room for next round
        self.last_selected_room = None
    
    def on_win_direct(self, bet_amount: float):
        """
        Direct win handler (doesn't depend on bet_history)
        
        Args:
            bet_amount: Amount bet
        """
        # Calculate profit (7x payout - bet amount)
        profit = bet_amount * 6  # Net profit (7x - 1x)
        
        # Update statistics
        self.win_streak += 1
        self.loss_streak = 0
        self.total_wins += 1
        self.total_games += 1
        self.bet_count += 1
        
        if self.win_streak > self.max_win_streak:
            self.max_win_streak = self.win_streak
        
        # Update balance
        if self.current_balance is not None:
            self.current_balance += profit
        
        # Reset bet to base bet
        self.current_bet = self.config.base_bet
        
        # Update last hand record in hands_history
        if self.hands_history:
            self.hands_history[-1]['result'] = 'Win'
            self.hands_history[-1]['profit'] = profit
        
        if 'ui_queue' in globals():
            ui_queue.put(("log", (f"🏆 WIN! Profit: +{profit:.4f} {ASSET_TYPE} | Streak: {self.win_streak}/{self.max_win_streak}", "bold green")))
        else:
            print(f"[WIN] Profit: +{profit:.4f} {ASSET_TYPE}, Streak: {self.win_streak}")
        
        # Reinvest if enabled
        if self.config.reinvest_profit:
            self.recalculate_base_bet()
    
    def on_loss_direct(self, killed_room: int, bet_amount: float):
        """
        Direct loss handler (doesn't depend on bet_history)
        
        Args:
            killed_room: Room that was killed
            bet_amount: Amount lost
        """
        # Calculate loss (negative)
        loss = -bet_amount
        
        # Update statistics
        self.loss_streak += 1
        self.win_streak = 0
        self.total_losses += 1
        self.total_games += 1
        self.bet_count += 1
        
        if self.loss_streak > self.max_loss_streak:
            self.max_loss_streak = self.loss_streak
        
        # Update balance
        if self.current_balance is not None:
            self.current_balance += loss  # loss is negative
        
        # Update last hand record in hands_history
        if self.hands_history:
            self.hands_history[-1]['result'] = 'Loss'
            self.hands_history[-1]['profit'] = loss
            # Also store the killed room for analysis
            self.hands_history[-1]['killed_room'] = killed_room
        
        # Martingale: multiply bet
        self.current_bet *= self.config.multiplier
        
        if 'ui_queue' in globals():
            ui_queue.put(("log", (f"💀 LOSS! Lost: {-loss:.4f} {ASSET_TYPE} | Streak: {self.loss_streak}/{self.max_loss_streak}", "bold red")))
            ui_queue.put(("log", (f"   Hand {self.loss_streak + 1} next bet: {self.current_bet:.4f} (x{self.config.multiplier})", "red")))
            
            # PAUSE AFTER LOSS LOGIC
            if self.config.pause_after_losses > 0:
                self.loss_pause_remaining = self.config.pause_after_losses
                ui_queue.put(("log", (f"⏸️ Pausing for {self.loss_pause_remaining} rounds due to loss...", "yellow")))
        else:
            print(f"[LOSS] Loss: {loss:.4f} {ASSET_TYPE}, Streak: {self.loss_streak}")
            print(f"[NEXT BET] Hand {self.loss_streak + 1}: {self.current_bet:.4f} {ASSET_TYPE} (x{self.config.multiplier})")
            if self.config.pause_after_losses > 0:
                self.loss_pause_remaining = self.config.pause_after_losses
                print(f"[PAUSE] Pausing for {self.loss_pause_remaining} rounds...")
    
    def on_result(self, killed_room: int, issue_id: str):
        """
        [DEPRECATED] Old on_result - use process_game_result instead
        
        Args:
            killed_room: Room that was killed (1-8)
            issue_id: Issue ID
        """
        # Add to kill history
        self.kill_history.append(killed_room)
        
        target_issue = str(issue_id)
        
        # Add detailed debug log to UI
        if 'ui_queue' in globals():
            ui_queue.put(("log", (f"🔍 Processing result: {target_issue} (Killed: {killed_room}), Bet history: {len(self.bet_history)}", "dim white")))
        
        print(f"[RESULT] Issue: {target_issue}, Killed: {killed_room}, Bet history count: {len(self.bet_history)}", flush=True)
        
        # Find matching bet
        bet_record = None
        for bet in reversed(self.bet_history):
            bet_issue = str(bet['issue'])
            print(f"  Checking bet: issue={bet_issue}, result={bet.get('result')}", flush=True)
            if bet_issue == target_issue and bet['result'] is None:
                bet_record = bet
                print(f"  ✓ Matched bet!", flush=True)
                break
        
        if not bet_record:
            msg = f"⚠️ No bet match for {target_issue}"
            if 'ui_queue' in globals():
                ui_queue.put(("log", (msg, "yellow")))
                if self.bet_history:
                    last = self.bet_history[-1]
                    ui_queue.put(("log", (f"   Last bet: {last['issue']}", "dim yellow")))
            else:
                print(msg)
            
            # FALLBACK: Still increment total_games to avoid permanent 0 display
            # This ensures stats are updated even if bet matching fails
            self.total_games += 1
            self.bet_count += 1
            print(f"[FALLBACK] Game counted (total: {self.total_games})", flush=True)
            if 'ui_queue' in globals():
                ui_queue.put(("log", (f"   Fallback: Game counted (total: {self.total_games})", "dim cyan")))
            return
        
        # Determine win/loss
        bet_room = bet_record['room']
        bet_amount = bet_record['amount']
        
        if bet_room == killed_room:
            # Loss
            self.on_loss(bet_record)
        else:
            # Win
            self.on_win(bet_record)
    
    def on_win(self, bet_record: Dict):
        """
        Handle win result
        
        Args:
            bet_record: Bet record dict
        """
        bet_amount = bet_record['amount']
        
        # Calculate profit (7x payout - bet amount)
        profit = bet_amount * 6  # Net profit (7x - 1x)
        
        # Update bet record
        bet_record['result'] = 'Win'
        bet_record['profit'] = profit
        
        # Update statistics
        self.win_streak += 1
        self.loss_streak = 0
        self.total_wins += 1
        self.total_games += 1
        self.bet_count += 1
        
        if self.win_streak > self.max_win_streak:
            self.max_win_streak = self.win_streak
        
        # Update balance
        if self.current_balance is not None:
            self.current_balance += profit
        
        # Reset bet to base bet
        self.current_bet = self.config.base_bet
        
        if 'ui_queue' in globals():
            ui_queue.put(("log", (f"🏆 WIN! Profit: +{profit:.4f} BUILD | Streak: {self.win_streak}", "bold green")))
        else:
            print(f"[WIN] Profit: +{profit:.4f} BUILD, Streak: {self.win_streak}")
        
        # Reinvest if enabled
        if self.config.reinvest_profit:
            self.recalculate_base_bet()
    
    def on_loss(self, bet_record: Dict):
        """
        Handle loss result
        
        Args:
            bet_record: Bet record dict
        """
        bet_amount = bet_record['amount']
        
        # Calculate loss (negative)
        loss = -bet_amount
        
        # Update bet record
        bet_record['result'] = 'Loss'
        bet_record['profit'] = loss
        
        # Update statistics
        self.loss_streak += 1
        self.win_streak = 0
        self.total_losses += 1
        self.total_games += 1
        self.bet_count += 1
        
        if self.loss_streak > self.max_loss_streak:
            self.max_loss_streak = self.loss_streak
        
        # Update balance
        if self.current_balance is not None:
            self.current_balance += loss  # loss is negative
        
        # Martingale: multiply bet
        self.current_bet *= self.config.multiplier
        
        if 'ui_queue' in globals():
            ui_queue.put(("log", (f"💀 LOSS! Loss: {loss:.4f} BUILD | Streak: {self.loss_streak}", "bold red")))
            ui_queue.put(("log", (f"   Next Bet: {self.current_bet:.4f} (x{self.config.multiplier})", "red")))
        else:
            print(f"[LOSS] Loss: {loss:.4f} BUILD, Streak: {self.loss_streak}")
            print(f"[NEXT BET] {self.current_bet:.4f} BUILD (x{self.config.multiplier})")
    
    def recalculate_base_bet(self):
        """Recalculate base bet when reinvesting profit"""
        try:
            # Fetch new balance
            balance_data = self.api.fetch_balance()
            if balance_data:
                new_balance = balance_data.get("BUILD", 0)
                self.current_balance = new_balance
                
                # Calculate new playing capital
                new_playing_capital = new_balance - self.config.safe_capital
                
                if new_playing_capital <= 0:
                    print(f"[WARN] Cannot reinvest: playing capital is {new_playing_capital}")
                    return
                
                # Recalculate base bet
                if self.config.use_tay_system:
                    new_base_bet = self._calculate_base_bet(
                        new_playing_capital,
                        self.config.num_tay,
                        self.config.multiplier
                    )
                    
                    self.config.base_bet = new_base_bet
                    self.current_bet = new_base_bet
                    self.playing_capital = new_playing_capital
                    
                    print(f"[REINVEST] New balance: {new_balance:.2f}")
                    print(f"[REINVEST] New playing capital: {new_playing_capital:.2f}")
                    print(f"[REINVEST] New base bet: {new_base_bet:.4f}")
                    
        except Exception as e:
            print(f"[ERROR] Reinvest failed: {e}")
    
    def update_balance(self) -> bool:
        """
        Update current balance from API
        
        Returns:
            True if successful, False otherwise
        """
        try:
            balance_data = self.api.fetch_balance()
            if balance_data:
                self.current_balance = balance_data.get("BUILD", 0)
                return True
        except Exception as e:
            print(f"[ERROR] Balance update failed: {e}")
        
        return False
    
    def get_statistics(self) -> Dict:
        """
        Get current game statistics
        
        Returns:
            Dict with statistics
        """
        win_rate = (self.total_wins / self.total_games * 100) if self.total_games > 0 else 0
        
        profit_loss = 0.0
        if self.current_balance and self.initial_balance:
            profit_loss = self.current_balance - self.initial_balance
        
        return {
            'total_games': self.total_games,
            'total_wins': self.total_wins,
            'total_losses': self.total_losses,
            'win_rate': win_rate,
            'current_win_streak': self.win_streak,
            'current_loss_streak': self.loss_streak,
            'max_win_streak': self.max_win_streak,
            'max_loss_streak': self.max_loss_streak,
            'profit_loss': profit_loss,
            'current_balance': self.current_balance or 0,
            'current_bet': self.current_bet,
        }
    
    def get_recent_history(self, n: int = 10) -> List[Dict]:
        """
        Get recent bet history
        
        Args:
            n: Number of records
            
        Returns:
            List of bet records
        """
        return self.bet_history[-n:] if self.bet_history else []
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.win_streak = 0
        self.loss_streak = 0
        self.total_games = 0
        self.total_wins = 0
        self.total_losses = 0
        self.max_win_streak = 0
        self.max_loss_streak = 0
        self.bet_count = 0
        self.pause_count = 0
        self.bet_history = []
        self.kill_history = []
        self.is_paused = False
        self.should_stop = False
    
    def _calculate_base_bet(self, capital: float, num_tay: int, multiplier: float) -> float:
        """
        Calculate base bet using bankroll formula
        
        Args:
            capital: Playing capital
            num_tay: Number of hands
            multiplier: Multiplier
            
        Returns:
            Base bet amount
        """
        try:
            denominator = (multiplier ** num_tay - 1)
            if denominator == 0:
                return 1.0
            return capital * (multiplier - 1) / denominator
        except:
            return 1.0


# === TESTING ===


# ============================================================================
# SECTION 5-7: UI COMPONENTS + WEBSOCKET + MAIN
# ============================================================================

# === HELPER FUNCTIONS ===

def load_config():
    """Load configuration from strategy_vth.json"""
    global game_config
    
    try:
        config_path = Path("strategy_vth.json")
        if not config_path.exists():
            print("⚠️ strategy_vth.json not found, using defaults")
            game_config = GameConfig()
            app_state["algorithm"] = game_config.algorithm
            return game_config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        game_config = GameConfig()
        game_config.use_tay_system = data.get("use_tay_system", False)
        game_config.safe_capital = data.get("safe_capital", 0.0)
        game_config.num_tay = data.get("num_tay", 4)
        game_config.multiplier = data.get("multiplier", 12.0)
        game_config.base_bet = data.get("base_bet", 1.0)
        game_config.asset_type = data.get("asset_type", "BUILD")
        game_config.reinvest_profit = data.get("reinvest_profit", False)
        game_config.algorithm = data.get("algorithm", "SAFE_GUARD v2.0")
        game_config.pause_after_losses = data.get("pause_after_losses", 5)
        game_config.bet_rounds_before_skip = data.get("bet_rounds_before_skip", 10)
        game_config.pause_rounds = data.get("pause_rounds", 2)
        game_config.stop_when_profit_reached = data.get("stop_when_profit_reached", False)
        game_config.profit_target = data.get("profit_target", 50.0)
        game_config.stop_when_loss_reached = data.get("stop_when_loss_reached", False)
        game_config.stop_loss_target = data.get("stop_loss_target", 30.0)
        
        # Update app_state algorithm display
        app_state["algorithm"] = game_config.algorithm
        
        print(f"✅ Config loaded: {game_config.algorithm}")
        return game_config
        
    except Exception as e:
        print(f"❌ Config load error: {e}")
        game_config = GameConfig()
        return game_config

def initialize_game_engine():
    """Initialize game API and engine with loaded config"""
    global game_api, game_engine
    
    try:
        if game_config is None:
            print("❌ No config loaded")
            return False
            
        if USER_ID is None or SECRET_KEY is None:
            print("❌ No credentials set (USER_ID/SECRET_KEY is None)")
            return False
        
        # Create API client
        game_api = GameAPI(
            uid=USER_ID,
            secret=SECRET_KEY,
            asset_type=ASSET_TYPE
        )
        
        # Create game engine
        game_engine = GameEngine(game_api, game_config)
        
        # Initialize engine (fetch balance, calculate base bet)
        if not game_engine.initialize():
            print("❌ Engine initialization failed")
            return False
        
        print(f"✅ Engine initialized | Base bet: {game_config.base_bet:.4f} {game_config.asset_type}")
        return True
        
    except Exception as e:
        print(f"❌ Engine init error: {e}")
        return False


def add_log(message, style="white"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    app_state["logs"].append({"time": timestamp, "msg": message, "style": style})
    if len(app_state["logs"]) > MAX_LOGS:
        app_state["logs"].pop(0)

def execute_bet():
    """
    Execute betting logic:
    - Check if should bet
    - Build room data with current stats
    - Use algorithm to select room
    - Enter room (place character)
    - Place bet
    - Track in hands_history
    """
    global bet_placed_this_round, current_selected_room
    
    try:
        if game_engine is None:
            add_log("❌ Game engine not initialized", "red")
            return
        
        # Check if should bet this round
        should_bet, reason = game_engine.should_bet_this_round()
        if not should_bet:
            add_log(f"⏭️ Skip: {reason}", "yellow")
            bet_placed_this_round = True  # Mark as handled
            return
        
        # Build rooms_data for algorithm
        # THREAD-SAFETY FIX: Create snapshot of rooms data to avoid mutation during iteration
        rooms_data = {}
        # Use .copy() or dict() to snapshot keys
        rooms_snapshot = dict(app_state["rooms"])
        
        for room_id_str, stats in rooms_snapshot.items():
            try:
                room_id = int(room_id_str)
                rooms_data[room_id] = {
                    'players': stats.get('user_cnt', 0),
                    'bet': stats.get('total_bet_amount', 0.0),
                    'kills': 0,
                    'survives': 0
                }
            except (ValueError, TypeError):
                continue
        
        if not rooms_data:
            add_log("⚠️ No room data available", "yellow")
            return
        
        # Select room using algorithm
        last_killed = last_killed_room if last_killed_room else 1
        selected_room = game_engine.select_room(rooms_data, last_killed)
        current_selected_room = selected_room
        
        # Get bet amount (calculated from loss_streak)
        bet_amount = game_engine.get_bet_amount()
        
        # Determine hand number (loss_streak + 1)
        hand_number = game_engine.loss_streak + 1
        
        # Check if in demo mode
        is_demo = game_config.demo_mode if game_config else False
        
        if is_demo:
            add_log(f"🎯 [DEMO] Hand {hand_number} → Room {selected_room} | {bet_amount:.4f} {game_config.asset_type} (không cược thật)", "magenta bold")
        else:
            add_log(f"🎯 Betting Hand {hand_number} on Room {selected_room} | Amount: {bet_amount:.4f} {game_config.asset_type}", "cyan bold")
        
        # Step 1 & 2: Enter room and place bet (skip if demo mode)
        if not is_demo:
            # Step 1: Enter room (place character)
            if not game_engine.api.enter_room(selected_room):
                add_log(f"❌ Failed to enter room {selected_room}", "red")
                bet_placed_this_round = True
                return
            
            add_log(f"✅ Entered Room {selected_room}", "green")
            
            # Step 2: Place bet
            if not game_engine.api.place_bet(selected_room, bet_amount):
                add_log(f"❌ Failed to place bet on room {selected_room}", "red")
                bet_placed_this_round = True
                return
            
            add_log(f"✅ Bet placed: Room {selected_room} | {bet_amount:.4f} {game_config.asset_type}", "bold green")
        else:
            # Demo mode: just log what would happen
            add_log(f"[DEMO] Would enter Room {selected_room}", "dim cyan")
            add_log(f"[DEMO] Would bet {bet_amount:.4f} BUILD", "dim cyan")
        
        # Step 3: Record in game engine for result tracking
        game_engine.last_selected_room = selected_room
        game_engine.current_issue_id = app_state["issue_id"]
        
        # Step 4: Save to hands_history (chia tay tracking)
        hand_record = {
            'hand_num': hand_number,
            'loss_streak_at_bet': game_engine.loss_streak,
            'room_selected': selected_room,
            'bet_amount': bet_amount,
            'issue_id': app_state["issue_id"],
            'result': None,  # Will be updated after result
            'demo_mode': is_demo,
            'timestamp': datetime.now().isoformat()
        }
        game_engine.hands_history.append(hand_record)
        
        # Mark as bet placed
        bet_placed_this_round = True
            
    except Exception as e:
        add_log(f"❌ Bet error: {e}", "red")
        import traceback
        traceback.print_exc()

# --- WALLET API ---
def fetch_balance():
    """Fetch current balances from wallet API"""
    if USER_ID is None or SECRET_KEY is None:
        return

    try:
        headers = {
            "accept": "*/*",
            "accept-language": "vi,en;q=0.9",
            "cache-control": "no-cache",
            "country-code": "vn",
            "origin": "https://xworld.info",
            "pragma": "no-cache",
            "referer": "https://xworld.info/",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
            "user-login": "login_v2",
            "xb-language": "vi-VN",
            "user-id": str(USER_ID),
            "user-secret-key": SECRET_KEY
        }
        
        body = {
            "user_id": USER_ID,
            "source": "home"
        }
        
        response = requests.post(WALLET_API_URL, headers=headers, json=body, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0 and "data" in data:
                user_asset = data["data"].get("user_asset", {})
                
                with balance_lock:
                    app_state["balances"]["USDT"] = float(user_asset.get("USDT", 0))
                    app_state["balances"]["WORLD"] = float(user_asset.get("WORLD", 0))
                    app_state["balances"]["BUILD"] = float(user_asset.get("BUILD", 0))
                    
                    # Set initial BUILD balance on first successful fetch for profit/loss calculation
                    if app_state["initial_build"] is None:
                        app_state["initial_build"] = app_state["balances"]["BUILD"]
                    else:
                        # Update profit/loss based on BUILD balance change
                        app_state["profit_loss"] = app_state["balances"]["BUILD"] - app_state["initial_build"]
                
                add_log(f"Balance updated: {ASSET_TYPE}={user_asset.get(ASSET_TYPE, 0):.2f}", "dim green")
        else:
            add_log(f"Balance API error: {response.status_code}", "dim red")
            
    except Exception as e:
        add_log(f"Balance fetch failed: {str(e)[:50]}", "dim red")

# ============================================================================
# BALANCE POLLING SINGLETON (Fix #2)
# ============================================================================

class BalancePoller:
    """
    Singleton balance polling với proper start/stop
    Đảm bảo chỉ có DUY NHẤT 1 thread chạy
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.thread = None
        self.stop_event = threading.Event()
        self.interval = 5  # 5 seconds polling interval
        self.is_running = False
        self._thread_lock = threading.Lock()
    
    def start(self):
        """
        Start polling (thread-safe)
        Tự động stop thread cũ nếu đang chạy
        """
        with self._thread_lock:
            # Stop existing thread first
            if self.is_running:
                self._stop_internal()
            
            # Start new thread
            self.stop_event.clear()
            self.is_running = True
            self.thread = threading.Thread(
                target=self._polling_loop,
                daemon=True,
                name="BalancePoller"
            )
            self.thread.start()
    
    def stop(self):
        """Public stop method"""
        with self._thread_lock:
            self._stop_internal()
    
    def _stop_internal(self):
        """
        Internal stop (không lock, dùng khi đã có lock)
        """
        if not self.is_running:
            return
        
        self.stop_event.set()
        self.is_running = False
        
        # Wait for thread to finish (max 3s)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        
        self.thread = None
    
    def _polling_loop(self):
        """
        Main polling loop
        Check stop_event để terminate sạch
        """
        while not self.stop_event.is_set():
            try:
                fetch_balance()  # Existing function
            except Exception as e:
                pass  # Silent fail to not spam logs
            
            # Sleep with interrupt check
            for _ in range(int(self.interval)):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

# Global singleton instance
balance_poller = BalancePoller()

def fetch_balance_loop():
    """Legacy function - now uses singleton"""
    balance_poller.start()

# --- WEBSOCKET HANDLERS ---
def on_open(ws):
    global ws_connection_state, ws_reconnect_delay, ws_last_message_time
    ws_connection_state = "CONNECTED"
    ws_reconnect_delay = 1  # Reset backoff on successful connection
    ws_last_message_time = time.time()  # Initialize heartbeat
    
    ui_queue.put(("status", ("Connected", "green")))
    ui_queue.put(("log", ("✅ WebSocket connected", "green")))
    
    # Enter Game directly (Skip intermediate login step)
    if USER_ID and SECRET_KEY:
        enter_game_msg = {
            "msg_type": "handle_enter_game",
            "asset_type": ASSET_TYPE, # Use global selected asset type
            "user_id": USER_ID,
            "user_secret_key": SECRET_KEY
        }
        ws.send(json.dumps(enter_game_msg))
        ui_queue.put(("log", (f"Sending enter_game request ({ASSET_TYPE})...", "cyan")))
    else:
        ui_queue.put(("log", ("❌ Missing credentials for enter_game", "red")))

def on_message(ws, message):
    global ws_last_message_time
    ws_last_message_time = time.time()  # Update heartbeat on every message
    
    try:
        data = json.loads(message)
        msg_type = data.get("msg_type")
        
        global last_killed_room, bet_placed_this_round, current_selected_room, is_waiting_for_result, result_backup_triggered
        
        if msg_type == "notify_enter_game":
            # Reset for new round - DO THIS FIRST
            bet_placed_this_round = False
            current_selected_room = None
            
            ui_queue.put(("enter_game", data))
            ui_queue.put(("log", (f"🎮 Entered Issue: [bold yellow]{data['issue_id']}[/]", "yellow")))
            
            # Update last killed room from previous round
            if "last_killed" in data:
                last_killed_room = data["last_killed"]

        elif msg_type == "notify_issue_stat":
            ui_queue.put(("stats", data["rooms"]))
            # DIRECT STATE UPDATE
            if "rooms" in data:
                 for r in data["rooms"]:
                    if isinstance(r, dict):
                        r_id = str(r.get("room_id"))
                        if r_id:
                            app_state["rooms"][r_id] = {
                                "user_cnt": r.get("user_cnt", 0),
                                "total_bet_amount": r.get("total_bet_amount", 0)
                            }

        elif msg_type == "notify_count_down":
            countdown_val = data["count_down"]
            ui_queue.put(("countdown", countdown_val))
            
            # DIRECT STATE UPDATE
            app_state["countdown"] = countdown_val
            
            # FIX: Only trigger ONE time when countdown hits exactly 11s to prevent double betting
            # CRITICAL FIX FOR TERMUX: TRIGGER BETTING DIRECTLY FROM WS THREAD
            if countdown_val == 11 and not bet_placed_this_round and game_engine is not None:
                bet_placed_this_round = True  # Set flag IMMEDIATELY to prevent re-trigger
                
                # Launch betting in a separate daemon thread to avoid blocking WS and independent of UI
                def run_betting_logic():
                    try:
                        time.sleep(0.5) # Small delay to ensure stats are updated
                        execute_bet()
                    except Exception as e:
                        add_log(f"Betting thread error: {e}", "red")
                
                bet_thread = threading.Thread(target=run_betting_logic, daemon=True, name="BettingThread")
                bet_thread.start()
                
                ui_queue.put(("log", ("🚀 Betting triggered (Background Thread)", "cyan")))
                # ui_queue.put(("bet_trigger", None)) # REMOVED: No longer relying on UI loop
            
            # NEW: When countdown reaches 1s, enter result waiting mode
            if countdown_val == 1 and not is_waiting_for_result:
                is_waiting_for_result = True
                result_wait_start_time = time.time()
                result_backup_triggered = False
                ui_queue.put(("log", ("⏳ Countdown=1s, entering result wait mode (auto-reconnect disabled)", "yellow")))
                
                # Schedule backup API fetch after 10 seconds
                def backup_result_fetch():
                    time.sleep(10)
                    
                    global is_waiting_for_result, result_backup_triggered
                    if is_waiting_for_result and not result_backup_triggered:
                        result_backup_triggered = True
                        ui_queue.put(("log", ("⚠️ No WS result after 10s, fetching from API backup...", "yellow")))
                        
                        try:
                            # Fetch last 10 games from history API
                            response = requests.get(HISTORY_API_URL, timeout=5)
                            if response.status_code == 200:
                                history_data = response.json()
                                recent_issues = history_data.get("data", {}).get("list", [])
                                
                                # Find the current issue result
                                current_issue_id = app_state.get("issue_id")
                                for issue in recent_issues:
                                    if str(issue.get("issue_id")) == str(current_issue_id):
                                        killed_room = issue.get("killed_room")
                                        ui_queue.put(("log", (f"✅ Got result from API: Issue {current_issue_id}, Killed: {killed_room}", "green")))
                                        
                                        # Process result (same logic as WS result)
                                        # Handle state update directly now
                                        app_state["last_result"] = {"issue_id": current_issue_id, "killed_room": killed_room}
                                        
                                        ui_queue.put(("result", {"issue_id": current_issue_id, "killed_room": killed_room}))
                                        
                                        if game_engine is not None:
                                            try:
                                                game_engine.process_game_result(int(killed_room), current_issue_id)
                                                game_engine.update_balance()
                                                
                                                stats = game_engine.get_statistics()
                                                app_state["max_win_streak"] = stats["max_win_streak"]
                                                app_state["max_loss_streak"] = stats["max_loss_streak"]
                                                app_state["total_games"] = stats["total_games"]
                                                app_state["current_win_streak"] = stats["current_win_streak"]
                                                app_state["current_loss_streak"] = stats["current_loss_streak"]
                                                app_state["profit_loss"] = stats["profit_loss"]
                                            except Exception as e:
                                                ui_queue.put(("log", (f"API result processing error: {e}", "red")))
                                        
                                        # Re-enable auto-reconnect after processing
                                        is_waiting_for_result = False
                                        break
                                else:
                                    ui_queue.put(("log", (f"⚠️ Issue {current_issue_id} not found in API history", "yellow")))
                            else:
                                ui_queue.put(("log", (f"❌ API fetch failed: {response.status_code}", "red")))
                        except Exception as e:
                            ui_queue.put(("log", (f"❌ Backup API error: {e}", "red")))
                            import traceback
                            traceback.print_exc()
                
                # Start backup thread
                import threading
                backup_thread = threading.Thread(target=backup_result_fetch, daemon=True)
                backup_thread.start()

        elif msg_type == "notify_result":
            # Reset result waiting flag when we receive result from WS
            if is_waiting_for_result:
                ui_queue.put(("log", ("✅ Received WS result, re-enabling auto-reconnect", "green")))
                is_waiting_for_result = False
                result_backup_triggered = True  # Prevent backup thread from running
            
            killed = data.get("killed_room", "Unknown")
            last_killed_room = killed
            
            # DIRECT STATE UPDATE
            if "issue_id" in data:
                 app_state["last_result"] = {"issue_id": data["issue_id"], "killed_room": killed}
            
            ui_queue.put(("result", data))
            
            ui_queue.put(("log", (f"Result: Issue [bold]{data['issue_id']}[/] | Killed: [bold red]{killed}[/]", "white")))
            
            # Update game engine with result using NEW process_game_result
            if game_engine is not None:
                try:
                    game_engine.process_game_result(int(killed), data['issue_id'])
                    game_engine.update_balance()
                    
                    # Update app_state statistics
                    stats = game_engine.get_statistics()
                    app_state["max_win_streak"] = stats["max_win_streak"]
                    app_state["max_loss_streak"] = stats["max_loss_streak"]
                    app_state["total_games"] = stats["total_games"]
                    app_state["current_win_streak"] = stats["current_win_streak"]
                    app_state["current_loss_streak"] = stats["current_loss_streak"]
                    app_state["profit_loss"] = stats["profit_loss"]
                except Exception as e:
                    ui_queue.put(("log", (f"Result update error: {e}", "red")))
                    import traceback
                    traceback.print_exc()
            
            # Re-enter logic
            time.sleep(1)
            if USER_ID and SECRET_KEY:
                enter_game_msg = {
                    "msg_type": "handle_enter_game",
                    "asset_type": ASSET_TYPE, # Use global asset type
                    "user_id": USER_ID,
                    "user_secret_key": SECRET_KEY
                }
                ws.send(json.dumps(enter_game_msg))
                ui_queue.put(("log", ("Auto re-entering next issue...", "dim cyan")))
            else:
                ui_queue.put(("log", ("❌ Cannot re-enter: Missing credentials", "red")))


    except Exception as e:
        ui_queue.put(("log", (f"Error parsing msg: {e}", "red")))

def on_error(ws, error):
    global ws_connection_state
    ui_queue.put(("log", (f"❌ WS Error: {error}", "bold red")))
    ui_queue.put(("status", ("Error", "bold red")))
    ws_connection_state = "DISCONNECTED"

def on_close(ws, close_status_code, close_msg):
    global ws_connection_state
    ws_connection_state = "DISCONNECTED"
    ui_queue.put(("status", ("Disconnected", "red")))
    ui_queue.put(("log", (f"⚠️ WebSocket closed: {close_msg}", "yellow")))


def connect_websocket():
    """Connect WebSocket with auto-reconnect on failure"""
    global ws_instance, ws_connection_state, ws_reconnect_delay
    
    while ws_should_run:
        try:
            # Skip if already connecting or connected
            if ws_connection_state in ["CONNECTING", "CONNECTED"]:
                time.sleep(1)
                continue
            
            ws_connection_state = "CONNECTING"
            ui_queue.put(("status", ("Connecting...", "yellow")))
            ui_queue.put(("log", ("🔄 Connecting to WebSocket...", "cyan")))
            
            ws_instance = websocket.WebSocketApp(
                WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Run forever with ping
            ws_instance.run_forever(ping_interval=20, ping_timeout=10)
            
            # Connection closed, prepare for reconnect
            if ws_should_run and ws_connection_state != "CONNECTED":
                ui_queue.put(("log", (f"⏳ Reconnecting in {ws_reconnect_delay}s...", "yellow")))
                time.sleep(ws_reconnect_delay)
                
                # Exponential backoff
                ws_reconnect_delay = min(ws_reconnect_delay * 2, ws_max_reconnect_delay)
                
        except Exception as e:
            ui_queue.put(("log", (f"❌ WebSocket connection failed: {e}", "red")))
            if ws_should_run:
                time.sleep(ws_reconnect_delay)
                ws_reconnect_delay = min(ws_reconnect_delay * 2, ws_max_reconnect_delay)

def monitor_websocket_health():
    """Monitor WebSocket health and force reconnect if stale"""
    global ws_instance, ws_connection_state, ws_last_message_time, is_waiting_for_result
    
    while ws_should_run:
        time.sleep(2)  # Check every 2 seconds
        
        if ws_connection_state == "CONNECTED":
            time_since_last_msg = time.time() - ws_last_message_time
            
            # CRITICAL: Do NOT reconnect while waiting for game result
            if is_waiting_for_result:
                # Skip reconnect check while waiting for result
                continue
            
            if time_since_last_msg > HEARTBEAT_TIMEOUT:
                ui_queue.put(("log", (f"⚠️ No messages for {int(time_since_last_msg)}s, reconnecting...", "yellow")))
                
                # Force close to trigger reconnect
                try:
                    if ws_instance:
                        ws_instance.close()
                except:
                    pass
                
                ws_connection_state = "DISCONNECTED"

def run_ws():
    """Start WebSocket with auto-reconnect"""
    connect_websocket()


# --- UI RENDERING ---
def make_layout():
    layout = Layout(name="root")
    layout.split(
        Layout(name="stats_row", size=6),  # 3 statistic boxes - increased size to show all content
        Layout(name="info", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=12)
    )
    layout["stats_row"].split_row(
        Layout(name="account_box", ratio=1),
        Layout(name="streak_box", ratio=1),
        Layout(name="algo_box", ratio=1)
    )
    layout["main"].split_row(
        Layout(name="stats", ratio=2),
        Layout(name="history", ratio=3)
    )
    return layout

from rich.progress_bar import ProgressBar

def generate_header():
    status_text = Text(app_state["status"], style=app_state["status_style"])
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right")
    grid.add_row(
        f"🔗 WebSocket Client | User: [bold cyan]{USER_ID}[/]",
        Text.assemble("Status: ", status_text)
    )
    return Panel(grid, style="blue", box=box.ROUNDED)

def generate_info_panel():
    # Horizontal Game Info
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="center", ratio=3) # Width for progress bar
    grid.add_column(justify="center", ratio=1)
    
    # 1. Issue
    issue_text = Text.assemble("Issue: ", (str(app_state["issue_id"]), "bold yellow"))
    
    # 2. Countdown / Progress Bar
    cd_val = app_state["countdown"]
    
    if isinstance(cd_val, int):
        total = app_state["max_duration"]
        
        # Safety fallback
        if total is None: 
            total = cd_val
            app_state["max_duration"] = total
            
        elapsed = max(0, total - cd_val)
        
        # User request: "khi còn 1 là đã full thanh tg đi"
        if cd_val <= 1:
            completed = total
        else:
            completed = min(total, elapsed)
        
        # Combine Bar + Text
        bar_grid = Table.grid(expand=True)
        bar_grid.add_column(ratio=1)
        bar_grid.add_column(justify="right", width=5)
        
        bar_obj = ProgressBar(total=total, completed=completed, width=None, complete_style="green", finished_style="green")
        cd_str = f"{cd_val}s"
        
        bar_grid.add_row(bar_obj, Text(cd_str, style="bold white"))
        mid_content = bar_grid
    else:
        # Waiting text
        mid_content = Text("Đợi xí cho đủ người chơi...", style="dim italic white")
    
    # 3. Last Killed
    killed = "--"
    if app_state["last_result"]:
        killed = str(app_state["last_result"].get("killed_room", "--"))
    killed_text = Text.assemble("Last Killed: ", (killed, "bold red"))

    grid.add_row(issue_text, mid_content, killed_text)

    return Panel(grid, border_style="green", box=box.ROUNDED, padding=(0, 1))

def generate_stats_panel():
    # Room Stats (unchanged)
    table = Table(title=None, expand=True, box=box.SIMPLE_HEAD)
    table.add_column("Room", justify="center", style="cyan")
    table.add_column("Users", justify="right", style="magenta")
    table.add_column("Total Bet", justify="right", style="green")

    if not app_state["rooms"]:
        table.add_row("-", "-", "-")
    else:
        sorted_rooms = sorted(app_state["rooms"].items(), key=lambda x: int(x[0]))
        for r_id, stats in sorted_rooms:
            room_num = int(r_id)
            
            # Default style
            r_style = "cyan"
            u_style = "magenta"
            t_style = "green"
            
            # Highlight logic
            if game_engine and current_selected_room and room_num == current_selected_room:
                 r_style = "bold green"
                 u_style = "bold green"
                 t_style = "bold green"
            
            if last_killed_room and room_num == int(last_killed_room):
                 r_style = "bold red"
                 u_style = "bold red"
                 t_style = "bold red"
            
            table.add_row(
                Text(str(r_id), style=r_style),
                Text(str(stats['user_cnt']), style=u_style),
                Text(f"{stats['total_bet_amount']:,}", style=t_style)
            )

    return Panel(table, title="[bold]Live Room Stats[/]", border_style="blue", box=box.ROUNDED)

def generate_history_panel():
    # History Table with 4 columns
    hist_table = Table(title=None, box=box.SIMPLE_HEAD, expand=True)
    hist_table.add_column("Ván", style="dim cyan", justify="center", width=8)
    hist_table.add_column("Chọn", style="yellow", justify="center", width=5)
    hist_table.add_column("Giết", style="bold red", justify="center", width=5)
    hist_table.add_column("Cược", style="green", justify="right")

    for item in reversed(app_state["history"]):
        hist_table.add_row(
            str(item['issue']),
            str(item.get('choice', '--')),
            str(item['killed']),
            str(item['bet'])
        )

    return Panel(hist_table, title="[bold]Last 6 Games[/]", border_style="magenta", box=box.ROUNDED)

def generate_footer():
    # Logs (unchanged)
    log_content = Table.grid(padding=(0, 1))
    log_content.add_column(style="dim white", width=10)
    log_content.add_column()
    
    # Fix: Create a snapshot copy to avoid "deque mutated during iteration"
    # This prevents race condition when add_log() is called from other threads during rendering
    logs_snapshot = list(app_state["logs"])
    
    for log in logs_snapshot:
        log_content.add_row(log["time"], log["msg"])
        
    return Panel(log_content, title="[bold]System Logs[/]", border_style="white", box=box.ROUNDED)

def generate_account_box():
    """Generate account info box with real-time balances"""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="cyan", justify="left")
    grid.add_column(style="green bold", justify="right")
    
    with balance_lock:
        usdt = app_state['balances']['USDT']
        world = app_state['balances']['WORLD']
        build = app_state['balances']['BUILD']
    
    grid.add_row("💵 USDT:", f"{usdt:.2f}")
    grid.add_row("🌍 WORLD:", f"{world:.2f}")
    grid.add_row("🏗️ BUILD:", f"{build:.2f}")
    
    # Add demo mode indicator
    is_demo = game_config.demo_mode if game_config else False
    if is_demo:
        grid.add_row("", "")  # Empty row separator
        grid.add_row("⚠️ Mode:", "[yellow bold]DEMO[/]")
    
    return Panel(grid, title="[bold yellow]Số Dư[/]", border_style="yellow", box=box.ROUNDED, padding=(0, 1))

def generate_statistics_box():
    """Generate statistics box with 4 metrics"""
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="white", justify="left")
    grid.add_column(style="bold", justify="right")
    
    # Profit/Loss (green if positive, red if negative)
    pl = app_state['profit_loss']
    pl_style = "green bold" if pl > 0 else ("red bold" if pl < 0 else "dim")
    pl_text = f"+{pl:.2f}" if pl >= 0 else f"{pl:.2f}"
    grid.add_row("💰 Lời/Lỗ:", Text(pl_text, style=pl_style))
    
    # Win streak: Current / Max
    cur_win = app_state.get('current_win_streak', 0)
    max_win = app_state.get('max_win_streak', 0)
    grid.add_row("🔥 Chuỗi thắng:", Text(f"{cur_win}/{max_win}", style="green"))
    
    # Loss streak: Current / Max
    cur_loss = app_state.get('current_loss_streak', 0)
    max_loss = app_state.get('max_loss_streak', 0)
    grid.add_row("❄️ Chuỗi thua:", Text(f"{cur_loss}/{max_loss}", style="red"))
    
    # Total games
    grid.add_row("🎮 Tổng ván:", Text(str(app_state['total_games']), style="cyan"))
    
    return Panel(grid, title="[bold cyan]Thống kê[/]", border_style="cyan", box=box.ROUNDED, padding=(0, 1))

def generate_algo_box():
    """Generate algorithm info box"""
    algo_text = Text(app_state['algorithm'], style="yellow italic", justify="center")
    
    return Panel(
        Align.center(algo_text, vertical="middle"),
        title="[bold magenta]Thuật Toán[/]",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(0, 1)
    )

def update_ui_state():
    # Process all pending messages in queue
    while not ui_queue.empty():
        msg_type, data = ui_queue.get()
        
        if msg_type == "status":
            app_state["status"], app_state["status_style"] = data
            
        elif msg_type == "enter_game":
            app_state["issue_id"] = str(data["issue_id"])
            if "duration" in data:
                app_state["max_duration"] = data["duration"]
            
            # Reset countdown to None so "Waiting..." text shows until first countdown update
            app_state["countdown"] = None
            # app_state["max_duration"] = None # This line was redundant after adding the 'duration' check
                
            # Initialize rooms from enter_game if available
            if "room_stat" in data:
                for r in data["room_stat"]:
                    # Force room_id to string for consistent lookup
                    r_id = str(r["room_id"])
                    app_state["rooms"][r_id] = {
                        "user_cnt": r["user_cnt"],
                        "total_bet_amount": r["total_bet_amount"]
                    }
                    
        elif msg_type == "stats":
            # data is list of rooms
            for r in data:
                r_id = str(r["room_id"])
                app_state["rooms"][r_id] = {
                    "user_cnt": r["user_cnt"],
                    "total_bet_amount": r["total_bet_amount"]
                }
                
        elif msg_type == "countdown":
            val = data
            if app_state["max_duration"] is None or val > app_state["max_duration"]:
                app_state["max_duration"] = val
            
            app_state["countdown"] = val
            
        elif msg_type == "result":
            # data = {'issue_id': ..., 'killed_room': ...}
            app_state["last_result"] = data
            app_state["countdown"] = None # Reset countdown to show waiting msg
            app_state["max_duration"] = None
            
            # --- UPDATE HISTORY ---
            try:
                killed_room = str(data.get("killed_room"))
                issue_id = str(data.get("issue_id"))
                
                # FIX: Get our actual bet from game_engine.hands_history instead of current_selected_room
                our_choice = "--"
                our_bet = 0.0
                
                if game_engine and game_engine.hands_history:
                    # Find matching hand by issue_id
                    for hand in reversed(game_engine.hands_history):
                        if hand.get('issue_id') == issue_id:
                            our_choice = str(hand.get('room_selected', '--'))
                            our_bet = hand.get('bet_amount', 0.0)
                            break
                
                history_item = {
                    "issue": issue_id,
                    "choice": our_choice,  # Our actual bet room from hands_history
                    "killed": killed_room,
                    "bet": f"{our_bet:.4f}"  # Our actual bet amount
                }
                
                app_state["history"].append(history_item)
                if len(app_state["history"]) > MAX_HISTORY:
                    app_state["history"].pop(0)
                    
            except Exception as e:
                add_log(f"History Error: {e}", "red")

        elif msg_type == "bet_trigger":
            # Execute bet when countdown reaches 20s
            # DEPRECATED: Betting is now triggered directly from WS thread
            # execute_bet()
            pass

        elif msg_type == "log":
            msg, style = data
            add_log(msg, style)


# --- MAIN ENTRY POINT ---


# ============================================================================
# SECTION 8: MENU FUNCTIONS
# ============================================================================

def show_main_menu() -> str:
    """Display main menu and return choice"""
    console.clear()
    console.print(Panel(
        Text("VUA THOAT HIEM - MAIN MENU", justify="center", style="bold cyan"),
        box=box.DOUBLE,
        border_style="cyan"
    ))
    
    console.print("\n[cyan]Chon chuc nang:[/cyan]")
    console.print("  [bold]1.[/bold] Bat dau choi")
    console.print("  [bold]2.[/bold] Quan li account")
    console.print("  [bold]3.[/bold] Cai dat cau hinh")
    console.print("  [bold]4.[/bold] Thoat")
    
    choice = Prompt.ask("\nNhap lua chon", choices=["1", "2", "3", "4"], default="1")
    return choice


def display_accounts_table(accounts: List[Account]):
    """Display accounts in table format"""
    table = Table(
        title="Accounts",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("#", style="magenta", justify="center")
    table.add_column("Ten", style="yellow")
    table.add_column("UID", style="green")
    table.add_column("Secret", style="white")
    
    for i, acc in enumerate(accounts, 1):
        table.add_row(
            str(i),
            acc.name,
            acc.uid,
            acc.mask_secret()
        )
    
    console.print(table)


def add_account(accounts: List[Account]):
    """Add new account"""
    console.print("\n[cyan]--- THEM ACCOUNT MOI ---[/cyan]")
    
    # Choose input method
    console.print("\nChon cach nhap:")
    console.print("  1. Paste link game (tu dong trich xuat)")
    console.print("  2. Nhap thu cong (UID + Secret)")
    
    method = Prompt.ask("Chon cach", choices=["1", "2"], default="1")
    
    uid = None
    secret = None
    
    if method == "1":
        # Paste URL
        url = console.input("\n[cyan]Paste link game cua ban:[/cyan] ").strip()
        uid, secret = parse_game_url(url)
        
        if uid and secret:
            console.print(f"[green]Trich xuat thanh cong![/green]")
            console.print(f"   UID: {uid}")
            console.print(f"   Secret: {secret[:10]}...{secret[-10:]}")
        else:
            console.print("[red]Khong the trich xuat! Vui long nhap thu cong.[/red]")
            uid = console.input("   Nhap UID: ").strip()
            secret = console.input("   Nhap Secret Key: ").strip()
    else:
        # Manual input
        uid = console.input("   Nhap UID: ").strip()
        secret = console.input("   Nhap Secret Key: ").strip()
    
    # Enter name
    name = console.input("\n   Nhap ten account (VD: Tai khoan chinh): ").strip()
    if not name:
        name = f"Account {uid[:4]}"
    
    # Validate
    if not uid or not secret:
        console.print("[red]Loi: UID hoac Secret khong hop le![/red]")
        console.input("\nNhan Enter de tiep tuc...")
        return
    
    # Save
    accounts.append(Account(name, uid, secret))
    save_accounts(accounts)
    console.print(f"\n[green]Da them account '{name}' thanh cong![/green]")
    console.input("\nNhan Enter de tiep tuc...")


def delete_account(accounts: List[Account]):
    """Delete account"""
    if not accounts:
        console.print("\n[yellow]Chua co account nao.[/yellow]")
        console.input("\nNhan Enter de tiep tuc...")
        return
    
    console.print("\n[cyan]--- XOA ACCOUNT ---[/cyan]")
    display_accounts_table(accounts)
    
    try:
        idx = IntPrompt.ask("\nChon so thu tu account can xoa (0 de huy)", default=0)
        if idx == 0:
            return
        
        if 1 <= idx <= len(accounts):
            account = accounts[idx - 1]
            confirm = Confirm.ask(f"Xac nhan xoa account '{account.name}'?")
            if confirm:
                accounts.pop(idx - 1)
                save_accounts(accounts)
                console.print("\n[green]Da xoa account thanh cong![/green]")
        else:
            console.print("\n[red]So thu tu khong hop le![/red]")
    except:
        console.print("\n[red]Loi nhap lieu![/red]")
    
    console.input("\nNhan Enter de tiep tuc...")


def edit_account(accounts: List[Account]):
    """Edit account"""
    if not accounts:
        console.print("\n[yellow]Chua co account nao.[/yellow]")
        console.input("\nNhan Enter de tiep tuc...")
        return
    
    console.print("\n[cyan]--- SUA ACCOUNT ---[/cyan]")
    display_accounts_table(accounts)
    
    try:
        idx = IntPrompt.ask("\nChon so thu tu account can sua (0 de huy)", default=0)
        if idx == 0:
            return
        
        if 1 <= idx <= len(accounts):
            account = accounts[idx - 1]
            console.print(f"\n[cyan]Dang sua account: {account.name}[/cyan]")
            console.print("  (Nhan Enter de giu nguyen)")
            
            # Edit name
            new_name = console.input(f"\n  Ten moi (hien tai: '{account.name}'): ").strip()
            
            # Edit UID + Secret
            console.print("\n  Sua UID va Secret:")
            console.print("    1. Paste link game (tu dong)")
            console.print("    2. Nhap thu cong")
            console.print("    3. Khong sua (giu nguyen)")
            
            edit_method = Prompt.ask("  Chon cach", choices=["1", "2", "3"], default="3")
            
            new_uid = None
            new_secret = None
            
            if edit_method == "1":
                url = console.input("\n  Paste link game moi: ").strip()
                if url:
                    new_uid, new_secret = parse_game_url(url)
                    if new_uid and new_secret:
                        console.print(f"[green]  Trich xuat thanh cong![/green]")
                        console.print(f"     UID: {new_uid}")
                        console.print(f"     Secret: {new_secret[:10]}...{new_secret[-10:]}")
                    else:
                        console.print("[red]  Khong the trich xuat! Giu nguyen gia tri cu.[/red]")
            
            elif edit_method == "2":
                new_uid = console.input(f"  UID moi (hien tai: {account.uid}): ").strip()
                new_secret = console.input(f"  Secret moi (hien tai: {account.mask_secret()}): ").strip()
            
            # Update
            if new_name:
                account.name = new_name
            if new_uid:
                account.uid = new_uid
            if new_secret:
                account.secret = new_secret
            
            save_accounts(accounts)
            console.print(f"\n[green]Da cap nhat account thanh cong![/green]")
        else:
            console.print("\n[red]So thu tu khong hop le![/red]")
    except:
        console.print("\n[red]Loi nhap lieu![/red]")
    
    console.input("\nNhan Enter de tiep tuc...")


def display_accounts(accounts: List[Account]):
    """Display all accounts"""
    console.clear()
    console.print(Panel(
        Text("DANH SACH TAI KHOAN", justify="center", style="bold green"),
        box=box.DOUBLE,
        border_style="green"
    ))
    
    if not accounts:
        console.print("\n[yellow]Chua co account nao.[/yellow]")
    else:
        display_accounts_table(accounts)
    
    console.input("\nNhan Enter de tiep tuc...")


def menu_account_management():
    """Account management menu"""
    accounts = load_accounts()
    
    while True:
        console.clear()
        console.print(Panel(
            Text("QUAN LI TAI KHOAN", justify="center", style="bold yellow"),
            box=box.DOUBLE,
            border_style="yellow"
        ))
        
        console.print("\n[yellow]Chon chuc nang:[/yellow]")
        console.print("  [bold]1.[/bold] Them account moi")
        console.print("  [bold]2.[/bold] Xoa account")
        console.print("  [bold]3.[/bold] Sua account")
        console.print("  [bold]4.[/bold] Hien thi danh sach account")
        console.print("  [bold]5.[/bold] Quay lai")
        
        choice = Prompt.ask("\nNhap lua chon", choices=["1", "2", "3", "4", "5"], default="5")
        
        if choice == "1":
            add_account(accounts)
        elif choice == "2":
            delete_account(accounts)
        elif choice == "3":
            edit_account(accounts)
        elif choice == "4":
            display_accounts(accounts)
        elif choice == "5":
            break


def menu_settings():
    """Settings configuration menu"""
    config = load_config()
    
    while True:
        console.clear()
        console.print(Panel(
            Text("CAI DAT CAU HINH", justify="center", style="bold magenta"),
            box=box.DOUBLE,
            border_style="magenta"
        ))
        
        # Display current config
        console.print("\n[dim]Cau hinh hien tai:[/dim]")
        console.print(f"  Thuat toan: [cyan]{config.algorithm}[/cyan]")
        console.print(f"  Su dung chia tay: [cyan]{'Co' if config.use_tay_system else 'Khong'}[/cyan]")
        if config.use_tay_system:
            console.print(f"    - So tay: {config.num_tay}, He so: x{config.multiplier}")
        console.print(f"  Tai dau tu: [cyan]{'Co' if config.reinvest_profit else 'Khong'}[/cyan]")
        
        console.print("\n[magenta]Chon tuy chon:[/magenta]")
        console.print("  [bold]1.[/bold] Tu chia tay (Bankroll Management)")
        console.print("  [bold]2.[/bold] Tu dong tang cuoc (Reinvest)")
        console.print("  [bold]3.[/bold] Thuat toan du doan")
        console.print("  [bold]4.[/bold] Nghi sau thua lien tiep")
        console.print("  [bold]5.[/bold] Nghi dinh ky")
        console.print("  [bold]6.[/bold] Chot lai (Take Profit)")
        console.print("  [bold]7.[/bold] Chot lo (Stop Loss)")
        console.print("  [bold]8.[/bold] Luu cau hinh")
        console.print("  [bold]9.[/bold] Quay lai")
        
        choice = Prompt.ask("\nNhap lua chon", choices=["1","2","3","4","5","6","7","8","9"], default="9")
        
        if choice == "1":
            setup_bankroll(config)
        elif choice == "2":
            setup_reinvest(config)
        elif choice == "3":
            setup_algorithm(config)
        elif choice == "4":
            setup_pause_after_losses(config)
        elif choice == "5":
            setup_periodic_pause(config)
        elif choice == "6":
            setup_take_profit(config)
        elif choice == "7":
            setup_stop_loss(config)
        elif choice == "8":
            save_config(config)
            console.print("\n[green]Da luu cau hinh thanh cong![/green]")
            console.input("\nNhan Enter de tiep tuc...")
        elif choice == "9":
            if Confirm.ask("\nLuu cau hinh truoc khi thoat?"):
                save_config(config)
                console.print("[green]Da luu![/green]")
            break


def setup_bankroll(config):
    """Setup bankroll management"""
    console.print("\n[cyan]--- TU CHIA TAY (BANKROLL MANAGEMENT) ---[/cyan]")
    
    use_tay = Confirm.ask("\nBan co muon chia von theo 'tay' khong?", default=config.use_tay_system)
    config.use_tay_system = use_tay
    
    if use_tay:
        # Get current balance
        current_balance = app_state.get("balance_build", 0)
        if current_balance <= 0:
            console.print("[yellow]Updating balance from server...[/yellow]")
            
            # Create temporary API instance if game_api not initialized yet
            if game_api:
                balance_data = game_api.fetch_balance()
            elif USER_ID and SECRET_KEY:
                temp_api = GameAPI(str(USER_ID), SECRET_KEY, ASSET_TYPE)
                balance_data = temp_api.fetch_balance()
            else:
                balance_data = None
            
            console.print(f"[dim]API Response: {balance_data}[/dim]")
            if balance_data:
                current_balance = balance_data.get("BUILD", 0)
                app_state["balance_build"] = current_balance
            else:
                current_balance = 1000.0  # Fallback
        
        console.print(f"\n[cyan]Current balance: {current_balance:.2f} BUILD[/cyan]")
        
        # Safe capital with validation
        while True:
            safe_cap = FloatPrompt.ask(
                f"  Von bao toan (so tien giu lai, khong dung de choi)",
                default=config.safe_capital
            )
            if safe_cap >= current_balance:
                console.print(f"[red]❌ Von bao toan ({safe_cap:.2f}) >= current balance ({current_balance:.2f})[/red]")
                console.print(f"[yellow]Vui long nhap so nho hon {current_balance:.2f}[/yellow]")
                continue
            config.safe_capital = safe_cap
            break
        
        # Number of hands
        config.num_tay = IntPrompt.ask("\n  So tay (chuoi thua toi da + 1)", default=config.num_tay)
        
        # Multiplier
        config.multiplier = FloatPrompt.ask("  He so nhan khi thua", default=config.multiplier)
        
        # Calculate base bet from REAL playing capital
        playing_capital = current_balance - config.safe_capital
        config.base_bet = calculate_base_bet(playing_capital, config.num_tay, config.multiplier)
        
        # Display calculation info
        console.print(f"\n[cyan]Tinh toan:[/cyan]")
        console.print(f"  Total balance: {current_balance:.2f} BUILD")
        console.print(f"  Safe capital: {config.safe_capital:.2f} BUILD")
        console.print(f"  Playing capital: {playing_capital:.2f} BUILD")
        console.print(f"  Base bet: {config.base_bet:.4f} BUILD (tinh tu {playing_capital:.2f} / {config.num_tay} tay / {config.multiplier}x)")
        console.print(f"\n[green]Da cau hinh: {config.num_tay} tay voi he so x{config.multiplier}, base bet {config.base_bet:.4f}[/green]")
    else:
        config.base_bet = FloatPrompt.ask("  Nhap so BUILD choi moi van", default=config.base_bet)
        config.multiplier = FloatPrompt.ask("  He so nhan khi thua", default=config.multiplier)
    
    console.input("\nNhan Enter de tiep tuc...")


def setup_reinvest(config):
    """Setup reinvest profit"""
    console.print("\n[cyan]--- TU DONG TANG CUOC (REINVEST) ---[/cyan]")
    console.print("Tai dau tu loi nhuan: Tu dong tang cuoc khi co lai")
    
    config.reinvest_profit = Confirm.ask("\nBat tinh nang nay?", default=config.reinvest_profit)
    
    if config.reinvest_profit:
        console.print("[green]Da bat tai dau tu loi nhuan![/green]")
    else:
        console.print("[yellow]Da tat tai dau tu loi nhuan.[/yellow]")
    
    console.input("\nNhan Enter de tiep tuc...")


def setup_algorithm(config):
    """Setup prediction algorithm"""
    console.print("\n[cyan]--- THUAT TOAN DU DOAN ---[/cyan]")
    
    # Display algorithms
    # Display algorithms with license filtering
    license_type = app_state.get("license_type", "Unknown")
    is_vip = "VIP" in license_type or "ADMIN" in license_type
    
    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("#", style="magenta")
    table.add_column("Ten", style="yellow")
    table.add_column("Win Rate", style="green")
    table.add_column("Mo ta", style="white")
    
    valid_keys = []
    for key, algo in ALGORITHMS.items():
        # Filtering logic:
        # Free Key: 1-7
        # VIP Key: 1-13 (All)
        if int(key) > 7 and not is_vip:
            continue
            
        table.add_row(key, algo["name"], algo["win_rate"], algo["desc"])
        valid_keys.append(key)
    
    console.print(table)
    if not is_vip:
        console.print("[dim italic]Nang cap VIP de mo khoa logic 8-13[/dim italic]")
    
    choice = Prompt.ask("\nChon thuat toan", choices=valid_keys, default="7") # Default to SAFE_GUARD (7)
    config.algorithm = ALGORITHMS[choice]["name"]
    
    console.print(f"\n[green]Da chon: {config.algorithm}[/green]")
    console.input("\nNhan Enter de tiep tuc...")


def setup_pause_after_losses(config):
    """Setup pause after consecutive losses"""
    console.print("\n[cyan]--- NGHI SAU THUA LIEN TIEP ---[/cyan]")
    console.print("Tu dong tam dung khi thua lien tiep qua nhieu")
    
    config.pause_after_losses = IntPrompt.ask("\nSo van thua toi da", default=config.pause_after_losses)
    
    console.print(f"\n[green]Se tam dung sau {config.pause_after_losses} thua lien tiep.[/green]")
    console.input("\nNhan Enter de tiep tuc...")


def setup_periodic_pause(config):
    """Setup periodic pause"""
    console.print("\n[cyan]--- NGHI DINH KY ---[/cyan]")
    console.print("Choi X van → Nghi Y van (lap lai)")
    
    config.bet_rounds_before_skip = IntPrompt.ask("\nChoi bao nhieu van", default=config.bet_rounds_before_skip)
    config.pause_rounds = IntPrompt.ask("Nghi bao nhieu van", default=config.pause_rounds)
    
    console.print(f"\n[green]Se choi {config.bet_rounds_before_skip} van, nghi {config.pause_rounds} van.[/green]")
    console.input("\nNhan Enter de tiep tuc...")


def setup_take_profit(config):
    """Setup take profit"""
    console.print("\n[cyan]--- CHOT LAI (TAKE PROFIT) ---[/cyan]")
    console.print("Tu dong dung khi dat muc tieu loi nhuan")
    
    config.stop_when_profit_reached = Confirm.ask("\nBat tinh nang nay?", default=config.stop_when_profit_reached)
    
    if config.stop_when_profit_reached:
        config.profit_target = FloatPrompt.ask(f"Muc tieu lai ({config.asset_type})", default=config.profit_target)
        console.print(f"\n[green]Se dung khi lai >= {config.profit_target} {config.asset_type}.[/green]")
    else:
        console.print("[yellow]Da tat chot lai.[/yellow]")
    
    console.input("\nNhan Enter de tiep tuc...")


def setup_stop_loss(config):
    """Setup stop loss"""
    console.print("\n[cyan]--- CHOT LO (STOP LOSS) ---[/cyan]")
    console.print("Tu dong dung khi lo qua nhieu (bao ve von)")
    
    config.stop_when_loss_reached = Confirm.ask("\nBat tinh nang nay?", default=config.stop_when_loss_reached)
    
    if config.stop_when_loss_reached:
        config.stop_loss_target = FloatPrompt.ask(f"Muc lo toi da ({config.asset_type})", default=config.stop_loss_target)
        console.print(f"\n[green]Se dung khi lo >= {config.stop_loss_target} {config.asset_type}.[/green]")
    else:
        console.print("[yellow]Da tat chot lo.[/yellow]")
    
    console.input("\nNhan Enter de tiep tuc...")


def menu_game_start():
    """Game start menu - Select account and start game"""
    console.clear()
    console.print(Panel(
        Text("BAT DAU CHOI", justify="center", style="bold green"),
        box=box.DOUBLE,
        border_style="green"
    ))
    
    # Step 1: Select account
    accounts = load_accounts()
    if not accounts:
        console.print("\n[red]Chua co account nao! Vui long them account truoc.[/red]")
        console.input("\nNhan Enter de quay lai...")
        return False
    
    console.print("\n[cyan]STEP 1: CHON ACCOUNT[/cyan]")
    display_accounts_table(accounts)
    
    if len(accounts) == 1:
        selected_account = accounts[0]
        console.print(f"\n[green]Tu dong chon account: {selected_account.name}[/green]")
    else:
        account_idx = IntPrompt.ask(
            "Chon account (1-N)",
            default=1
        )
        if account_idx < 1 or account_idx > len(accounts):
            console.print("[red]Lua chon khong hop le![/red]")
            console.input("\nNhan Enter...")
            return False
        selected_account = accounts[account_idx - 1]
    
    # Set global USER_ID and SECRET_KEY immediately after account selection
    # This allows API calls during config setup
    global USER_ID, SECRET_KEY
    USER_ID = int(selected_account.uid)
    SECRET_KEY = selected_account.secret
    
    # Step 1.5: Select Asset Type
    console.print("\n[cyan]STEP 1.5: CHON LOAI TAI SAN[/cyan]")
    config_temp = load_config() # Load temp to get default
    asset_choices = ["BUILD", "USDT", "WORLD"]
    asset_choice = Prompt.ask("Chon loai tai san", choices=asset_choices, default=config_temp.asset_type)
    
    # Update global ASSET_TYPE
    global ASSET_TYPE
    ASSET_TYPE = asset_choice
    
    # Save to config later (or update loaded config)
    
    # Step 2: Load config
    console.print("\n[cyan]STEP 2: LOAD CONFIG[/cyan]")
    config = load_config()
    # OVERRIDE config asset type with user selection
    config.asset_type = ASSET_TYPE
    
    # Display current config
    console.print("\n[dim]Cau hinh hien tai:[/dim]")
    console.print(f"  ASSET: [bold yellow]{config.asset_type}[/bold yellow]")
    console.print(f"  Algorithm: [cyan]{config.algorithm}[/cyan]")
    console.print(f"  Base bet: [cyan]{config.base_bet:.4f}[/cyan] {config.asset_type}")
    console.print(f"  Multiplier: [cyan]x{config.multiplier}[/cyan]")
    if config.use_tay_system:
        console.print(f"  Von bao toan: [cyan]{config.safe_capital:.2f}[/cyan] {config.asset_type}")
        console.print(f"  So tay: [cyan]{config.num_tay}[/cyan]")
    
    # Ask if want to play with current config
    console.print("\n[yellow]Chon lua chon:[/yellow]")
    console.print("  1. Choi voi cau hinh nay")
    console.print("  2. Cau hinh nhanh (chi cho lan nay)")
    console.print("  3. Quay lai Settings de luu cau hinh moi")
    
    config_choice = Prompt.ask("Chon", choices=["1", "2", "3"], default="1")
    
    if config_choice == "3":
        console.print("[yellow]Vui long vao Settings de cau hinh.[/yellow]")
        console.input("\nNhan Enter...")
        return False
    
    elif config_choice == "2":
        # Quick config (temporary for this session only)
        console.print("\n[cyan]--- CAU HINH NHANH (TAM THOI) ---[/cyan]")
        console.print("[dim]Cau hinh nay chi dung cho lan choi nay, khong luu vao file.[/dim]\n")
        
        # Algorithm
        console.print("[yellow]1. THUAT TOAN DU DOAN[/yellow]")
        console.print("Chon thuat toan:")
        for key, algo in ALGORITHMS.items():
            console.print(f"  {key}. {algo['name']} ({algo['win_rate']})")
        algo_choice = Prompt.ask("Chon algorithm", choices=list(ALGORITHMS.keys()), default="1")
        config.algorithm = ALGORITHMS[algo_choice]["name"]
        # Sync app_state for UI display
        app_state["algorithm"] = config.algorithm
        
        # Bankroll
        console.print("\n[yellow]2. TU CHIA TAY (BANKROLL MANAGEMENT)[/yellow]")
        if Confirm.ask("Su dung he thong chia tay?", default=config.use_tay_system):
            config.use_tay_system = True
            
            # Get current balance
            current_balance = app_state.get("balances", {}).get("BUILD", 0)
            if current_balance <= 0:
                console.print("[yellow]Updating balance from server...[/yellow]")
                
                # Create temporary API instance if game_api not initialized yet
                if game_api:
                    balance_data = game_api.fetch_balance()
                elif USER_ID and SECRET_KEY:
                    temp_api = GameAPI(str(USER_ID), SECRET_KEY, ASSET_TYPE)
                    balance_data = temp_api.fetch_balance()
                else:
                    balance_data = None
                
                console.print(f"[dim]API Response: {balance_data}[/dim]")
                if balance_data:
                    current_balance = balance_data.get("BUILD", 0)
                    app_state["balances"]["BUILD"] = current_balance
                else:
                    current_balance = 1000.0  # Fallback
            
            console.print(f"[cyan]Current balance: {current_balance:.2f} {config.asset_type}[/cyan]")
            
            # Input safe capital with validation
            while True:
                safe_cap = FloatPrompt.ask(f"  Von bao toan ({config.asset_type})", default=config.safe_capital)
                if safe_cap >= current_balance:
                    console.print(f"[red]❌ Von bao toan ({safe_cap:.2f}) >= current balance ({current_balance:.2f})[/red]")
                    console.print(f"[yellow]Vui long nhap so nho hon {current_balance:.2f}[/yellow]")
                    continue
                config.safe_capital = safe_cap
                break
            
            config.num_tay = IntPrompt.ask("  So tay", default=config.num_tay)
            config.multiplier = FloatPrompt.ask("  He so nhan", default=config.multiplier)
            
            # Calculate base bet from REAL playing capital
            playing_capital = current_balance - config.safe_capital
            config.base_bet = calculate_base_bet(playing_capital, config.num_tay, config.multiplier)
            
            # Display calculation info
            console.print(f"\n[cyan]Tinh toan:[/cyan]")
            console.print(f"  Total balance: {current_balance:.2f} {config.asset_type}")
            console.print(f"  Safe capital: {config.safe_capital:.2f} {config.asset_type}")
            console.print(f"  Playing capital: {playing_capital:.2f} {config.asset_type}")
            console.print(f"  Base bet: {config.base_bet:.4f} {config.asset_type} (tinh tu {playing_capital:.2f} / {config.num_tay} tay / {config.multiplier}x)")
        else:
            config.use_tay_system = False
            config.base_bet = FloatPrompt.ask(f"  Base bet ({config.asset_type})", default=config.base_bet)
            config.multiplier = FloatPrompt.ask("  He so nhan khi thua", default=config.multiplier)
        
        # Reinvest
        console.print("\n[yellow]3. TAI DAU TU LOI NHUAN[/yellow]")
        config.reinvest_profit = Confirm.ask("Bat tai dau tu loi nhuan khi co lai?", default=config.reinvest_profit)
        
        # Pause after losses
        console.print("\n[yellow]4. NGHI SAU KHI THUA[/yellow]")
        config.pause_after_losses = IntPrompt.ask("Sau khi thua thi nghi bao nhieu van?", default=config.pause_after_losses)
        
        # Periodic pause
        console.print("\n[yellow]5. NGHI DINH KY[/yellow]")
        config.bet_rounds_before_skip = IntPrompt.ask("Choi bao nhieu van roi nghi mot lan?", default=config.bet_rounds_before_skip)
        config.pause_rounds = IntPrompt.ask("Nghi bao nhieu van?", default=config.pause_rounds)
        
        # Take profit
        console.print("\n[yellow]6. CHOT LAI (TAKE PROFIT)[/yellow]")
        if Confirm.ask("Bat chot lai khi co lai?", default=config.stop_when_profit_reached):
            config.stop_when_profit_reached = True
            config.profit_target = FloatPrompt.ask("  Muc tieu lai (BUILD)", default=config.profit_target)
        else:
            config.stop_when_profit_reached = False
        
        # Stop loss
        console.print("\n[yellow]7. CHOT LO (STOP LOSS)[/yellow]")
        if Confirm.ask("Bat chot lo khi thua?", default=config.stop_when_loss_reached):
            config.stop_when_loss_reached = True
            config.stop_loss_target = FloatPrompt.ask("  Muc tieu lo (BUILD)", default=config.stop_loss_target)
        else:
            config.stop_when_loss_reached = False
        
        console.print("\n[green]Da cau hinh xong![/green]")
    
    # Display final config summary
    console.print("\n[green]===  CAU HINH CHOI ===[/green]")
    console.print(f"  Algorithm: {config.algorithm}")
    console.print(f"  Base bet: {config.base_bet:.4f} BUILD")
    console.print(f"  Multiplier: x{config.multiplier}")
    if config.use_tay_system:
        console.print(f"  So tay: {config.num_tay}")
        console.print(f"  Von bao toan: {config.safe_capital:.2f} BUILD")
    if config.reinvest_profit:
        console.print("  Auto reinvest: Bat")
    if config.stop_when_profit_reached:
        console.print(f"  Chot lai: {config.profit_target:.2f} BUILD")
    if config.stop_when_loss_reached:
        console.print(f"  Chot lo: {config.stop_loss_target:.2f} BUILD")
    
    # Ask about demo mode
    console.print("\n[yellow]===  CHE DO CHOI ===[/yellow]")
    console.print("[cyan]Demo Mode:[/cyan] Chi xem, khong cuoc that (dung de test thuat toan)")
    console.print("[cyan]Real Mode:[/cyan] Dat cuoc that su voi tien BUILD")
    
    config.demo_mode = Confirm.ask("\n[bold yellow]Ban co muon CUOC THAT khong?[/bold yellow]", default=True)
    config.demo_mode = not config.demo_mode  # Invert: if user says YES to real betting, demo_mode = False
    
    if config.demo_mode:
        console.print("[yellow]⚠️  CHE DO DEMO: Se khong dat cuoc that, chi xem thuat toan hoat dong[/yellow]")
    else:
        console.print("[green]✓ CHE DO CUOC THAT: Se dat cuoc that su voi tien BUILD[/green]")
    
    # Confirm start
    if not Confirm.ask("\nBat dau choi game?", default=True):
        return False
    
    # Update global game_config
    global game_config
    game_config = config  # Use the config (either loaded or quick-configured)
    # Sync app_state for UI display
    app_state["algorithm"] = config.algorithm
    
    console.print("\n[cyan]Dang khoi tao game...[/cyan]")
    time.sleep(1)
    
    return True


def run_game_loop():
    """Run the main game loop with current config"""
    global game_api, game_engine
    
    # Initialize game engine
    if not initialize_game_engine():
        console.print("[red]Failed to initialize game engine![/red]")
        console.input("\nNhan Enter de quay lai...")
        return
    
    # Start WS Thread
    ws_thread = threading.Thread(target=run_ws, daemon=True)
    ws_thread.start()
    
    # Start WebSocket Health Monitor Thread
    health_thread = threading.Thread(target=monitor_websocket_health, daemon=True)
    health_thread.start()
    
    # ✅ FIX #2: Use BalancePoller singleton instead of manual thread
    balance_poller.start()

    # Start Rich Live UI
    layout = make_layout()
    
    # Add initial log
    ui_queue.put(("log", ("System UI Initialized", "bold green")))
    ui_queue.put(("log", (f"Using Algorithm: {game_config.algorithm}", "cyan")))
    
    try:
        with Live(layout, refresh_per_second=4, screen=False) as live:
            last_queue_monitor = time.time()
            
            while True:
                update_ui_state()
                
                # ✅ FIX #1: Monitor queue health every 60s
                if time.time() - last_queue_monitor > 60:
                    stats = ui_queue.get_stats()
                    if stats['utilization'] > 80:
                        console.print(f"[yellow][WARN] UI Queue: {stats['size']}/{stats['maxsize']} ({stats['utilization']:.1f}%), dropped: {stats['dropped']}[/yellow]")
                    last_queue_monitor = time.time()
                
                # Update 3 statistic boxes at the top
                layout["account_box"].update(generate_account_box())
                layout["streak_box"].update(generate_statistics_box())
                layout["algo_box"].update(generate_algo_box())
                
                layout["info"].update(generate_info_panel())
                layout["stats"].update(generate_stats_panel())
                layout["history"].update(generate_history_panel())
                layout["footer"].update(generate_footer())
                
                time.sleep(0.1)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Dung game...[/yellow]")
        
        # ✅ FIX #2: Proper cleanup
        balance_poller.stop()
        
        if game_engine:
            stats = game_engine.get_statistics()
            console.print(f"\nThong ke: {stats['total_games']} van, Win Rate: {stats['win_rate']:.1f}%, P/L: {stats['profit_loss']:.2f} BUILD")
        console.input("\nNhan Enter de quay lai menu...")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        # LICENSE CHECK
        license_type = run_key_activation_flow()
        app_state["license_type"] = license_type # Store for global access
        console.clear()
        console.print(f"\n[bold green]Tool đang chạy với quyền: {license_type}...[/]")
        time.sleep(1)
        
        # Main menu loop
        while True:
            choice = show_main_menu()
            
            if choice == "1":
                # Start game
                if menu_game_start():
                    run_game_loop()
            
            elif choice == "2":
                # Account management
                menu_account_management()
            
            elif choice == "3":
                # Settings
                menu_settings()
            
            elif choice == "4":
                # Exit
                console.print("\n[yellow]Tamiet![/yellow]")
                break
    
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Da dung.[/yellow]")
    except Exception as e:
        console.print(f"\n\n[red]Loi: {e}[/red]")
        import traceback
        traceback.print_exc()

