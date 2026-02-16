#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROJECT: KING OF SPEED - ADVANCED LOGIC PREDICTION SYSTEM
Version: 4.0 Pure Logic (No Random)
"""

import random
import sys
import os
import time
import threading
import hashlib
import hmac
import secrets
import json
import traceback
import io
import inspect
import numpy as np
import statistics
import collections
import datetime
import base64
import platform
import subprocess
import uuid
import requests
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
from colorama import init, Fore, Style


init(autoreset=True)

# Lấy thư mục làm việc (tương thích exec())
# Khi chạy bằng exec(), __file__ không tồn tại nên dùng getcwd()
# Support LTOOL_ROOT for auto-update system
if os.getenv("LTOOL_ROOT"):
    BASE_DIR = os.getenv("LTOOL_ROOT")
else:
    BASE_DIR = os.getcwd()

# Tạo thư mục config riêng
CONFIG_DIR = os.path.join(BASE_DIR, 'vuatocdooo_config')
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR, exist_ok=True)

CONFIG_ACC_FILE = os.path.join(CONFIG_DIR, 'cauhinhacc.txt')
CONFIG_GAME_FILE = os.path.join(CONFIG_DIR, 'lc-configch.txt')

# ============================================================================
# HỆ THỐNG KEY VERIFICATION (VIP ONLY)
# ============================================================================

# API Configuration
API_URL = "http://cyclonezerotool.x10.network/czero_api/key_tool.php"
TOOL_SECRET = "Luanvi1904_luonganh_tool_1237_Nguyen_Czero@123456789419_tao_key_haha_do_ma_doan_duoc_do_e_yeu_hi_hi_bruhhhhhhhhhhhhh_shibaaaaaaa_conchim_hi_hi"

def get_system_storage_path():
    """Lấy đường dẫn file lưu license (hidden)"""
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

def load_system_data():
    """Load license data từ file"""
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

def save_system_data(data):
    """Save license data vào file"""
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

def _generate_hardware_id_raw():
    """Tạo machine ID từ hardware"""
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

def get_stable_machine_id():
    """Lấy machine ID (stable)"""
    data = load_system_data()
    if data.get("machine_id"):
        return data["machine_id"]
    new_id = _generate_hardware_id_raw()
    data["machine_id"] = new_id
    save_system_data(data)
    return new_id

def save_license_record(key_type, key_value):
    """Lưu license"""
    data = load_system_data()
    if not data.get("machine_id"):
        data["machine_id"] = get_stable_machine_id()
    data["license"] = {
        "type": key_type,
        "key": key_value,
        "saved_date": datetime.datetime.now().strftime("%Y%m%d")
    }
    save_system_data(data)

def get_stored_license():
    """Lấy license đã lưu"""
    return load_system_data().get("license")

def check_vip_key_with_api(key, hwid):
    """Verify VIP key qua API"""
    try:
        msg = key + hwid
        tool_hash = hmac.new(TOOL_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
        data = {"key": key, "hwid": hwid, "tool_hash": tool_hash}
        
        response = requests.post(API_URL, data=data, timeout=10)
        
        # Kiểm tra response có phải JSON không
        try:
            resp = response.json()
        except ValueError:
            return False, f"Server trả về lỗi: {response.text[:100]}"
        
        status = resp.get("status", "unknown")
        
        # Map status codes từ server (xem server_api_analysis.md)
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
            return False, message
        
        # Verify response signature
        expire = resp.get("expire_date", "")
        server_hash = resp.get("response_hash", "")
        check_msg = expire + hwid
        local_hash = hmac.new(TOOL_SECRET.encode(), check_msg.encode(), hashlib.sha256).hexdigest()
        
        if local_hash != server_hash:
            return False, "Server response bị giả mạo!"
        
        # Tính số ngày còn lại
        time_left = resp.get("time_left", 0)
        days_left = time_left // 86400
        
        return True, f"VIP hợp lệ (Hạn: {expire}, còn {days_left} ngày)"
    except requests.exceptions.RequestException as e:
        return False, f"Lỗi kết nối: {str(e)}"
    except Exception as e:
        return False, f"Lỗi: {str(e)}"

def init_vip_key_system():
    """Khởi tạo VIP key system"""
    machine_id = get_stable_machine_id()
    stored = get_stored_license()
    
    # Kiểm tra key đã lưu
    if stored and stored.get('type') == 'VIP':
        valid, msg = check_vip_key_with_api(stored.get('key', ''), machine_id)
        if valid:
            print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")
            return True
        print(f"{Fore.YELLOW}⚠️  Key cũ không hợp lệ: {msg}{Style.RESET_ALL}")
    
    # Prompt nhập VIP key
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}  🔐 VIP KEY REQUIRED - VUATOCDOOO{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  Mã máy: {Fore.WHITE}{machine_id}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        vip_key = input(f"{Fore.YELLOW}Nhập VIP Key ({attempt}/{max_attempts}): {Style.RESET_ALL}").strip()
        
        if not vip_key:
            print(f"{Fore.RED}❌ Vui lòng nhập key!{Style.RESET_ALL}")
            continue
        
        print(f"{Fore.CYAN}⏳ Đang kiểm tra key...{Style.RESET_ALL}")
        valid, msg = check_vip_key_with_api(vip_key, machine_id)
        
        if valid:
            save_license_record('VIP', vip_key)
            print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Đang khởi động tool...{Style.RESET_ALL}\n")
            time.sleep(1)
            return True
        else:
            print(f"{Fore.RED}❌ {msg}{Style.RESET_ALL}")
            if attempt < max_attempts:
                retry = input(f"{Fore.YELLOW}Thử lại? (y/n): {Style.RESET_ALL}").strip().lower()
                if retry != 'y':
                    break
    
    print(f"{Fore.RED}>>> Tool yêu cầu VIP key để chạy!{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Liên hệ admin để mua key.{Style.RESET_ALL}\n")
    return False

# ============================================================================
# PHẦN 1: HỆ THỐNG LOGIC PHÂN TÍCH THUẦN TÚY (KHÔNG RANDOM)
# ============================================================================

class PureLogicAnalyzer:
    """Phân tích logic thuần túy - không có yếu tố ngẫu nhiên"""
    
    def __init__(self):
        self.history = []
        self.patterns = {}
        self.sequence_patterns = {}
        self.statistics = {
            'frequency': [0] * 6,
            'recency': [0] * 6,
            'streaks': {i: [] for i in range(1, 7)},
            'gaps': {i: [] for i in range(1, 7)},
            'transitions': np.zeros((6, 6)),
            'position_analysis': {i: [] for i in range(6)},  # Phân tích vị trí trong chuỗi
            'time_based_patterns': {}
        }
        self.last_update = time.time()
        
    def update_history(self, result):
        """Cập nhật lịch sử với phân tích chi tiết"""
        if 1 <= result <= 6:
            self.history.append(result)
            
            # Giới hạn lịch sử để hiệu suất
            if len(self.history) > 1000:
                self.history = self.history[-500:]
            
            # Cập nhật toàn bộ thống kê
            self._update_comprehensive_statistics(result)
            self._analyze_detailed_patterns()
            self._detect_mathematical_sequences()
            self._analyze_temporal_patterns()
            
            self.last_update = time.time()
    
    def _update_comprehensive_statistics(self, result):
        """Cập nhật thống kê toàn diện"""
        idx = result - 1
        
        # 1. Tần suất cơ bản
        self.statistics['frequency'][idx] += 1
        
        # 2. Recency với decay theo thời gian
        current_time = time.time()
        time_decay = 0.95  # Mỗi giây giảm 5%
        
        for i in range(6):
            if self.statistics['recency'][i] > 0:
                elapsed = current_time - self.last_update
                decay_factor = time_decay ** elapsed
                self.statistics['recency'][i] *= decay_factor
        
        self.statistics['recency'][idx] = 1.0
        
        # 3. Cập nhật ma trận chuyển tiếp Markov
        if len(self.history) >= 2:
            prev_idx = self.history[-2] - 1
            self.statistics['transitions'][prev_idx][idx] += 1
        
        # 4. Phân tích gap (khoảng cách giữa các lần xuất hiện)
        if result in self.statistics['gaps']:
            last_occurrence = self._find_last_occurrence(result)
            if last_occurrence is not None:
                gap = len(self.history) - last_occurrence - 1
                self.statistics['gaps'][result].append(gap)
                if len(self.statistics['gaps'][result]) > 20:
                    self.statistics['gaps'][result] = self.statistics['gaps'][result][-10:]
        
        # 5. Phân tích vị trí trong chuỗi
        sequence_pos = len(self.history) % 10  # Vị trí trong chuỗi 10 số
        self.statistics['position_analysis'][idx].append(sequence_pos)
    
    def _find_last_occurrence(self, number):
        """Tìm vị trí xuất hiện gần nhất của một số"""
        for i in range(len(self.history) - 2, -1, -1):
            if self.history[i] == number:
                return i
        return None
    
    def _analyze_detailed_patterns(self):
        """Phân tích pattern chi tiết từ độ dài 2 đến 5"""
        if len(self.history) < 6:
            return
        
        # Pattern độ dài 2-5
        for pattern_length in range(2, 6):
            for i in range(len(self.history) - pattern_length):
                pattern = tuple(self.history[i:i+pattern_length])
                
                if pattern not in self.patterns:
                    self.patterns[pattern] = {
                        'count': 0,
                        'next_numbers': [],
                        'positions': []
                    }
                
                self.patterns[pattern]['count'] += 1
                self.patterns[pattern]['positions'].append(i)
                
                # Lưu số tiếp theo nếu có
                if i + pattern_length < len(self.history):
                    next_num = self.history[i + pattern_length]
                    self.patterns[pattern]['next_numbers'].append(next_num)
    
    def _detect_mathematical_sequences(self):
        """Phát hiện các chuỗi toán học"""
        if len(self.history) < 4:
            return
        
        recent = self.history[-4:]
        
        # Kiểm tra cấp số cộng
        diffs = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
        if len(set(diffs)) == 1:  # Tất cả các hiệu bằng nhau
            seq_type = f"arithmetic_{diffs[0]}"
            if seq_type not in self.sequence_patterns:
                self.sequence_patterns[seq_type] = []
            self.sequence_patterns[seq_type].append(recent[-1])
        
        # Kiểm tra cấp số nhân (với làm tròn)
        if all(x != 0 for x in recent[:-1]):
            ratios = [recent[i+1] / recent[i] for i in range(len(recent)-1)]
            if max(ratios) - min(ratios) < 0.1:  # Sai số nhỏ
                seq_type = f"geometric_{ratios[0]:.2f}"
                if seq_type not in self.sequence_patterns:
                    self.sequence_patterns[seq_type] = []
                self.sequence_patterns[seq_type].append(recent[-1])
        
        # Kiểm tra chuỗi Fibonacci (mod 6)
        if len(self.history) >= 3:
            for i in range(len(self.history) - 2):
                a, b, c = self.history[i:i+3]
                if (a + b) % 6 == c % 6:
                    seq_type = "fibonacci_mod"
                    if seq_type not in self.sequence_patterns:
                        self.sequence_patterns[seq_type] = []
                    self.sequence_patterns[seq_type].append(c)
    
    def _analyze_temporal_patterns(self):
        """Phân tích pattern theo thời gian thực"""
        current_time = datetime.datetime.now()
        minute = current_time.minute
        second = current_time.second
        
        # Phân tích theo phút
        minute_key = f"minute_{minute}"
        if minute_key not in self.statistics['time_based_patterns']:
            self.statistics['time_based_patterns'][minute_key] = []
        
        if self.history:
            self.statistics['time_based_patterns'][minute_key].append(self.history[-1])
            
            # Giới hạn số lượng
            if len(self.statistics['time_based_patterns'][minute_key]) > 10:
                self.statistics['time_based_patterns'][minute_key] = self.statistics['time_based_patterns'][minute_key][-5:]

class DeterministicLogicPredictor:
    """Dự đoán hoàn toàn xác định dựa trên logic toán học"""
    
    def __init__(self):
        self.analyzer = PureLogicAnalyzer()
        self.prediction_history = []
        self.confidence_scores = []
        self.algorithm_weights = self._initialize_algorithm_weights()
        
    def _initialize_algorithm_weights(self):
        """Khởi tạo trọng số cho các thuật toán phân tích"""
        return {
            'frequency_analysis': 0.20,
            'pattern_recognition': 0.25,
            'markov_analysis': 0.20,
            'gap_analysis': 0.15,
            'mathematical_sequences': 0.10,
            'temporal_patterns': 0.10
        }
    
    def analyze_and_predict(self, num_predictions=3):
        """Phân tích logic và dự đoán hoàn toàn xác định"""
        if len(self.analyzer.history) < 5:
            return self._get_balanced_predictions(num_predictions)
        
        # Thu thập điểm số từ tất cả phương pháp phân tích
        all_scores = {}
        
        # 1. Phân tích tần suất
        freq_scores = self._frequency_analysis()
        
        # 2. Nhận diện pattern
        pattern_scores = self._pattern_recognition()
        
        # 3. Phân tích Markov
        markov_scores = self._markov_analysis()
        
        # 4. Phân tích gap
        gap_scores = self._gap_analysis()
        
        # 5. Chuỗi toán học
        math_scores = self._mathematical_sequence_analysis()
        
        # 6. Pattern thời gian
        time_scores = self._temporal_pattern_analysis()
        
        # Kết hợp tất cả điểm số với trọng số
        for i in range(1, 7):
            combined_score = (
                freq_scores.get(i, 0) * self.algorithm_weights['frequency_analysis'] +
                pattern_scores.get(i, 0) * self.algorithm_weights['pattern_recognition'] +
                markov_scores.get(i, 0) * self.algorithm_weights['markov_analysis'] +
                gap_scores.get(i, 0) * self.algorithm_weights['gap_analysis'] +
                math_scores.get(i, 0) * self.algorithm_weights['mathematical_sequences'] +
                time_scores.get(i, 0) * self.algorithm_weights['temporal_patterns']
            )
            all_scores[i] = combined_score
        
        # Tính độ tin cậy
        confidence = self._calculate_confidence(all_scores)
        self.confidence_scores.append(confidence)
        
        # Lấy dự đoán dựa trên điểm số
        predictions = self._get_predictions_from_scores(all_scores, num_predictions)
        
        # Ghi nhận dự đoán
        self.prediction_history.append({
            'predictions': predictions.copy(),
            'confidence': confidence,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        return predictions
    
    def _frequency_analysis(self):
        """Phân tích tần suất nâng cao"""
        scores = {}
        history = self.analyzer.history
        
        if not history:
            return {i: 1.0 for i in range(1, 7)}
        
        # Phân tích nhiều cửa sổ thời gian
        windows = [20, 50, 100]
        window_weights = [0.5, 0.3, 0.2]  # Cửa sổ nhỏ hơn có trọng số cao hơn
        
        for i in range(1, 7):
            score = 0
            total_weight = 0
            
            for window_size, weight in zip(windows, window_weights):
                if len(history) >= window_size:
                    window_data = history[-window_size:]
                    freq = window_data.count(i)
                    
                    # Điểm số tỷ lệ nghịch với tần suất (số ít xuất hiện có điểm cao)
                    if window_size > 0:
                        inverse_freq = (window_size - freq) / window_size
                        score += inverse_freq * weight
                        total_weight += weight
            
            if total_weight > 0:
                scores[i] = score / total_weight
            else:
                scores[i] = 0.5
        
        return scores
    
    def _pattern_recognition(self):
        """Nhận diện pattern với độ ưu tiên cao"""
        scores = {i: 0.0 for i in range(1, 7)}
        history = self.analyzer.history
        
        if len(history) < 3:
            return scores
        
        # Kiểm tra pattern độ dài 3 (ưu tiên cao nhất)
        if len(history) >= 3:
            last_three = tuple(history[-3:])
            if last_three in self.analyzer.patterns:
                pattern_data = self.analyzer.patterns[last_three]
                if pattern_data['next_numbers']:
                    counter = collections.Counter(pattern_data['next_numbers'])
                    total = sum(counter.values())
                    
                    # Pattern có độ tin cậy cao nếu xuất hiện nhiều lần
                    pattern_strength = min(1.0, pattern_data['count'] / 10)
                    
                    for num, count in counter.items():
                        probability = count / total
                        scores[num] = probability * pattern_strength * 1.5  # Tăng cường
        
        # Kiểm tra pattern độ dài 2
        if len(history) >= 2:
            last_two = tuple(history[-2:])
            if last_two in self.analyzer.patterns:
                pattern_data = self.analyzer.patterns[last_two]
                if pattern_data['next_numbers']:
                    counter = collections.Counter(pattern_data['next_numbers'])
                    total = sum(counter.values())
                    
                    pattern_strength = min(1.0, pattern_data['count'] / 15)
                    
                    for num, count in counter.items():
                        probability = count / total
                        # Cập nhật nếu điểm cao hơn
                        scores[num] = max(scores[num], probability * pattern_strength)
        
        return scores
    
    def _markov_analysis(self):
        """Phân tích Markov chain nâng cao"""
        scores = {i: 0.0 for i in range(1, 7)}
        history = self.analyzer.history
        
        if len(history) < 2:
            return scores
        
        transitions = self.analyzer.statistics['transitions']
        last_state = history[-1] - 1
        
        # Tính xác suất chuyển tiếp trực tiếp
        row_sum = transitions[last_state].sum()
        if row_sum > 0:
            for i in range(6):
                direct_prob = transitions[last_state][i] / row_sum
                scores[i+1] = direct_prob
        
        # Xem xét chuỗi Markov bậc 2
        if len(history) >= 3:
            prev_state = history[-2] - 1
            # Tính xác suất kết hợp
            for i in range(6):
                # P(C|A,B) ≈ P(C|B) * P(B|A)
                prob_c_given_b = transitions[last_state][i] / row_sum if row_sum > 0 else 1/6
                prev_row_sum = transitions[prev_state].sum()
                prob_b_given_a = transitions[prev_state][last_state] / prev_row_sum if prev_row_sum > 0 else 1/6
                
                combined_prob = prob_c_given_b * prob_b_given_a
                scores[i+1] = max(scores[i+1], combined_prob * 0.7)
        
        return scores
    
    def _gap_analysis(self):
        """Phân tích khoảng cách giữa các lần xuất hiện"""
        scores = {i: 0.0 for i in range(1, 7)}
        
        for num in range(1, 7):
            gaps = self.analyzer.statistics['gaps'][num]
            if gaps:
                avg_gap = statistics.mean(gaps)
                last_gap = gaps[-1] if gaps else 0
                
                # Số có gap trung bình lớn và gap gần đây lớn có điểm cao
                if avg_gap > 0:
                    # Điểm dựa trên độ "quá hạn"
                    overdue_score = min(1.0, last_gap / (avg_gap * 1.5))
                    scores[num] = overdue_score
        
        return scores
    
    def _mathematical_sequence_analysis(self):
        """Phân tích các chuỗi toán học"""
        scores = {i: 0.0 for i in range(1, 7)}
        history = self.analyzer.history
        
        if len(history) < 3:
            return scores
        
        # Kiểm tra cấp số cộng
        if len(history) >= 3:
            recent = history[-3:]
            diff1 = recent[1] - recent[0]
            diff2 = recent[2] - recent[1]
            
            if diff1 == diff2:
                next_predicted = recent[2] + diff1
                if 1 <= next_predicted <= 6:
                    scores[next_predicted] += 0.8
        
        # Kiểm tra cấp số nhân
        if len(history) >= 3 and all(x != 0 for x in history[-3:]):
            recent = history[-3:]
            ratio1 = recent[1] / recent[0]
            ratio2 = recent[2] / recent[1]
            
            if abs(ratio1 - ratio2) < 0.1:
                next_predicted = int(round(recent[2] * ratio1))
                if 1 <= next_predicted <= 6:
                    scores[next_predicted] += 0.6
        
        # Kiểm tra Fibonacci
        if len(history) >= 3:
            a, b, c = history[-3:]
            if (a + b) % 6 == c % 6:
                next_predicted = (b + c) % 6
                if next_predicted == 0:
                    next_predicted = 6
                scores[next_predicted] += 0.7
        
        return scores
    
    def _temporal_pattern_analysis(self):
        """Phân tích pattern theo thời gian"""
        scores = {i: 0.0 for i in range(1, 7)}
        current_time = datetime.datetime.now()
        minute = current_time.minute
        
        # Phân tích theo phút
        minute_key = f"minute_{minute}"
        if minute_key in self.analyzer.statistics['time_based_patterns']:
            minute_data = self.analyzer.statistics['time_based_patterns'][minute_key]
            if minute_data:
                counter = collections.Counter(minute_data)
                total = len(minute_data)
                
                for num, count in counter.items():
                    scores[num] = count / total * 0.5  # Trọng số thấp
        
        return scores
    
    def _calculate_confidence(self, scores):
        """Tính độ tin cậy của dự đoán"""
        if not scores:
            return 0.0
        
        values = list(scores.values())
        
        # Độ tin cậy cao nếu có số phân biệt rõ ràng
        max_score = max(values)
        second_max = sorted(values)[-2] if len(values) > 1 else 0
        
        if max_score > 0:
            confidence = (max_score - second_max) / max_score
            return min(1.0, max(0.0, confidence))
        
        return 0.0
    
    def _get_predictions_from_scores(self, scores, num_predictions):
        """Lấy dự đoán từ điểm số"""
        if not scores:
            return self._get_balanced_predictions(num_predictions)
        
        # Sắp xếp theo điểm số
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        predictions = []
        seen = set()
        
        # Lấy các số có điểm cao nhất
        for num, score in sorted_items:
            if num not in seen:
                predictions.append(num)
                seen.add(num)
                if len(predictions) >= num_predictions:
                    break
        
        # Nếu chưa đủ, thêm số có điểm cao tiếp theo
        if len(predictions) < num_predictions:
            remaining = [i for i in range(1, 7) if i not in seen]
            if remaining:
                # Thêm dựa trên phân phối điểm số
                remaining_scores = [scores.get(i, 0.01) for i in remaining]
                total = sum(remaining_scores)
                if total > 0:
                    probs = [s/total for s in remaining_scores]
                    
                    while len(predictions) < num_predictions and remaining:
                        # Chọn dựa trên xác suất
                        idx = np.random.choice(range(len(remaining)), p=probs)
                        predictions.append(remaining.pop(idx))
                        if remaining:
                            remaining_scores = [scores.get(i, 0.01) for i in remaining]
                            total = sum(remaining_scores)
                            probs = [s/total for s in remaining_scores] if total > 0 else [1/len(remaining)]*len(remaining)
        
        return predictions[:num_predictions]
    
    def _get_balanced_predictions(self, num_predictions):
        """Dự đoán cân bằng khi không đủ dữ liệu"""
        # Phân phối đều nhưng có tính đến số lần xuất hiện ít
        all_numbers = list(range(1, 7))
        
        if not self.analyzer.history:
            return all_numbers[:num_predictions]
        
        # Ưu tiên số ít xuất hiện
        freq = [self.analyzer.history.count(i) for i in range(1, 7)]
        if sum(freq) > 0:
            inverse_probs = [1/(f+1) for f in freq]
            total = sum(inverse_probs)
            probs = [p/total for p in inverse_probs]
            
            predictions = []
            temp_numbers = all_numbers.copy()
            temp_probs = probs.copy()
            
            while len(predictions) < num_predictions and temp_numbers:
                idx = np.random.choice(range(len(temp_numbers)), p=temp_probs)
                predictions.append(temp_numbers.pop(idx))
                if temp_numbers:
                    # Tính lại xác suất
                    temp_freq = [self.analyzer.history.count(i) for i in temp_numbers]
                    temp_inverse = [1/(f+1) for f in temp_freq]
                    temp_total = sum(temp_inverse)
                    temp_probs = [p/temp_total for p in temp_inverse] if temp_total > 0 else [1/len(temp_numbers)]*len(temp_numbers)
            
            return predictions
        else:
            return all_numbers[:num_predictions]
    
    def get_analysis_report(self):
        """Tạo báo cáo phân tích chi tiết"""
        if not self.analyzer.history:
            return "Chưa có đủ dữ liệu để phân tích"
        
        report = []
        report.append("=" * 60)
        report.append("BÁO CÁO PHÂN TÍCH LOGIC")
        report.append("=" * 60)
        
        # Thống kê cơ bản
        report.append(f"Tổng số mẫu: {len(self.analyzer.history)}")
        
        # Tần suất
        freq_text = "Tần suất: "
        for i in range(1, 7):
            count = self.analyzer.history.count(i)
            percentage = (count / len(self.analyzer.history)) * 100
            freq_text += f"{i}:{count}({percentage:.1f}%) "
        report.append(freq_text)
        
        # Pattern phổ biến
        if self.analyzer.patterns:
            report.append("\nPattern phổ biến:")
            sorted_patterns = sorted(self.analyzer.patterns.items(), 
                                   key=lambda x: x[1]['count'], 
                                   reverse=True)[:5]
            for pattern, data in sorted_patterns:
                if data['next_numbers']:
                    counter = collections.Counter(data['next_numbers'])
                    most_common = counter.most_common(1)[0]
                    report.append(f"  {pattern} → {most_common[0]} ({most_common[1]}/{data['count']})")
        
        # Chuỗi toán học phát hiện
        if self.analyzer.sequence_patterns:
            report.append("\nChuỗi toán học phát hiện:")
            for seq_type, numbers in self.analyzer.sequence_patterns.items():
                if numbers:
                    report.append(f"  {seq_type}: {numbers[-5:]}")
        
        # Độ tin cậy trung bình
        if self.confidence_scores:
            avg_confidence = statistics.mean(self.confidence_scores[-10:]) if len(self.confidence_scores) >= 10 else statistics.mean(self.confidence_scores)
            report.append(f"\nĐộ tin cậy trung bình (10 lần gần nhất): {avg_confidence:.2%}")
        
        return "\n".join(report)

# ============================================================================
# PHẦN 2: HỆ THỐNG GỐC (GIỮ NGUYÊN)
# ============================================================================

class DependencyManager:
    REQUIRED = {
        'pycurl': 'pycurl',
        'certifi': 'certifi',
    }
    
    @staticmethod
    def check_and_install():
        import subprocess
        import importlib
        
        for module_name, package_name in DependencyManager.REQUIRED.items():
            try:
                importlib.import_module(module_name)
            except ImportError:
                print(f"[*] Installing {package_name}...")
                try:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", package_name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    print(f"[!] Failed to install {package_name}: {e}")
                    return False
        return True

class SecurityMonitor:
    def __init__(self):
        self._suspicious_patterns = [
            'hook', 'inject', 'monkey', 'patch', 'frida',
            'mitmproxy', 'burp', 'intercept', 'proxy', 'debug',
            'trace', 'mitm', 'charles', 'fiddler'
        ]
        self._baseline_modules = set(sys.modules.keys())
        self._check_count = 0
    
    def check_environment(self):
        if sys.gettrace() is not None:
            return False, "Debugger detected"
        
        suspicious_vars = [
            'PYCHARM_HOSTED', 'VSCODE_CWD', 'DEBUGPY_PROCESS_ID',
            'PYTHONBREAKPOINT', 'PYTHONINSPECT'
        ]
        for var in suspicious_vars:
            if os.environ.get(var):
                return False, f"Suspicious env: {var}"
        
        self._check_count += 1
        if self._check_count % 10 == 0:
            current_modules = set(sys.modules.keys())
            new_modules = current_modules - self._baseline_modules
            for mod_name in new_modules:
                for pattern in self._suspicious_patterns:
                    if pattern in mod_name.lower():
                        return False, f"Suspicious module: {mod_name}"
        
        return True, "OK"
    
    def check_caller_stack(self, max_depth=10):
        try:
            frame = inspect.currentframe()
            for _ in range(3):
                if frame:
                    frame = frame.f_back
            
            depth = 0
            while frame and depth < max_depth:
                frame_info = inspect.getframeinfo(frame)
                filename = frame_info.filename.lower()
                func_name = frame.f_code.co_name.lower()
                
                for pattern in self._suspicious_patterns:
                    if pattern in filename or pattern in func_name:
                        return False, f"Suspicious caller: {pattern}"
                
                frame = frame.f_back
                depth += 1
            
            return True, "OK"
        except Exception as e:
            return False, f"Stack check error: {e}"
        finally:
            del frame

class CryptoEngine:
    def __init__(self, key=None):
        self._key = key or secrets.token_bytes(32)
        self._nonce_cache = set()
        self._nonce_max = 10000
    
    def get_key(self):
        return self._key
    
    def generate_signature(self, *components):
        timestamp = int(time.time() * 1000)
        nonce = secrets.token_hex(16)
        if len(self._nonce_cache) > self._nonce_max:
            self._nonce_cache.clear()
        
        message = "|".join(str(c) for c in components) + f"|{timestamp}|{nonce}"
        signature = hmac.new(
            self._key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'signature': signature,
            'timestamp': timestamp,
            'nonce': nonce
        }
    
    def verify_signature(self, signature, timestamp, nonce, 
                        *components, max_age=300000):
        if abs(int(time.time() * 1000) - timestamp) > max_age:
            return False, "Timestamp expired"
        if nonce in self._nonce_cache:
            return False, "Nonce replayed"
        message = "|".join(str(c) for c in components) + f"|{timestamp}|{nonce}"
        expected = hmac.new(
            self._key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return False, "Signature mismatch"
        self._nonce_cache.add(nonce)
        return True, "OK"
    
    @staticmethod
    def compute_hash(data):
        return hashlib.sha256(data).hexdigest()

class SecureRequestEngine:
    def __init__(self):
        self._crypto = CryptoEngine()
        self._monitor = SecurityMonitor()
        self._lock = threading.Lock()
        self._initialized = False
    
    def initialize(self):
        with self._lock:
            if self._initialized:
                return True
            
            try:
                import pycurl
                import certifi
                self.pycurl = pycurl
                self.certifi = certifi
                self._initialized = True
                return True
            except Exception as e:
                print(f"[!] PyCURL init failed: {e}")
                return False
    
    def execute_request(self, config):
        ok, reason = self._monitor.check_environment()
        if not ok:
            self._emergency_shutdown(f"Environment check failed: {reason}")
        
        ok, reason = self._monitor.check_caller_stack()
        if not ok:
            self._emergency_shutdown(f"Caller check failed: {reason}")
        
        if not self._initialized:
            if not self.initialize():
                return {"error": "Failed to initialize PyCURL"}
        
        url = config.get('url', '')
        method = config.get('method', 'GET').upper()
        headers = config.get('headers') or {}
        cookies = config.get('cookies')
        params = config.get('params')
        data = config.get('data')
        json_body = config.get('json')
        proxy = config.get('proxy')
        timeout = config.get('timeout', 15)
        verify = config.get('verify', True)
        
        if params:
            parsed = urlparse(url)
            query = dict(parse_qsl(parsed.query))
            query.update(params)
            url = urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, urlencode(query, doseq=True), parsed.fragment
            ))
        
        body_bytes = None
        if json_body is not None:
            body_bytes = json.dumps(json_body).encode('utf-8')
        elif data:
            if isinstance(data, dict):
                body_bytes = urlencode(data, doseq=True).encode('utf-8')
            elif isinstance(data, str):
                body_bytes = data.encode('utf-8')
            elif isinstance(data, (bytes, bytearray)):
                body_bytes = bytes(data)
        
        header_list = []
        for k, v in headers.items():
            header_list.append(f"{k}: {v}")
        
        if cookies:
            if isinstance(cookies, dict):
                cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            else:
                cookie_str = str(cookies)
            header_list.append(f"Cookie: {cookie_str}")
        
        if body_bytes and not any('content-type' in h.lower() for h in header_list):
            if json_body is not None:
                header_list.append("Content-Type: application/json")
            elif isinstance(data, dict):
                header_list.append("Content-Type: application/x-www-form-urlencoded")
        
        buf = io.BytesIO()
        header_buf = io.BytesIO()
        c = self.pycurl.Curl()
        
        try:
            c.setopt(self.pycurl.URL, url)
            c.setopt(self.pycurl.WRITEFUNCTION, buf.write)
            c.setopt(self.pycurl.HEADERFUNCTION, header_buf.write)
            c.setopt(self.pycurl.TIMEOUT, int(timeout))
            c.setopt(self.pycurl.CONNECTTIMEOUT, int(timeout // 2))
            c.setopt(self.pycurl.FOLLOWLOCATION, 1)
            c.setopt(self.pycurl.MAXREDIRS, 5)
            c.setopt(self.pycurl.NOSIGNAL, 1)
            
            if verify:
                try:
                    c.setopt(self.pycurl.CAINFO, self.certifi.where())
                except:
                    c.setopt(self.pycurl.SSL_VERIFYPEER, 0)
            else:
                c.setopt(self.pycurl.SSL_VERIFYPEER, 0)
                c.setopt(self.pycurl.SSL_VERIFYHOST, 0)
            
            if proxy:
                c.setopt(self.pycurl.PROXY, proxy)
            
            if method == 'GET':
                c.setopt(self.pycurl.HTTPGET, 1)
            elif method == 'POST':
                c.setopt(self.pycurl.POST, 1)
                if body_bytes:
                    c.setopt(self.pycurl.POSTFIELDS, body_bytes)
            else:
                c.setopt(self.pycurl.CUSTOMREQUEST, method)
                if body_bytes:
                    c.setopt(self.pycurl.POSTFIELDS, body_bytes)
            
            if header_list:
                c.setopt(self.pycurl.HTTPHEADER, header_list)
            
            if not any('user-agent' in h.lower() for h in header_list):
                c.setopt(self.pycurl.USERAGENT, "Mozilla/5.0 (SecureEngine/4.0)")
            
            c.perform()
            
            status = c.getinfo(self.pycurl.RESPONSE_CODE)
            body = buf.getvalue()
            headers_raw = header_buf.getvalue()
            
            return {
                'status': status,
                'body': body,
                'headers': headers_raw.decode('utf-8', errors='ignore'),
                'url': c.getinfo(self.pycurl.EFFECTIVE_URL),
                'error': None
            }
            
        except Exception as e:
            return {
                'status': 0,
                'body': b'',
                'headers': '',
                'url': url,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        finally:
            c.close()
            buf.close()
            header_buf.close()
    
    def _emergency_shutdown(self, reason):
        print(f"\n[!!!] SECURITY BREACH: {reason}", file=sys.stderr)
        os._exit(1)

class SecureSession:
    def __init__(self, engine, proxy=None, headers=None, cookiefile=None):
        self.engine = engine
        self.proxy = proxy
        self.headers = headers or {}
        self.cookiefile = cookiefile

    def request(self, method, url, **kwargs):
        if self.proxy and "proxy" not in kwargs:
            kwargs["proxy"] = self.proxy
        if self.headers:
            h = kwargs.get("headers", {})
            h.update(self.headers)
            kwargs["headers"] = h
        return self.engine.execute_request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

class SecureHTTP:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._engine = SecureRequestEngine()
        return cls._instance
    
    def request(self, url, method='GET', **kwargs):
        config = {
            'url': url,
            'method': method,
            **kwargs
        }
        return self._engine.execute_request(config)
    
    def get(self, url, **kwargs):
        return self.request(url, 'GET', **kwargs)
    
    def post(self, url, **kwargs):
        return self.request(url, 'POST', **kwargs)
    
    def put(self, url, **kwargs):
        return self.request(url, 'PUT', **kwargs)
    
    def delete(self, url, **kwargs):
        return self.request(url, 'DELETE', **kwargs)
    
    def create_session(self, proxy=None, headers=None, cookiefile=None):
        return SecureSession(
            self._engine,
            proxy=proxy,
            headers=headers,
            cookiefile=cookiefile
        )

# ============================================================================
# PHẦN 3: CÁC HÀM GIAO TIẾP VỚI API
# ============================================================================

NV = {
    1: 'Bậc thầy tấn công',
    2: 'Quyền sắt',
    3: 'Thợ lặn sâu',
    4: 'Cơn lốc sân cỏ',
    5: 'Hiếp sĩ phi nhanh',
    6: 'Vua home run'
}

def calculate_base_bet(capital: float, num_tay: int, multiplier: float) -> float:
    """
    Tính tiền cược gốc dựa trên công thức bankroll
    
    Công thức: base_bet = capital × (multiplier - 1) / (multiplier^num_tay - 1)
    """
    try:
        denominator = (multiplier ** num_tay - 1)
        if denominator == 0:
            return 1.0
        return capital * (multiplier - 1) / denominator
    except:
        return 1.0

def prints(r, g, b, text="text", end="\n"):
    print(f"\033[38;2;{r};{g};{b}m{text}\033[0m", end=end)

# Khởi tạo hệ thống Logic Predictor
logic_predictor = DeterministicLogicPredictor()

def bet_cdtd(headers, ki, kq, Coin, bet_amount, type_bet):
    try:
        json_data = {
            'issue_id': int(ki),
            'bet_group': type_bet,
            'asset_type': Coin,
            'athlete_id': kq,
            'bet_amount': bet_amount,
        }
        response = json.loads(http.post('https://api.sprintrun.win/sprint/bet', 
                                       headers=headers, 
                                       json=json_data)['body'].decode("utf-8"))
        if response['code'] == 0 and response['msg'] == 'ok':
            return True
        return False
    except Exception as e:
        prints(255, 0, 0, f'Lỗi khi đặt {Coin}: {e}')
        return False

def home(headers, Coin):
    params = {'asset': Coin}
    response = http.get('https://api.sprintrun.win/sprint/home', 
                       params=params, 
                       headers=headers)
    return response['body'].decode("utf-8")

def user_asset(headers):
    try:
        json_data = {
            'user_id': int(headers['user-id']),
            'source': 'home',
        }
        response = json.loads(http.post('https://wallet.3games.io/api/wallet/user_asset', 
                                       headers=headers, 
                                       json=json_data)['body'].decode('utf-8'))
        asset = {
            'USDT': response['data']['user_asset']['USDT'],
            'WORLD': response['data']['user_asset']['WORLD'],
            'BUILD': response['data']['user_asset']['BUILD']
        }
        return asset
    except Exception as e:
        prints(255, 0, 0, f'Lỗi khi lấy số dư: {e}')
        time.sleep(2)
        return user_asset(headers)

def info(headers, ki, Coin):
    try:
        params = {
            'issue': str(ki),
            'asset': Coin,
        }
        response = json.loads(http.get('https://api.sprintrun.win/sprint/issue_result', 
                                      params=params, 
                                      headers=headers)['body'].decode("utf-8"))
        if len(response['data']['athlete_rank']) > 0:
            return response
        return None
    except Exception as e:
        prints(255, 0, 0, f"Lỗi khi lấy thông tin kỳ: {e}")
        time.sleep(1)
        return info(headers, ki, Coin)

def check_result(headers, Coin, bot_chon, type_game):
    res = json.loads(home(headers, Coin))
    ki = res['data']['issue_id']
    
    while True:
        if int(res['data']['expire_seconds']) <= 1:
            prints(255, 255, 0, f'Bắt đầu ván chơi...         ', end='\r')
            break
        else:
            res = json.loads(home(headers, Coin))
            if 'data' in res:
                prints(255, 255, 0, 'Ván chơi còn ' + str(res['data']['expire_seconds']) + ' giây sẽ bắt đầu...', end='\r')
        time.sleep(0.5)
    
    time.sleep(8)
    re_end = info(headers, ki, Coin)
    
    if re_end and 'data' in re_end:
        prints(255, 255, 0, f'Kì {re_end["data"]["issue_id"]} - Người về nhất: {re_end["data"]["athlete_rank"][0]} {NV.get(int(re_end["data"]["athlete_rank"][0]), "Unknown")}')
        prints(5, 255, 0, f'Tổng đặt {re_end["data"]["my_total_bet"]:.10f} - tổng nhận: {Fore.GREEN + str(re_end["data"]["my_total_award"]) if re_end["data"]["my_total_award"] != 0 else Fore.RED + str(re_end["data"]["my_total_award"])}')
        
        json_data = {
            'issue_id': re_end['data']['issue_id'],
            'top1': re_end['data']['athlete_rank'][0],
            'my_total_bet': re_end['data']['my_total_bet'],
            'my_total_award': re_end['data']['my_total_award'],
            'kq': re_end['data']['athlete_rank'][0] in bot_chon if type_game == 'winner' else not re_end['data']['athlete_rank'][0] in bot_chon,
            'bot_chon': bot_chon,
        }
        
        # Cập nhật lịch sử cho logic predictor
        logic_predictor.analyzer.update_history(re_end['data']['athlete_rank'][0])
        
        return json_data
    
    return None

def vanchoi_logic(headers, Coin, history, he_so, bet_amount0, type_bet, So_nv):
    """Ván chơi sử dụng logic predictor"""
    res = json.loads(home(headers, Coin))
    ki = res['data']['issue_id']
    
    # Sử dụng logic predictor để dự đoán
    bot_chon = logic_predictor.analyze_and_predict(So_nv)
    
    prints(0, 255, 234, f'Logic System chọn: {bot_chon}, Loại: {type_bet}')
    
    # Hiển thị báo cáo phân tích
    if len(logic_predictor.analyzer.history) >= 10:
        prints(0, 255, 255, "Phân tích logic đang hoạt động...")
    
    # Tính toán số tiền đặt cược
    bet_amount = bet_amount0 / len(bot_chon) if bot_chon else bet_amount0
    
    if len(history) > 0:
        if history[0]['kq'] == False:
            bet_amount = history[0]['my_total_bet'] * he_so / len(bot_chon) if bot_chon else bet_amount0
    
    # Đặt cược
    success_count = 0
    for i in bot_chon:
        if bet_cdtd(headers, ki, i, Coin, bet_amount, type_bet):
            success_count += 1
    
    if success_count == 0:
        prints(255, 0, 0, "Lỗi: Không thể đặt cược!")
        return None
    
    # Kiểm tra kết quả
    data = check_result(headers, Coin, bot_chon, type_bet)
    return data

def vanchoi_random(headers, Coin, history, he_so, bet_amount0, type_bet, So_nv):
    """Ván chơi sử dụng random (dự phòng)"""
    res = json.loads(home(headers, Coin))
    ki = res['data']['issue_id']
    
    # Random chọn
    all_numbers = list(range(1, 7))
    bot_chon = random.sample(all_numbers, min(So_nv, 6))
    
    prints(255, 165, 0, f'Random chọn: {bot_chon}, Loại: {type_bet}')
    
    # Tính toán số tiền đặt cược
    bet_amount = bet_amount0 / len(bot_chon) if bot_chon else bet_amount0
    
    if len(history) > 0:
        if history[0]['kq'] == False:
            bet_amount = history[0]['my_total_bet'] * he_so / len(bot_chon) if bot_chon else bet_amount0
    
    # Đặt cược
    success_count = 0
    for i in bot_chon:
        if bet_cdtd(headers, ki, i, Coin, bet_amount, type_bet):
            success_count += 1
    
    if success_count == 0:
        prints(255, 0, 0, "Lỗi: Không thể đặt cược!")
        return None
    
    # Kiểm tra kết quả
    data = check_result(headers, Coin, bot_chon, type_bet)
    
    # Vẫn cập nhật lịch sử cho logic predictor
    if data and 'top1' in data:
        logic_predictor.analyzer.update_history(data['top1'])
    
    return data

# ============================================================================
# PHẦN 4: HÀM MAIN VÀ MENU
# ============================================================================

def banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # LTOOL ASCII Banner
    banner_text = r"""
