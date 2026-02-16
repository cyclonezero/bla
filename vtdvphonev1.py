# -*- coding: utf-8 -*-
import sys
import time
import os
import json
import random 
import datetime
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from collections import Counter
import hashlib
import hmac

def install_and_import(package, import_name):
    try:
        __import__(import_name)
    except ImportError:
        print(f"Dang cai dat thu vien: {package}...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except Exception as e:
            print(f"Loi cai dat {package}: {e}")

required_packages = [
    ("requests", "requests"),
    ("pytz", "pytz"),
    ("user-agent", "user_agent"),
    ("colorama", "colorama"),
    ("rich", "rich")
]

for pkg, imp in required_packages:
    install_and_import(pkg, imp)

import requests
import pytz
from user_agent import generate_user_agent
from colorama import Fore, Style, init
import base64
import platform
import subprocess
import uuid
import codecs

# Rich imports
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

# Configure console for UTF-8 on Windows
if platform.system() == "Windows":
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

console = Console()

init(autoreset=True)

class Col:
    CYAN = Fore.CYAN
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    WHITE = Fore.WHITE
    RESET = Style.RESET_ALL
    BRIGHT = Style.BRIGHT

def print_banner_ltool():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Col.RED + Col.BRIGHT + r"""
██╗      ████████╗ ██████╗  ██████╗ ██╗
██║      ╚══██╔══╝██╔═══██╗██╔═══██╗██║
██║         ██║   ██║   ██║██║   ██║██║
██║         ██║   ██║   ██║██║   ██║██║
███████╗    ██║   ╚██████╔╝╚██████╔╝███████╗
╚══════╝    ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
    """ + Col.RESET)
    print(Col.CYAN + "="*60)
    print(f"{Col.YELLOW} 👤 ADMIN: {Col.BRIGHT}Lương Anh{Col.RESET}")
    print(f"{Col.YELLOW} 📢 ZALO GROUP : {Col.BRIGHT}https://zalo.me/g/ljtglc229{Col.RESET}")
    print(f"{Col.YELLOW} 🛠️  PHIÊN BẢN : {Col.BRIGHT}V1{Col.RESET}")
    print(Col.CYAN + "="*60 + Col.RESET)
    print("\n")

API_BASE = "https://api.sprintrun.win/sprint"
URL_USER_INFO = "https://wallet.3games.io/api/wallet/user_asset" 
URL_BET = f"{API_BASE}/bet"
URL_RECENT_10 = f"{API_BASE}/recent_10_issues"
URL_RECENT_100 = f"{API_BASE}/recent_100_issues"
URL_ISSUE_RESULT = f"{API_BASE}/issue_result" 
URL_HOME = f"{API_BASE}/home" 

# Lấy thư mục làm việc (tương thích exec())
# Khi chạy bằng exec(), __file__ không tồn tại nên dùng getcwd()
# Support LTOOL_ROOT for auto-update system
if os.getenv("LTOOL_ROOT"):
    BASE_DIR = os.getenv("LTOOL_ROOT")
else:
    BASE_DIR = os.getcwd()