██╗     ████████╗ ██████╗  ██████╗ ██╗     
██║     ╚══██╔══╝██╔═══██╗██╔═══██╗██║     
██║        ██║   ██║   ██║██║   ██║██║     
██║        ██║   ██║   ██║██║   ██║██║     
███████╗   ██║   ╚██████╔╝╚██████╔╝███████╗
╚══════╝   ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
    """
    
    # Print banner with gradient effect
    prints(0, 255, 255, banner_text)
    prints(255, 215, 0, "=" * 60)
    prints(0, 255, 255, ">> Advanced Gaming Platform - VUA TỐC ĐỘ")
    prints(255, 215, 0, "=" * 60)
    print()
    
    # Contact info
    prints(100, 200, 255, "  Zalo Group : ", end="")
    prints(255, 255, 255, "https://zalo.me/g/zgbloo300")
    prints(100, 200, 255, "  Developer  : ", end="")
    prints(255, 255, 255, "_LTA")
    
    print()
    prints(255, 215, 0, "=" * 60)
    prints(0, 255, 255, "PHIÊN BẢN: API.ALMODEL7.0.4.VN")
    prints(0, 255, 255, "TOOL SỬ DỤNG THUẬT TOÁN AL MODEL VÀ LOGIC DỰ ĐOÁN")
    prints(255, 215, 0, "=" * 60)
    print()

def cauhinh():
    if os.path.exists('cauhinhacc.txt'):
        prints(255, 255, 0, 'Bạn có muốn sử dụng lại thông tin Xworld đã lưu không? (y/n): ', end='')
        x = input().strip().lower()
        if x == 'n':
            str_info = """
    Hướng dẫn lấy link:
    1. Truy cập vào trang web xworld.io
    2. Đăng nhập tài khoản của bạn
    3. Tìm và nhấn vào chạy đua tốc độ
    4. Nhấn lập tức truy cập
    5. Copy link trang web đó và dán vào đây
"""
            prints(218, 255, 125, str_info)
            prints(247, 255, 97, "═" * 47)
            prints(125, 255, 168, '📋 Nhập link của bạn: ', end=' ')
            link = input().strip()
            
            try:
                user_id = link.split('&')[0].split('?userId=')[1]
                user_secretkey = link.split('&')[1].split('secretKey=')[1]
                
                prints(218, 255, 125, f'    User id của bạn là {user_id}')
                prints(218, 255, 125, f'    User secret key của bạn là {user_secretkey}')
                
                json_data = {
                    'user-id': user_id,
                    'user-secret-key': user_secretkey,
                }
                
                with open('cauhinhacc.txt', 'w+', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=4, ensure_ascii=False)
                    prints(5, 255, 0, 'Đã lưu dữ liệu vào file cauhinhacc.txt')
                    
            except Exception as e:
                prints(255, 0, 0, f'Lỗi khi phân tích link: {e}')
                prints(255, 255, 0, 'Vui lòng nhập đúng định dạng link!')
                return
    else:
        str_info = """
    Hướng dẫn lấy link:
    1. Truy cập vào trang web xworld.io
    2. Đăng nhập tài khoản của bạn
    3. Tìm và nhấn vào chạy đua tốc độ
    4. Nhấn lập tức truy cập
    5. Copy link trang web đó và dán vào đây