# Tạo thư mục data riêng
DATA_DIR = os.path.join(BASE_DIR, 'vtdvphonev1_data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(DATA_DIR, "history_data.json")
TRAINING_FILE = os.path.join(DATA_DIR, "ltool_data.json")

global_history_data = [] 
bot_bet_history_tracker = []

# ============================================================================
# HỆ THỐNG KEY VERIFICATION (FREE + VIP) - RICH UI VERSION
# ============================================================================

# ===== CẤU HÌNH LIÊN KẾT API HOST =====
GENERATE_TOKEN_URL = "http://cyclonezerotool.x10.network/czero_api/generate_token.php" 
VERIFY_TOKEN_URL = "http://cyclonezerotool.x10.network/czero_api/verify_token_create_key.php"

# Bắt buộc phải giống hệt $SECRET_KEY trong file PHP để Python tự dịch được Key
SECRET_KEY_FREE = "cocaiconchim"

# Cấu hình VIP
VIP_API_URL = "http://cyclonezerotool.x10.network/czero_api/key_tool.php"
TOOL_SECRET = "Luanvi1904_luonganh_tool_1237_Nguyen_Czero@123456789419_tao_key_haha_do_ma_doan_duoc_do_e_yeu_hi_hi_bruhhhhhhhhhhhhh_shibaaaaaaa_conchim_hi_hi"
KEY_CHECK_INTERVAL = 30

# ===== HỆ THỐNG LƯU TRỮ =====
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

def load_system_data() -> dict:
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

def save_system_data(data: dict) -> None:
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

# ===== QUẢN LÝ MÃ MÁY =====
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

# ===== QUẢN LÝ LICENSE =====
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

def get_stored_license() -> dict:
    return load_system_data().get("license")

def clear_stored_license() -> None:
    data = load_system_data()
    data["license"] = None
    save_system_data(data)

# ===== TỰ DỊCH KEY FREE TRONG PYTHON =====
def verify_free_key(key: str, machine_id: str):
    """Giải mã Key từ server PHP trả về (Bản cắt 12 kí tự)"""
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

# ===== LOGIC KEY VIP =====
def check_vip_key_with_api(key: str, hwid: str):
    try:
        msg = key + hwid
        tool_hash = hmac.new(TOOL_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
        data = {"key": key, "hwid": hwid, "tool_hash": tool_hash}
        
        response = requests.post(VIP_API_URL, data=data, timeout=10)
        
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
    except requests.exceptions.RequestException as e:
        return False, f"Lỗi kết nối: {str(e)}", None
    except Exception as e:
        return False, f"Lỗi: {str(e)}", None

# ===== GIAO DIỆN RICH =====

def create_header() -> Panel:
    header_text = Text()
    header_text.append("KEY MANAGER", style="bold cyan")
    header_text.append(" - L-TOOL by CZERO", style="dim")
    return Panel(Align.center(header_text), box=box.DOUBLE, style="bold blue", padding=(0, 2))

def show_panel(title: str, message: str, style: str) -> None:
    console.print(Panel(Text(message, justify='left'), title=title, border_style=style, padding=(1, 2)))
    time.sleep(1.5)

# ===== QUẢN LÝ CHẠY CHÍNH =====
class LicenseManagerError(Exception):
    pass

class LicenseManager:
    def __init__(self) -> None:
        self.machine_id = get_stable_machine_id()
        self.cached_license = get_stored_license()
        self._last_runtime_check = 0.0
    
    def ensure_access(self) -> str:
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
                    show_panel('Key Hợp Lệ', f"{message}\nĐang vào tool...", 'green')
                    time.sleep(1)
                    return key_type
                else:
                    show_panel('Key Lỗi / Hết Hạn', message, 'red')
                    time.sleep(2)
                    return self._interactive_flow()
        return self._interactive_flow()
    
    def runtime_guard(self) -> None:
        now = time.time()
        if now - self._last_runtime_check < KEY_CHECK_INTERVAL:
            return
        self.cached_license = get_stored_license()
        valid, _, message = self._validate_license(self.cached_license)
        self._last_runtime_check = now
        if not valid:
            raise LicenseManagerError(message)
    
    def _validate_license(self, record: dict):
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
        while True:
            console.clear()
            console.print(create_header())
            menu = Table.grid(padding=(0, 1))
            menu.add_column()
            menu.add_row('[bold cyan]1.[/] Lấy Key Free (vượt link 2 bước, hạn 24h)')
            menu.add_row('[bold cyan]2.[/] Nhập Key VIP (không giới hạn)')
            title = f'Kích hoạt key - Mã máy: {self.machine_id}'
            console.print(Panel(menu, title=title, border_style='bright_magenta'))
            
            choice = Prompt.ask('Chọn chế độ', choices=['1', '2'])
            if choice == '1':
                result = self._handle_free_activation()
            else:
                result = self._handle_vip_activation()
            if result:
                return result
    
    def _handle_free_activation(self):
        # --- BƯỚC 1: LẤY TOKEN ---
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

        # --- BƯỚC 2: GỬI TOKEN LẤY KEY ---
        console.print("\n[cyan]Đang kiểm tra Token và tạo link vượt lần 2...[/]")
        try:
            # Gửi dạng data (form) để khớp với $_POST bên PHP
            payload = {"token": token_input, "machine": self.machine_id}
            resp2 = requests.post(VERIFY_TOKEN_URL, data=payload, timeout=10)
            link_key = resp2.text.strip() if resp2.status_code == 200 else f"Lỗi server: {resp2.status_code}"
        except Exception as e:
            link_key = f"Lỗi mạng: {e}"

        if "http" not in link_key:
            show_panel('Lỗi Xác Thực', f"Token sai hoặc hết hạn!\nPhản hồi: {link_key}", 'red')
            return None

        info2 = Table.grid(padding=0)
        info2.add_column(style='bold')
        info2.add_column()
        info2.add_row('Link lấy Key: ', link_key)
        console.print(Panel(info2, title='Bước 2: Lấy Key Chính Thức', border_style='bright_magenta', padding=(1, 2)))
        
        key_input = console.input('[yellow]Nhập KEY (Sau khi vượt link 2):[/] ').strip()

        # --- BƯỚC 3: KIỂM TRA KEY GIAO CHO NGƯỜI DÙNG ---
        valid, message = verify_free_key(key_input, self.machine_id)
        
        if valid:
            save_license_record('FREE', key_input)
            self.cached_license = get_stored_license()
            show_panel('Thành công', message, 'green')
            return 'FREE'
        
        show_panel('Thất bại', message, 'red')
        return None
    
    def _handle_vip_activation(self):
        vip_key = console.input('[yellow]Nhập Key VIP:[/] ').strip()
        console.print("\n[cyan]Đang kiểm tra key...[/]")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("[cyan]Kiểm tra với server...", total=None)
            valid, message, resp_data = check_vip_key_with_api(vip_key, self.machine_id)
            progress.update(task, completed=True)
        
        if valid:
            save_license_record('VIP', vip_key)
            self.cached_license = get_stored_license()
            show_panel('VIP kích hoạt', message, 'green')
            return 'VIP'
        show_panel('Lỗi', message, 'red')
        return None

# ===== KHỞI CHẠY =====
def run_key_activation_flow() -> str:
    manager = LicenseManager()
    return manager.ensure_access()

# ============================================================================
# GAME LOGIC
# ============================================================================ 

ATHLETE_NAMES = {
    "1": "Bậc thầy tấn công", 
    "2": "Quyền sắt", 
    "3": "Thợ lặn sâu", 
    "4": "Cơn lốc sân cỏ", 
    "5": "Hiệp sĩ phi nhanh", 
    "6": "Vua home run"
}

def calculate_base_bet(capital: float, num_tay: int, multiplier: float) -> float:
    """
    Tính tiền cược gốc dựa trên công thức bankroll
    
    Công thức: base_bet = capital × (multiplier - 1) / (multiplier^num_tay - 1)
    
    Args:
        capital: Vốn an toàn dành cho hệ thống tay
        num_tay: Số tay tối đa (ví dụ: 4)
        multiplier: Hệ số nhân khi thua (ví dụ: 12.0)
    
    Returns:
        Tiền cược gốc (base_bet)
    
    Example:
        >>> calculate_base_bet(1000, 4, 12.0)
        0.5304...
    """
    try:
        denominator = (multiplier ** num_tay - 1)
        if denominator == 0:
            return 1.0
        return capital * (multiplier - 1) / denominator
    except:
        return 1.0


def get_vietnam_time():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(tz)

def log_print(text):
    now = get_vietnam_time().strftime("%H:%M:%S")
    print(f"[{now}] {text}")

def wait_for_next_issue_timer(session, current_issue, asset_type):
    print(f"\n{Col.YELLOW}⏳ Đang chờ kết quả kỳ #{int(current_issue) + 1}...{Col.RESET}")
    start_wait = time.time()
    
    while True:
        try:
            ts = int(time.time() * 1000)
            url = f"{URL_RECENT_10}?asset={asset_type}&_={ts}"
            resp = make_api_request(session, "GET", url, max_retries=1)
            
            if resp and resp.get("code") == 0:
                recents = resp.get("data", {}).get("recent_10", [])
                if recents:
                    newest_id = str(recents[0]["issue_id"])
                    if newest_id != str(current_issue):
                        print(f"\r✅ {Col.GREEN}Đã có kết quả mới: #{newest_id}           {Col.RESET}\n")
                        return newest_id 
        except:
            pass

        elapsed = time.time() - start_wait
        sys.stdout.write(f"\r⏱️ Thời gian chờ: {Col.CYAN}{int(elapsed)}s{Col.RESET}")
        sys.stdout.flush()
        time.sleep(2) 

def load_history_data():
    global global_history_data
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                global_history_data = json.load(f)
        except: global_history_data = []
    else:
        global_history_data = []

def save_history_data_item(item):
    global global_history_data
    if not item.get('ranks'): return
    
    if not any(d.get('issue_id') == item.get('issue_id') for d in global_history_data):
        global_history_data.insert(0, item)
        if len(global_history_data) > 1000: 
            global_history_data.pop()
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(global_history_data, f)
        except: pass

def save_deep_learning_data(record):
    data_list = []
    if os.path.exists(TRAINING_FILE):
        try:
            with open(TRAINING_FILE, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
        except: data_list = []
    
    data_list.append(record)
    try:
        with open(TRAINING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, indent=2)
    except Exception as e:
        print(f"Lỗi lưu file Training: {e}")

def make_api_request(session, method, url, max_retries=3, **kwargs):
    default_headers = {
        "User-Agent": generate_user_agent(os='win', device_type='desktop'),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://sprintrun.win",
        "Referer": "https://sprintrun.win/",
    }
    if 'headers' in kwargs: kwargs['headers'].update(default_headers)
    else: kwargs['headers'] = default_headers

    for attempt in range(max_retries):
        try:
            response = session.request(method, url, timeout=15, **kwargs)
            if response.status_code in [200, 201]: return response.json()
            else: time.sleep(1)
        except Exception:
            if attempt == max_retries - 1: return None
            time.sleep(2)
    return None

def fetch_recent_100(session, asset_type):
    try:
        ts = int(time.time() * 1000)
        url = f"{URL_RECENT_100}?asset={asset_type}&_={ts}"
        resp = make_api_request(session, "GET", url)
        if resp and resp.get("code") == 0:
            return resp.get("data", {}).get("recent_100", [])
    except: pass
    return []

def get_current_game_info(session, asset_type):
    ts = int(time.time() * 1000)
    url = f"{URL_HOME}?asset={asset_type}&_={ts}"
    try:
        r = make_api_request(session, "GET", url)
        if r and r.get("code") == 0:
            return r.get("data") 
    except: pass
    return None

def analyze_and_predict_not_winner(session, current_history_10, asset_type, streak_loss, streak_win):
    global bot_bet_history_tracker, global_history_data

    history_100 = fetch_recent_100(session, asset_type)
    
    combined_data = []
    seen_ids = set()
    
    all_sources = current_history_10 + history_100 + global_history_data
    
    for item in all_sources:
        iid = str(item.get('issue_id', ''))
        ranks = item.get('ranks', []) or item.get('result', [])
        
        if iid and iid not in seen_ids and ranks and len(ranks) >= 6:
            seen_ids.add(iid)
            clean_item = {
                'issue_id': iid,
                'ranks': [int(x) for x in ranks], 
                'winner': int(ranks[0])
            }
            combined_data.append(clean_item)
    
    combined_data.sort(key=lambda x: int(x['issue_id']), reverse=True)
    
    if not combined_data:
        return 1

    last_match = combined_data[0]
    last_ranks = last_match['ranks'] 
    last_winner = last_ranks[0]
    
    danger_candidates = set()
    
    next_winner_counts = Counter()
    scan_depth = min(len(combined_data) - 1, 200)
    
    for i in range(1, scan_depth):
        prev = combined_data[i]
        curr = combined_data[i-1] 
        
        if prev['winner'] == last_winner:
            next_winner_counts[curr['winner']] += 1

    if next_winner_counts:
        most_common = next_winner_counts.most_common()
        for num, freq in most_common:
            total_occurences = sum(next_winner_counts.values())
            if freq / total_occurences > 0.15: 
                danger_candidates.add(num)
    
    danger_candidates.add(last_winner)

    final_choice = None

    if streak_loss > 0:
        print(f"   🛡️ BOT đang thua 🥹, đổi chiến thuật!...")
        
        
        recent_20 = combined_data[:20]
        recent_winners = [x['winner'] for x in recent_20]
        winner_counts_20 = Counter(recent_winners)
        
        candidates_pool = [1, 2, 3, 4, 5, 6]
        candidates_pool.sort(key=lambda x: winner_counts_20[x]) 
        
        for cand in candidates_pool:
            if cand not in danger_candidates:
                final_choice = cand
                print(f"   -> Chọn {cand} (Cold & Safe)")
                break
        
        if final_choice is None:
            final_choice = candidates_pool[0]

    else:
        
        top2 = last_ranks[1]
        top3 = last_ranks[2]
        top4 = last_ranks[3]
        
        priority_list = [top2, top3, top4]
        
        for cand in priority_list:
            if cand not in danger_candidates:
                final_choice = cand
                break
        
        if final_choice is None:
            top5 = last_ranks[4]
            top6 = last_ranks[5]
            if top5 not in danger_candidates: final_choice = top5
            else: final_choice = top6

    if len(bot_bet_history_tracker) > 0 and streak_loss > 0:
        last_bad_choice = bot_bet_history_tracker[-1]
        if final_choice == last_bad_choice:
            remain = [x for x in [1,2,3,4,5,6] if x != final_choice and x != last_winner]
            if remain:
                final_choice = remain[0]

    return final_choice

def get_detailed_result(session, issue_id, asset_type):
    ts = int(time.time() * 1000)
    url = f"{URL_ISSUE_RESULT}?issue={issue_id}&asset={asset_type}&_={ts}"
    try:
        r = make_api_request(session, "GET", url)
        if r and r.get("code") == 0:
             return r.get("data", {}).get("athlete_rank", [])
    except: pass
    return []

def get_wallet_balance(session, url, bet_type):
    user_id = session.headers.get("user-id")
    if not user_id: return None
    payload = {'user_id': int(user_id), 'source': 'home'}
    try:
        resp = make_api_request(session, "POST", url, json=payload)
        if not resp or resp.get("code") not in [0, 200]: return None
        assets = resp.get("data", {}).get("user_asset", {})
        balance_str = assets.get(bet_type)
        return float(balance_str) if balance_str is not None else None
    except: return None

def run_tool():
    global bot_bet_history_tracker, use_tay_system, num_tay, multiplier, base_bet
    
    try:
        # Sử dụng hệ thống key mới với giao diện Rich
        k_type = run_key_activation_flow()
        
        console.clear()
        console.print(f"\n[bold green]Tool đang chạy với quyền: {k_type}...[/]")
        console.print("[dim]Nhấn Ctrl+C để thoát[/]\n")
        time.sleep(1)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Đã dừng chương trình.[/]\n")
        sys.exit(0)
    except LicenseManagerError as e:
        console.print(f"\n[bold red]Lỗi License: {e}[/]\n")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Lỗi: {e}[/]\n")
        sys.exit(1)

    print_banner_ltool()

    # ========== BƯỚC 1: NHẬP LINK GAME ==========
    print(f"\n{Col.CYAN}{'='*60}{Col.RESET}")
    print(f"{Col.YELLOW}{Col.BRIGHT}  BƯỚC 1: ĐĂNG NHẬP TÀI KHOẢN{Col.RESET}")
    print(f"{Col.CYAN}{'='*60}{Col.RESET}")
    
    while True:
        url_input = input(f"\n{Col.GREEN}👉 Nhập Link Game (userId & secretKey):{Col.RESET}\n   ").strip()
        try:
            if 'userId=' not in url_input or 'secretKey=' not in url_input:
                print(f"{Col.RED}   ❌ Link sai định dạng. Vui lòng thử lại!{Col.RESET}")
                continue
            params = parse_qs(urlparse(url_input).query)
            user_id = params.get("userId", [None])[0] or url_input.split('userId=')[1].split('&')[0]
            secret_key = params.get("secretKey", [None])[0] or url_input.split('secretKey=')[1].split('&')[0]
            print(f"{Col.GREEN}   ✅ Đăng nhập thành công!{Col.RESET}")
            break
        except:
            print(f"{Col.RED}   ❌ Lỗi xử lý link. Vui lòng kiểm tra lại!{Col.RESET}")

    # ========== BƯỚC 2: CẤU HÌNH CƯỢC ==========
    print(f"\n{Col.CYAN}{'='*60}{Col.RESET}")
    print(f"{Col.YELLOW}{Col.BRIGHT}  BƯỚC 2: CẤU HÌNH CƯỢC{Col.RESET}")
    print(f"{Col.CYAN}{'='*60}{Col.RESET}")
    
    # Chọn loại tiền
    print(f"\n{Col.CYAN}┌─ Loại Tiền Cược:{Col.RESET}")
    print(f"{Col.CYAN}│{Col.RESET}  {Col.YELLOW}1.{Col.RESET} BUILD")
    print(f"{Col.CYAN}│{Col.RESET}  {Col.YELLOW}2.{Col.RESET} USDT")
    print(f"{Col.CYAN}│{Col.RESET}  {Col.YELLOW}3.{Col.RESET} WORLD")
    print(f"{Col.CYAN}└{'─'*40}{Col.RESET}")
    
    coin_choice = input(f"{Col.GREEN}👉 Chọn loại tiền (1/2/3) [mặc định: 1]: {Col.RESET}").strip() or "1"
    bet_type = {"1": "BUILD", "2": "USDT", "3": "WORLD"}.get(coin_choice, "BUILD")
    print(f"{Col.GREEN}   ✅ Đã chọn: {bet_type}{Col.RESET}")
    
    # Chọn hệ thống cược
    print(f"\n{Col.CYAN}┌─ Hệ Thống Cược:{Col.RESET}")
    print(f"{Col.CYAN}│{Col.RESET}  {Col.YELLOW}1.{Col.RESET} Cược thủ công (Nhập số tiền)")
    print(f"{Col.CYAN}│{Col.RESET}  {Col.YELLOW}2.{Col.RESET} Hệ thống TAY (Tự động tính theo vốn)")
    print(f"{Col.CYAN}└{'─'*40}{Col.RESET}")
    
    bet_system = input(f"{Col.GREEN}👉 Chọn hệ thống (1/2) [mặc định: 1]: {Col.RESET}").strip() or "1"
    use_tay_system = (bet_system == '2')
    
    if use_tay_system:
        # Cấu hình hệ thống TAY
        print(f"\n{Col.CYAN}┌─ Cấu Hình Hệ Thống TAY:{Col.RESET}")
        
        safe_capital_input = input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Vốn an toàn ({bet_type}) [Enter = bỏ qua]: {Col.RESET}").strip()
        
        if not safe_capital_input:
            # Bỏ qua TAY system, chuyển về thủ công
            print(f"{Col.CYAN}│{Col.RESET} {Col.YELLOW}⚠️  Bỏ qua hệ thống TAY, chuyển sang thủ công{Col.RESET}")
            print(f"{Col.CYAN}└{'─'*40}{Col.RESET}")
            use_tay_system = False
            
            print(f"\n{Col.CYAN}┌─ Cấu Hình Số Tiền:{Col.RESET}")
            base_bet = float(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Tiền cược gốc: {Col.RESET}"))
            multiplier = float(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Hệ số nhân khi thua [mặc định: 2]: {Col.RESET}").strip() or "2")
            num_tay = 0
            print(f"{Col.CYAN}└{'─'*40}{Col.RESET}")
        else:
            safe_capital = float(safe_capital_input)
            num_tay = int(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Số tay tối đa [mặc định: 4]: {Col.RESET}").strip() or "4")
            multiplier = float(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Hệ số nhân [mặc định: 12]: {Col.RESET}").strip() or "12")
            
            # Tính base_bet tự động
            base_bet = calculate_base_bet(safe_capital, num_tay, multiplier)
            print(f"{Col.CYAN}│{Col.RESET}")
            print(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}✅ Tiền cược gốc (tự động): {base_bet:.6f} {bet_type}{Col.RESET}")
            print(f"{Col.CYAN}│{Col.RESET} {Col.YELLOW}📊 Dự kiến các tay:{Col.RESET}")
            
            total_if_lose_all = 0
            for i in range(num_tay):
                bet_amount = base_bet * (multiplier ** i)
                total_if_lose_all += bet_amount
                print(f"{Col.CYAN}│{Col.RESET}    Tay {i+1}: {bet_amount:.6f} {bet_type}")
            
            print(f"{Col.CYAN}│{Col.RESET}    {Col.RED}━━━━━━━━━━━━━━━━━━━━━━━━━━{Col.RESET}")
            print(f"{Col.CYAN}│{Col.RESET}    {Col.RED}Tổng nếu thua hết: {total_if_lose_all:.6f} {bet_type}{Col.RESET}")
            print(f"{Col.CYAN}└{'─'*40}{Col.RESET}")
    else:
        # Cấu hình thủ công
        print(f"\n{Col.CYAN}┌─ Cấu Hình Số Tiền:{Col.RESET}")
        base_bet = float(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Tiền cược gốc: {Col.RESET}"))
        multiplier = float(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Hệ số nhân khi thua [mặc định: 2]: {Col.RESET}").strip() or "2")
        num_tay = 0
        print(f"{Col.CYAN}└{'─'*40}{Col.RESET}")
    
    # Điều kiện dừng
    print(f"\n{Col.CYAN}┌─ Điều Kiện Dừng:{Col.RESET}")
    max_lose_streak = int(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Chuỗi thua tối đa [mặc định: 0 = Không giới hạn]: {Col.RESET}").strip() or "0")
    stop_profit = float(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Lãi mục tiêu dừng [mặc định: 1000]: {Col.RESET}").strip() or "1000")
    stop_loss = float(input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Lỗ tối đa dừng [mặc định: 500]: {Col.RESET}").strip() or "500")
    print(f"{Col.CYAN}└{'─'*40}{Col.RESET}")


    
    # Chế độ nghỉ
    print(f"\n{Col.CYAN}┌─ Chế Độ Nghỉ Sau Thua:{Col.RESET}")
    use_skip = input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Có nghỉ khi thua không? (y/n): {Col.RESET}").lower()
    skip_loss_min = 0
    skip_loss_max = 0
    if use_skip == 'y':
        print(f"{Col.CYAN}│{Col.RESET}")
        print(f"{Col.CYAN}│{Col.RESET}  {Col.YELLOW}1.{Col.RESET} Tool tự động random nghỉ x ván")
        print(f"{Col.CYAN}│{Col.RESET}  {Col.YELLOW}2.{Col.RESET} Tự cài đặt (Nhập thủ công)")
        mode_skip = input(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}Lựa chọn (1/2): {Col.RESET}").strip()
        if mode_skip == '1':
            skip_loss_min = 6
            skip_loss_max = 10
            print(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}✅ Đã chọn: Tự động nghỉ 6-10 ván{Col.RESET}")
        else:
            skip_loss_min = int(input(f"{Col.CYAN}│{Col.RESET}   {Col.GREEN}Nghỉ Min (ván): {Col.RESET}"))
            skip_loss_max = int(input(f"{Col.CYAN}│{Col.RESET}   {Col.GREEN}Nghỉ Max (ván): {Col.RESET}"))
            print(f"{Col.CYAN}│{Col.RESET} {Col.GREEN}✅ Đã cài đặt: Nghỉ {skip_loss_min}-{skip_loss_max} ván{Col.RESET}")
    else:
        print(f"{Col.CYAN}│{Col.RESET} {Col.YELLOW}⚠️  Không sử dụng chế độ nghỉ{Col.RESET}")
    print(f"{Col.CYAN}└{'─'*40}{Col.RESET}")

    session = requests.Session()
    session.headers.update({
        "user-id": str(user_id),
        "user-secret-key": secret_key,
    })

    initial_bal = get_wallet_balance(session, URL_USER_INFO, bet_type)
    if initial_bal is None:
        print(f"{Col.RED}❌ Đăng nhập thất bại.{Col.RESET}"); sys.exit()

    print(f"\n{Col.GREEN}✅ Đã vào game! Vốn: {initial_bal} {bet_type}{Col.RESET}")
    
    stats = {
        "wins": 0, "losses": 0, "streak_loss": 0, "streak_win": 0,
        "max_streak_win": 0, "max_streak_loss": 0,
        "profit": 0.0, "last_issue": None, "last_bet": None,
        "base_bal": initial_bal, "curr_bet": base_bet,
        "skip": 0, "loss_skip": 0
    }
    
    load_history_data()
    print("\n" * 1) 
    
    startup_rounds_count = 0 
    
    first_info = get_current_game_info(session, bet_type)
    if first_info:
        stats["last_issue"] = str(int(first_info.get("issue_id")) - 1)
    else:
        stats["last_issue"] = "0"

    while True:
        try:
            new_issue_id = wait_for_next_issue_timer(session, stats["last_issue"], bet_type)
            
            stats["last_issue"] = new_issue_id
            
            detailed_ranks = get_detailed_result(session, new_issue_id, bet_type)
            if not detailed_ranks:
                ts = int(time.time() * 1000)
                r10 = make_api_request(session, "GET", f"{URL_RECENT_10}?asset={bet_type}&_={ts}")
                if r10:
                    data10 = r10.get("data", {}).get("recent_10", [])
                    for x in data10:
                        if str(x.get("issue_id")) == new_issue_id:
                            detailed_ranks = x.get("ranks", []) or x.get("result", [])
                            break
            
            if not detailed_ranks:
                print(f"{Col.RED}⚠️ Không lấy được kết quả chi tiết kỳ {new_issue_id}{Col.RESET}")
                continue

            winner = int(detailed_ranks[0])
            winner_name = ATHLETE_NAMES.get(str(winner), 'Unknown')
            
            current_balance_now = get_wallet_balance(session, URL_USER_INFO, bet_type) or 0.0
            stats["profit"] = current_balance_now - stats["base_bal"]

            full_record = {
                "issue_id": new_issue_id,
                "ranks": [int(x) for x in detailed_ranks],
                "result": detailed_ranks 
            }
            save_history_data_item(full_record)

            print(f"\n{Col.CYAN}{'-'*60}{Col.RESET}")
            
            if stats["last_bet"] and str(stats["last_bet"]["issue"]) == new_issue_id:
                bet_info = stats["last_bet"]
                choice_num = int(bet_info["room"])
                
                is_win = (winner != choice_num) 
                
                training_record = {
                    "issue_id": new_issue_id,
                    "winner": winner,
                    "ranks": detailed_ranks,
                    "bet_placed": choice_num,
                    "bet_amount": bet_info["total_amount"],
                    "result": "win" if is_win else "loss",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_deep_learning_data(training_record)

                profit_round = 0
                result_text = ""
                
                if is_win:
                    stats["wins"] += 1; stats["streak_win"] += 1; stats["streak_loss"] = 0
                    stats["curr_bet"] = base_bet 
                    profit_round = bet_info['total_amount'] * 0.15
                    result_text = f"{Col.GREEN}THẮNG{Col.RESET}"
                else:
                    stats["losses"] += 1; stats["streak_loss"] += 1; stats["streak_win"] = 0
                    stats["curr_bet"] = bet_info["unit_bet"] * multiplier
                    profit_round = -bet_info['total_amount']
                    result_text = f"{Col.RED}THUA{Col.RESET}"
                    if skip_loss_max > 0:
                        stats["loss_skip"] = random.randint(skip_loss_min, skip_loss_max)

                if stats["streak_win"] > stats["max_streak_win"]: stats["max_streak_win"] = stats["streak_win"]
                if stats["streak_loss"] > stats["max_streak_loss"]: stats["max_streak_loss"] = stats["streak_loss"]
                
                choice_name = ATHLETE_NAMES.get(str(choice_num), "Unknown")

                print(f"{Col.CYAN}Ván: {new_issue_id}{Col.RESET}")
                print(f"{Col.CYAN}Về nhất: {winner} - {winner_name}{Col.RESET}")
                print(f"{Col.CYAN}----------------------------{Col.RESET}")
                print(f" 🤖 BOT CƯỢC     : {Col.YELLOW}{choice_num} - {choice_name} (NOT WINNER){Col.RESET}")
                print(f" 💵 Tiền cược    : {bet_info['total_amount']}")
                print(f" 🎲 Kết quả      : {result_text}")
                print(f" 📈 Lãi ván      : {Col.GREEN if profit_round > 0 else Col.RED}{profit_round:+.4f}{Col.RESET}")
                print(f" 💰 Tổng lãi     : {Col.GREEN if stats['profit'] > 0 else Col.RED}{stats['profit']:+.4f}{Col.RESET}")
                print(f" 🏦 Số dư ban đầu: {stats['base_bal']:.2f}")
                print(f" 💳 Số dư hiện tại: {current_balance_now:.2f}")
                print(f" 📊 Tổng WIN | LOS: {Col.GREEN}{stats['wins']}{Col.RESET} | {Col.RED}{stats['losses']}{Col.RESET}")
                print(f" 🔥 MAX WIN | LOS : {Col.GREEN}{stats['max_streak_win']}{Col.RESET} | {Col.RED}{stats['max_streak_loss']}{Col.RESET}")

            else:
                print(f"{Col.CYAN}Ván: {new_issue_id}{Col.RESET}")
                print(f"{Col.CYAN}Về nhất: {winner} - {winner_name}{Col.RESET}")
                print(f"{Col.CYAN}----------------------------{Col.RESET}")
                print(f" 🤖 BOT CƯỢC: KHÔNG CƯỢC (Bỏ qua/Nghỉ)")
                print(f" 💳 Số dư hiện tại: {current_balance_now:.2f}")

            if max_lose_streak > 0 and stats["streak_loss"] >= max_lose_streak:
                print(f"\n{Col.RED}🛑 Dừng: Max thua liên tiếp.{Col.RESET}"); sys.exit()
            if stats["profit"] >= stop_profit:
                print(f"\n{Col.GREEN}🎉 Dừng: Đủ lãi.{Col.RESET}"); sys.exit()
            if stats["profit"] <= -stop_loss:
                print(f"\n{Col.RED}⚠️ Dừng: Cắt lỗ.{Col.RESET}"); sys.exit()

            ts = int(time.time() * 1000)
            url_recents = f"{URL_RECENT_10}?asset={bet_type}&_={ts}"
            resp10 = make_api_request(session, "GET", url_recents)
            recents = resp10.get("data", {}).get("recent_10", []) if resp10 else []
            
            if recents and str(recents[0]["issue_id"]) != new_issue_id:
                recents.insert(0, {"issue_id": new_issue_id, "ranks": detailed_ranks})

            print(f"\n{Col.YELLOW}📜 LỊCH SỬ 10 VÁN GẦN NHẤT:{Col.RESET}")
            print(f"{'Kỳ':<10} | {'NV Về Nhất':<20} | {'T1':<3} {'T2':<3} {'T3':<3} {'T4':<3} {'T5':<3} {'T6':<3}")
            print("-" * 80)
            for item in recents[:10]:
                r_id = item.get('issue_id')
                r = item.get('ranks', []) or item.get('result', [])
                if len(r) >= 6:
                    w_name = ATHLETE_NAMES.get(str(r[0]), "Unknown")
                    print(f"{r_id:<10} | {Col.BRIGHT}{w_name:<20}{Col.RESET} | {r[0]:<3} {r[1]:<3} {r[2]:<3} {r[3]:<3} {r[4]:<3} {r[5]:<3}")
            print("-" * 80)
            print("\n")

            
            if startup_rounds_count < 2:
                startup_rounds_count += 1
                print(f"\n{Col.YELLOW}🚀 ĐANG KHỞI ĐỘNG: Ván {startup_rounds_count}/2.{Col.RESET}")
                stats["last_bet"] = None
                continue 

            if stats["loss_skip"] > 0:
                print(f"\n{Col.YELLOW}💤 Bot đang nghỉ xả xui... Còn {stats['loss_skip']} ván.{Col.RESET}")
                stats["loss_skip"] -= 1
                stats["last_bet"] = None
                continue 

            if current_balance_now < stats["curr_bet"]:
                log_print("Hết tiền cược. Bỏ qua."); stats["last_bet"] = None; continue

            choice = analyze_and_predict_not_winner(
                session, 
                recents,
                bet_type,
                stats["streak_loss"],
                stats["streak_win"]
            )
            
            bot_bet_history_tracker.append(choice)
            if len(bot_bet_history_tracker) > 10:
                bot_bet_history_tracker.pop(0)

            next_issue = int(new_issue_id) + 1
            
            # Tính tiền cược theo hệ thống
            if use_tay_system:
                # Hệ thống TAY: base_bet × multiplier^loss_streak
                unit_bet = base_bet * (multiplier ** stats["streak_loss"])
                
                # Kiểm tra vượt quá số tay
                if stats["streak_loss"] >= num_tay:
                    print(f"\n{Col.RED}{'='*60}{Col.RESET}")
                    print(f"{Col.RED}🛑 ĐÃ THUA HẾT {num_tay} TAY! DỪNG LẠI ĐỂ BẢO VỆ VỐN.{Col.RESET}")
                    print(f"{Col.RED}{'='*60}{Col.RESET}")
                    print(f"{Col.YELLOW}📊 Thống kê cuối cùng:{Col.RESET}")
                    print(f"   Tổng WIN | LOS: {Col.GREEN}{stats['wins']}{Col.RESET} | {Col.RED}{stats['losses']}{Col.RESET}")
                    print(f"   Tổng lãi/lỗ: {Col.GREEN if stats['profit'] > 0 else Col.RED}{stats['profit']:+.4f}{Col.RESET}")
                    sys.exit()
            else:
                # Thủ công: sử dụng curr_bet
                unit_bet = stats["curr_bet"]
            
            unit_bet = round(unit_bet, 4)
            payload_bet_amount = int(unit_bet) if int(unit_bet) == unit_bet else unit_bet

            bet_payload = {
                "issue_id": next_issue, 
                "bet_group": "not_winner", 
                "asset_type": bet_type, 
                "athlete_id": int(choice), 
                "bet_amount": payload_bet_amount 
            }
            
            choice_name_log = ATHLETE_NAMES.get(str(choice), "Unknown")
            log_print(f"Đang đặt cược kỳ #{next_issue}:\n🤖 BOT cược {choice} ({choice_name_log}) | Tiền: {payload_bet_amount}")
            
            r = make_api_request(session, "POST", URL_BET, json=bet_payload)
            if r and r.get("code") == 0:
                 print(f"{Col.GREEN}✅ Đặt cược thành công.{Col.RESET}")
                 stats["last_bet"] = {
                     "issue": str(next_issue), "room": choice, 
                     "unit_bet": unit_bet, "total_amount": unit_bet
                 }
            else:
                err_msg = r.get('msg') if r else 'Unknown'
                if not err_msg: err_msg = r.get('message') 
                print(f"{Col.RED}⚠️ Lỗi API: {err_msg}{Col.RESET}")
                stats["last_bet"] = None


        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            print(f"Lỗi vòng lặp chính: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_tool()