"""
        prints(218, 255, 125, str_info)
        prints(247, 255, 97, "═" * 47)
        prints(125, 255, 168, '📋 Nhập link của bạn: ', end=' ')
        link = input().strip()
        
        try:
            user_id = link.split('&')[0].split('?userId=')[1]
            user_secretkey = link.split('&')[1].split('secretKey=')[1]
            
            prints(218, 255, 125, f'    User id của bạn là {user_id}')
            prints(218, 255, 125, f'    User secret key của bạn là {user_secretkey}')
            
            json_data = {
                'user-id': user_id,
                'user-secret-key': user_secretkey,
            }
            
            with open(CONFIG_ACC_FILE, 'w+', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
                prints(5, 255, 0, f'Đã lưu dữ liệu vào {CONFIG_ACC_FILE}')
                
        except Exception as e:
            prints(255, 0, 0, f'Lỗi khi phân tích link: {e}')
            prints(255, 255, 0, 'Vui lòng nhập đúng định dạng link!')
            return
    
    # Cấu hình game
    if os.path.exists(CONFIG_GAME_FILE):
        prints(255, 255, 0, 'Bạn có muốn sử dụng lại cấu hình đã lưu không? (y/n): ', end='')
        x = input().strip().lower()
        if x == 'n':
            str_coin = """
    Nhập loại tiền mà bạn muốn chơi:
        1. USDT
        2. BUILD
        3. WORLD
"""
            prints(219, 237, 138, str_coin)
            
            while True:
                prints(125, 255, 168, 'Nhập loại tiền (1=USDT, 2=BUILD, 3=WORLD) [mặc định: 2]: ', end=' ')
                x = input().strip() or '2'
                
                if x in ['1', '2', '3']:
                    if x == '1':
                        Coin = 'USDT'
                    elif x == '2':
                        Coin = 'BUILD'
                    else:
                        Coin = 'WORLD'
                    break
                else:
                    prints(247, 30, 30, 'Nhập sai, vui lòng nhập lại ...')
            
            try:
                # Chọn hệ thống cược
                prints(255, 255, 0, '''
    === HỆ THỐNG CƯỢC ===
    1. Cược thủ công (Nhập số tiền)
    2. Hệ thống TAY (Tự động tính theo vốn)
''')
                bet_system = input('Chọn hệ thống (1/2) [mặc định: 1]: ').strip() or '1'
                use_tay_system = (bet_system == '2')
                
                if use_tay_system:
                    prints(0, 255, 255, '\n--- CẤU HÌNH HỆ THỐNG TAY ---')
                    safe_capital_input = input(f'Vốn an toàn ({Coin}) [Enter = bỏ qua]: ').strip()
                    
                    if not safe_capital_input:
                        prints(255, 255, 0, '⚠️  Bỏ qua hệ thống TAY, chuyển sang thủ công')
                        use_tay_system = False
                        bet_amount0 = float(input(f'Nhập số {Coin} muốn đặt: '))
                        he_so = float(input('Nhập hệ số cược sau thua [mặc định: 2]: ').strip() or '2')
                        num_tay = 0
                    else:
                        safe_capital = float(safe_capital_input)
                        num_tay = int(input('Số tay tối đa [mặc định: 4]: ').strip() or '4')
                        he_so = float(input('Hệ số nhân [mặc định: 12]: ').strip() or '12')
                        
                        bet_amount0 = calculate_base_bet(safe_capital, num_tay, he_so)
                        prints(0, 255, 0, f'✅ Tiền cược gốc (tự động): {bet_amount0:.6f} {Coin}')
                        prints(255, 255, 0, '📊 Dự kiến:')
                        for i in range(num_tay):
                            prints(255, 255, 255, f'  Tay {i+1}: {bet_amount0 * (he_so**i):.6f} {Coin}')
                        total_risk = sum(bet_amount0 * (he_so**i) for i in range(num_tay))
                        prints(255, 0, 0, f'  Tổng nếu thua hết: {total_risk:.6f} {Coin}')
                else:
                    bet_amount0 = float(input(f'Nhập số {Coin} muốn đặt: '))
                    he_so = float(input('Nhập hệ số cược sau thua [mặc định: 2]: ').strip() or '2')
                    num_tay = 0
                
                prints(255, 255, 0, '''
    1. Đặt vào "Ai là quán quân"
    2. Đặt vào "Ai không là quán quân"
''')
                
                type_choice = input('Chọn loại đặt (1/2): ').strip()
                type_bet = 'winner' if type_choice == '1' else 'not_winner'
                
                So_nv = int(input('Đặt vào bao nhiêu người (1-6): '))
                So_nv = max(1, min(6, So_nv))
                
                json_config = {
                    'Coin': Coin,
                    'he_so': he_so,
                    'bet_amount0': bet_amount0,
                    'type_bet': type_bet,
                    'So_nv': So_nv,
                    'use_tay_system': use_tay_system,
                    'num_tay': num_tay if use_tay_system else 0,
                }
                
                with open('lc-configch.txt', 'w+', encoding='utf-8') as f:
                    json.dump(json_config, f, indent=4, ensure_ascii=False)
                    prints(5, 255, 0, 'Đã lưu cấu hình vào file lc-configch.txt')
                    
            except ValueError as e:
                prints(255, 0, 0, f'Lỗi nhập số: {e}')
                return
    else:
        str_coin = """
    Nhập loại tiền mà bạn muốn chơi:
        1. USDT
        2. BUILD
        3. WORLD
"""
        prints(219, 237, 138, str_coin)
        
        while True:
            prints(125, 255, 168, 'Nhập loại tiền (1=USDT, 2=BUILD, 3=WORLD) [mặc định: 2]: ', end=' ')
            x = input().strip() or '2'
            
            if x in ['1', '2', '3']:
                if x == '1':
                    Coin = 'USDT'
                elif x == '2':
                    Coin = 'BUILD'
                else:
                    Coin = 'WORLD'
                break
            else:
                prints(247, 30, 30, 'Nhập sai, vui lòng nhập lại ...')
        
        try:
            # Chọn hệ thống cược
            prints(255, 255, 0, '''
    === HỆ THỐNG CƯỢC ===
    1. Cược thủ công (Nhập số tiền)
    2. Hệ thống TAY (Tự động tính theo vốn)
''')
            bet_system = input('Chọn hệ thống (1/2) [mặc định: 1]: ').strip() or '1'
            use_tay_system = (bet_system == '2')
            
            if use_tay_system:
                prints(0, 255, 255, '\n--- CẤU HÌNH HỆ THỐNG TAY ---')
                safe_capital_input = input(f'Vốn an toàn ({Coin}) [Enter = bỏ qua]: ').strip()
                
                if not safe_capital_input:
                    prints(255, 255, 0, '⚠️  Bỏ qua hệ thống TAY, chuyển sang thủ công')
                    use_tay_system = False
                    bet_amount0 = float(input(f'Nhập số {Coin} muốn đặt: '))
                    he_so = float(input('Nhập hệ số cược sau thua [mặc định: 2]: ').strip() or '2')
                    num_tay = 0
                else:
                    safe_capital = float(safe_capital_input)
                    num_tay = int(input('Số tay tối đa [mặc định: 4]: ').strip() or '4')
                    he_so = float(input('Hệ số nhân [mặc định: 12]: ').strip() or '12')
                    
                    bet_amount0 = calculate_base_bet(safe_capital, num_tay, he_so)
                    prints(0, 255, 0, f'✅ Tiền cược gốc (tự động): {bet_amount0:.6f} {Coin}')
                    prints(255, 255, 0, '📊 Dự kiến:')
                    for i in range(num_tay):
                        prints(255, 255, 255, f'  Tay {i+1}: {bet_amount0 * (he_so**i):.6f} {Coin}')
                    total_risk = sum(bet_amount0 * (he_so**i) for i in range(num_tay))
                    prints(255, 0, 0, f'  Tổng nếu thua hết: {total_risk:.6f} {Coin}')
            else:
                bet_amount0 = float(input(f'Nhập số {Coin} muốn đặt: '))
                he_so = float(input('Nhập hệ số cược sau thua [mặc định: 2]: ').strip() or '2')
                num_tay = 0
            
            prints(255, 255, 0, '''
    1. Đặt vào "Ai là quán quân"
    2. Đặt vào "Ai không là quán quân"
''')
            
            type_choice = input('Chọn loại đặt (1/2): ').strip()
            type_bet = 'winner' if type_choice == '1' else 'not_winner'
            
            So_nv = int(input('Đặt vào bao nhiêu người (1-6): '))
            So_nv = max(1, min(6, So_nv))
            
            json_config = {
                'Coin': Coin,
                'he_so': he_so,
                'bet_amount0': bet_amount0,
                'type_bet': type_bet,
                'So_nv': So_nv,
                'use_tay_system': use_tay_system,
                'num_tay': num_tay if use_tay_system else 0,
            }
            
            with open(CONFIG_GAME_FILE, 'w+', encoding='utf-8') as f:
                json.dump(json_config, f, indent=4, ensure_ascii=False)
                prints(5, 255, 0, f'Đã lưu cấu hình vào {CONFIG_GAME_FILE}')
                
        except ValueError as e:
            prints(255, 0, 0, f'Lỗi nhập số: {e}')
            return

def main_logic():
    """Hàm main sử dụng hệ thống logic"""
    # Kiểm tra VIP key trước khi chạy tool
    if not init_vip_key_system():
        sys.exit(1)
    
    banner()
    
    try:
        # Đọc thông tin đăng nhập
        with open(CONFIG_ACC_FILE, 'r', encoding='utf-8') as f:
            re = json.loads(f.read())
        user_id, user_secretkey = re['user-id'], re['user-secret-key']
        
        # Đọc cấu hình game
        with open(CONFIG_GAME_FILE, 'r', encoding='utf-8') as f:
            re = json.loads(f.read())
        Coin = re['Coin']
        he_so = re['he_so']
        bet_amount0 = re['bet_amount0']
        type_bet = re['type_bet']
        So_nv = re['So_nv']
        # Load tay system config (backward compatible)
        use_tay_system = re.get('use_tay_system', False)
        num_tay = re.get('num_tay', 0)
        
    except Exception as e:
        prints(255, 0, 0, f"Lỗi đọc cấu hình: {e}")
        prints(255, 255, 0, 'Hãy cấu hình trước khi chạy tool!')
        time.sleep(3)
        return
    
    # Tạo headers
    headers = {
        'accept': '*/*',
        'accept-language': 'vi,en;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://sprintrun.win',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36',
        'user-id': str(user_id),
        'user-login': 'login_v2',
        'user-secret-key': user_secretkey,
    }
    
    # Khởi tạo thống kê
    stats = {
        'win': 0,
        'lose': 0,
        'win_streak': 0,
        'max_win_streak': 0,
        'lose_streak': 0,
        'max_lose_streak': 0,
        'earn': 0,
        'logic_accuracy': 0.0,
        'total_bet': 0.0,
        'total_win': 0.0
    }
    
    history = []
    logic_success = 0
    logic_total = 0
    
    prints(0, 255, 0, "HỆ THỐNG LOGIC PREDICTION ĐÃ SẴN SÀNG!")
    prints(0, 255, 0, f"Coin: {Coin}, Số người đặt: {So_nv}, Loại: {type_bet}")
    print()
    
    try:
        while True:
            print('-' * 60)
            
            # Hiển thị số dư
            try:
                asset = user_asset(headers)
                prints(0, 255, 238, f'USDT: {asset["USDT"]:.4f} | WORLD: {asset["WORLD"]:.4f} | BUILD: {asset["BUILD"]:.4f}')
            except:
                prints(255, 165, 0, "Đang tải số dư...")
            
            # Hiển thị thống kê
            total_games = stats['win'] + stats['lose']
            if total_games > 0:
                win_rate = (stats['win'] / total_games) * 100
                if logic_total > 0:
                    logic_accuracy = (logic_success / logic_total) * 100
                    stats['logic_accuracy'] = logic_accuracy
                
                prints(5, 255, 0, f"Thắng: {stats['win']}/{total_games} ({win_rate:.2f}%)")
                prints(5, 255, 0, f"Chuỗi thắng: {stats['win_streak']} (Max: {stats['max_win_streak']})")
                prints(5, 255, 0, f"Chuỗi thua: {stats['lose_streak']} (Max: {stats['max_lose_streak']})")
                
                if stats['earn'] < 0:
                    prints(255, 0, 0, f'Lời/lỗ: {stats["earn"]:.10f}')
                else:
                    prints(0, 255, 0, f'Lời/lỗ: {stats["earn"]:.10f}')
                
                if logic_total > 0:
                    prints(0, 255, 255, f'Độ chính xác Logic System: {logic_accuracy:.2f}%')
            
            # Hiển thị báo cáo phân tích nếu có đủ dữ liệu
            if len(logic_predictor.analyzer.history) >= 10:
                if total_games % 5 == 0:
                    prints(255, 215, 0, "\n" + logic_predictor.get_analysis_report())
            
            # Chọn chế độ chơi dựa trên độ tin cậy
            use_logic = True
            if len(logic_predictor.analyzer.history) < 10:
                prints(255, 165, 0, "Đang thu thập dữ liệu (cần ít nhất 10 mẫu)...")
            elif logic_total > 10 and stats['logic_accuracy'] < 40:
                prints(255, 165, 0, "Logic System độ chính xác thấp, chuyển sang random...")
                use_logic = False
            
            # Thực hiện ván chơi
            if use_logic:
                res = vanchoi_logic(headers, Coin, history, he_so, bet_amount0, type_bet, So_nv)
                logic_total += 1
            else:
                res = vanchoi_random(headers, Coin, history, he_so, bet_amount0, type_bet, So_nv)
            
            if res:
                history.insert(0, res)
                
                # Cập nhật thống kê
                if res['kq']:
                    stats['win'] += 1
                    stats['win_streak'] += 1
                    stats['max_win_streak'] = max(stats['win_streak'], stats['max_win_streak'])
                    stats['lose_streak'] = 0
                    
                    if use_logic:
                        logic_success += 1
                else:
                    stats['lose'] += 1
                    stats['lose_streak'] += 1
                    stats['max_lose_streak'] = max(stats['max_lose_streak'], stats['lose_streak'])
                    stats['win_streak'] = 0
                
                # Cập nhật lợi nhuận
                profit = -1 * res['my_total_bet'] + res['my_total_award']
                stats['earn'] += profit
                stats['total_bet'] += res['my_total_bet']
                stats['total_win'] += res['my_total_award']
                
                # Tự động lưu checkpoint
                if (stats['win'] + stats['lose']) % 10 == 0:
                    checkpoint = {
                        'stats': stats,
                        'history_length': len(history),
                        'logic_data': {
                            'analyzer_history': logic_predictor.analyzer.history[-50:],
                            'patterns_count': len(logic_predictor.analyzer.patterns),
                            'confidence_scores': logic_predictor.confidence_scores[-20:]
                        },
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                    try:
                        with open('logic_checkpoint.json', 'w', encoding='utf-8') as f:
                            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
                        prints(0, 255, 0, '✓ Đã lưu checkpoint logic system')
                    except:
                        pass
                
                # Kiểm tra số dư
                if stats['earn'] < -bet_amount0 * 10:  # Thua quá nhiều
                    prints(255, 0, 0, "CẢNH BÁO: Đang thua nhiều, cân nhắc dừng lại!")
                
            else:
                prints(255, 0, 0, "Lỗi trong ván chơi, thử lại...")
                time.sleep(5)
            
            # Nghỉ giữa các ván
            time.sleep(2)
            
    except KeyboardInterrupt:
        prints(255, 255, 0, "\n\nĐã dừng bởi người dùng")
        
        # Lưu thống kê cuối cùng
        final_stats = {
            'final_stats': stats,
            'logic_performance': {
                'total_predictions': logic_total,
                'successful_predictions': logic_success,
                'accuracy': (logic_success / logic_total * 100) if logic_total > 0 else 0
            },
            'analyzer_data': {
                'total_history': len(logic_predictor.analyzer.history),
                'patterns_detected': len(logic_predictor.analyzer.patterns),
                'sequence_patterns': len(logic_predictor.analyzer.sequence_patterns)
            },
            'exit_time': datetime.datetime.now().isoformat()
        }
        
        try:
            with open('final_stats.json', 'w', encoding='utf-8') as f:
                json.dump(final_stats, f, indent=2, ensure_ascii=False)
            prints(0, 255, 0, "Đã lưu thống kê cuối cùng")
        except:
            pass
        
    except Exception as e:
        prints(255, 0, 0, f"Lỗi không mong muốn: {e}")
        traceback.print_exc()

def main_random():
    """Hàm main sử dụng random (legacy)"""
    banner()
    
    try:
        with open('cauhinhacc.txt', 'r', encoding='utf-8') as f:
            re = json.loads(f.read())
        user_id, user_secretkey = re['user-id'], re['user-secret-key']
        
        with open('lc-configch.txt', 'r', encoding='utf-8') as f:
            re = json.loads(f.read())
        Coin = re['Coin']
        he_so = re['he_so']
        bet_amount0 = re['bet_amount0']
        type_bet = re['type_bet']
        So_nv = re['So_nv']
        
    except Exception as e:
        prints(255, 0, 0, f"Lỗi: {e}")
        prints(255, 255, 0, 'Hãy cấu hình trước khi chạy tool')
        return
    
    headers = {
        'accept': '*/*',
        'accept-language': 'vi,en;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://sprintrun.win',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36',
        'user-id': str(user_id),
        'user-login': 'login_v2',
        'user-secret-key': user_secretkey,
    }
    
    stats = {
        'win': 0,
        'lose': 0,
        'win_streak': 0,
        'max_win_streak': 0,
        'lose_streak': 0,
        'max_lose_streak': 0,
        'earn': 0,
    }
    
    history = []
    
    try:
        while True:
            print('-' * 47)
            
            try:
                asset = user_asset(headers)
                prints(0, 255, 238, f'USDT: {asset["USDT"]:.4f} | WORLD: {asset["WORLD"]:.4f} | BUILD: {asset["BUILD"]:.4f}')
            except:
                pass
            
            total = stats['win'] + stats['lose']
            if total > 0:
                win_rate = (stats['win'] / total) * 100
                prints(5, 255, 0, f"Thắng: {stats['win']}/{total} ({win_rate:.2f}%)")
                prints(5, 255, 0, f'Chuỗi thắng: {stats["win_streak"]} (Max: {stats["max_win_streak"]})')
                prints(5, 255, 0, f'Chuỗi thua: {stats["lose_streak"]} (Max: {stats["max_lose_streak"]})')
                
                if stats['earn'] < 0:
                    prints(255, 0, 0, f'Lời/lỗ: {stats["earn"]:.10f}')
                else:
                    prints(5, 255, 0, f'Lời/lỗ: {stats["earn"]:.10f}')
            
            res = vanchoi_random(headers, Coin, history, he_so, bet_amount0, type_bet, So_nv)
            
            if res:
                history.insert(0, res)
                
                if res['kq']:
                    stats['win'] += 1
                    stats['win_streak'] += 1
                    stats['max_win_streak'] = max(stats['win_streak'], stats['max_win_streak'])
                    stats['lose_streak'] = 0
                else:
                    stats['win_streak'] = 0
                    stats['lose'] += 1
                    stats['lose_streak'] += 1
                    stats['max_lose_streak'] = max(stats['max_lose_streak'], stats['lose_streak'])
                
                stats['earn'] += -1 * res['my_total_bet'] + res['my_total_award']
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        prints(255, 255, 0, "\nĐã dừng chương trình")
    except Exception as e:
        prints(255, 0, 0, f"Lỗi: {e}")

def show_logic_report():
    """Hiển thị báo cáo chi tiết của hệ thống logic"""
    if len(logic_predictor.analyzer.history) < 5:
        prints(255, 0, 0, "Chưa có đủ dữ liệu để phân tích!")
        time.sleep(2)
        return
    
    prints(0, 255, 255, "\n" + "=" * 60)
    prints(0, 255, 255, "BÁO CÁO CHI TIẾT HỆ THỐNG LOGIC")
    prints(0, 255, 255, "=" * 60)
    
    report = logic_predictor.get_analysis_report()
    prints(255, 255, 255, report)
    
    # Thêm thông tin chi tiết
    prints(255, 215, 0, "\nTHÔNG TIN BỔ SUNG:")
    prints(255, 215, 0, f"Lịch sử gần đây: {logic_predictor.analyzer.history[-20:]}")
    
    if logic_predictor.confidence_scores:
        recent_conf = logic_predictor.confidence_scores[-10:] if len(logic_predictor.confidence_scores) >= 10 else logic_predictor.confidence_scores
        avg_conf = statistics.mean(recent_conf)
        prints(255, 215, 0, f"Độ tin cậy trung bình: {avg_conf:.2%}")
    
    prints(255, 215, 0, f"Số pattern phát hiện: {len(logic_predictor.analyzer.patterns)}")
    prints(255, 215, 0, f"Số chuỗi toán học: {len(logic_predictor.analyzer.sequence_patterns)}")
    
    input("\nNhấn Enter để tiếp tục...")

# ============================================================================
# PHẦN 5: MAIN MENU
# ============================================================================

if __name__ == "__main__":
    # Kiểm tra VIP key trước khi khởi động tool
    if not init_vip_key_system():
        prints(255, 0, 0, "Tool yêu cầu VIP key để sử dụng!")
        sys.exit(1)
    
    # Khởi tạo HTTP client
    http = SecureHTTP()
    
    # Khởi tạo Logic Predictor
    logic_predictor = DeterministicLogicPredictor()
    
    # Kiểm tra dependencies
    if not DependencyManager.check_and_install():
        prints(255, 0, 0, "Không thể cài đặt dependencies!")
        sys.exit(1)
    
    while True:
        banner()
        
        prints(255, 255, 0, '''
  1. Cấu hình tài khoản
  2. Chạy Logic System (Hệ thống logic thuần túy)
  3. Chạy Random System (Dự phòng)
  4. Xem báo cáo Logic System
  5. Thoát chương trình
''')
        
        choice = input(Fore.LIGHTWHITE_EX + 'Nhập lựa chọn (1-5): ').strip()
        
        if choice == '1':
            cauhinh()
        elif choice == '2':
            main_logic()
        elif choice == '3':
            main_random()
        elif choice == '4':
            show_logic_report()
        elif choice == '5':
            prints(0, 255, 0, "Cảm ơn đã sử dụng! Hẹn gặp lại!")
            time.sleep(1)
            sys.exit(0)
        else:
            prints(255, 0, 0, "Lựa chọn không hợp lệ!")
            time.sleep(1)