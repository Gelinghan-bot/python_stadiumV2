import sys
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QMainWindow,
)
from PyQt5.QtCore import QDate, Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QPixmap, QIcon
import requests
from bs4 import BeautifulSoup
import datetime
import time
import re

# Import LoginWindow and NetworkClient
try:
    from log_in import LoginWindow, NetworkClient
    from import_class import TeacherDashboard
    from admin import AdminWidget
except ImportError:
    from client.log_in import LoginWindow, NetworkClient
    from client.admin import AdminWidget


class WeatherCrawlerThread(QThread):
    weather_fetched = pyqtSignal(str, str)  # 信号：天气类型和日期
    error_occurred = pyqtSignal(str)  # 信号：错误信息

    def __init__(self, date_str):
        super().__init__()
        self.date_str = date_str  # 格式：'YYYY-MM-DD'

    def run(self):
        try:
            # 尝试从中国天气网获取数据
            success = self.fetch_from_weather_com_cn()
            if not success:
                print(f"【自检结果】无法从天气网站获取数据，使用模拟数据")
                self.fetch_mock_weather()
        except Exception as e:
            print(f"【自检结果】天气爬取异常: {str(e)}")
            self.fetch_mock_weather()  # 出现异常时使用模拟数据

    def fetch_from_weather_com_cn(self):
        """从中国天气网获取天气信息"""
        print(f"【开始爬取】尝试获取 {self.date_str} 的天气信息")
        
        # 中国天气网北京天气的URL
        url = "https://www.weather.com.cn/weather/101010100.shtml"  # 北京
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        try:
            print(f"【请求发送】向 {url} 发送请求...")
            response = requests.get(url, headers=headers, timeout=20)
            print(f"【响应状态】HTTP {response.status_code}")
            
            if response.status_code != 200:
                print(f"【自检结果】HTTP状态码错误: {response.status_code}")
                return False
                
            response.encoding = 'utf-8'
            print(f"【响应编码】{response.encoding}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否能正确解析页面
            title_tag = soup.find('title')
            if title_tag:
                print(f"【页面标题】{title_tag.get_text()}")
            else:
                print(f"【自检结果】无法解析页面结构")
                return False
            
            # 查找天气信息表格中的对应日期行
            forecast_items = soup.find_all('li', class_='sky')
            print(f"【解析结果】找到 {len(forecast_items)} 个天气预报条目")
            
            if not forecast_items:
                print(f"【自检结果】未找到天气预报条目，可能页面结构已改变")
                return False
            
            # 解析目标日期
            target_date = datetime.datetime.strptime(self.date_str, '%Y-%m-%d')
            target_month = target_date.month
            target_day = target_date.day
            
            print(f"【查找目标】查找日期: {target_month}月{target_day}日")
            
            for i, item in enumerate(forecast_items):
                date_span = item.find('h1')
                weather_info = item.find('p', class_='wea')
                
                if date_span and weather_info:
                    date_text = date_span.get_text(strip=True)
                    weather_text = weather_info.get_text(strip=True)
                    
                    print(f"  - 条目 {i+1}: 日期='{date_text}', 天气='{weather_text}'")
                    
                    # 修复日期匹配逻辑
                    # 中国天气网显示格式可能是 "22日（今天）" 这种格式
                    # 我们需要提取日期数字部分进行匹配
                    # 提取所有数字（日期）
                    day_matches = re.findall(r'(\d+)日', date_text)
                    if day_matches:
                        found_day = int(day_matches[0])  # 获取第一个匹配的日
                        print(f"    - 解析到日: {found_day}, 目标日: {target_day}")
                        
                        # 检查日期是否匹配
                        if found_day == target_day:
                            print(f"【自检结果】成功找到匹配的天气信息: {weather_text}")
                            
                            # 尝试获取温度信息
                            temp_info = item.find('p', class_='tem')
                            if temp_info:
                                temp_text = temp_info.get_text(strip=True)
                                print(f"    - 温度信息: {temp_text}")
                                weather_text = f"{weather_text} {temp_text}"
                            
                            self.weather_fetched.emit(weather_text, self.date_str)
                            return True
                    else:
                        print(f"    - 未找到日期数字")
                else:
                    print(f"  - 条目 {i+1}: 日期或天气信息缺失")
            
            print(f"【自检结果】未找到指定日期的天气信息")
            return False
                
        except requests.Timeout:
            print(f"【自检结果】请求超时 - 可能网络连接缓慢或网站响应时间过长")
            return False
        except requests.ConnectionError:
            print(f"【自检结果】连接错误 - 可能网络连接问题或网站不可达")
            return False
        except requests.RequestException as e:
            print(f"【自检结果】请求异常: {str(e)}")
            return False
        except Exception as e:
            print(f"【自检结果】解析天气数据时出错: {str(e)}")
            return False

    def fetch_mock_weather(self):
        """获取模拟天气数据"""
        # 根据日期生成模拟天气
        date_obj = datetime.datetime.strptime(self.date_str, '%Y-%m-%d')
        day_of_year = date_obj.timetuple().tm_yday
        
        # 根据日期生成不同的天气（模拟）
        weather_types = [
            "晴", "多云", "阴", "小雨", "中雨", "大雨", "阵雨", 
            "雷阵雨", "小雪", "中雪", "大雪", "雾", "霾"
        ]
        
        # 使用日期作为种子生成相对稳定的天气
        weather_index = day_of_year % len(weather_types)
        weather_desc = weather_types[weather_index]
        
        # 添加温度信息（模拟）
        temp_high = 15 + (day_of_year % 20)  # 15-35度
        temp_low = temp_high - 10  # 昼夜温差10度
        
        weather_text = f"{weather_desc} {temp_low}°C ~ {temp_high}°C"
        
        print(f"【使用模拟数据】{weather_text}")
        self.weather_fetched.emit(weather_text, self.date_str)


class HomeWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_user = None  # Track login state
        self.latest_reservations = []
        self.brand_color = "#84cc16"
        self.dark_text = "#111827"
        self.venue_name_to_id = {
            "足球场": 1,
            "篮球场": 2,
            "篮球馆": 2,
            "排球场": 3,
            "网球场": 4,
            "羽毛球馆": 5,
            "乒乓球馆": 6,
            "健身房": 7,
            "台球室": 8,
            "游泳馆": 9,
        }

        # Initialize Network Client and connect immediately
        self.network = NetworkClient()
        if self.network.connect():
            print("Connected to server successfully")
        else:
            print("Failed to connect to server (Guest Mode)")

        self.setWindowTitle("GoSport · 校园场馆服务")
        self.resize(1280, 860)

        # Main Container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setStyleSheet(
            """
            QWidget {
                background-color: #f6f7fb;
                color: #111827;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            """
        )

        # Main Layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Navigation Bar
        self.setup_navbar()

        # Content Area (Stacked Widget)
        self.content_stack = QStackedWidget()
        self.main_layout.addWidget(self.content_stack)

        # Initialize Pages
        self.setup_home_page()
        self.setup_static_pages()

        # 存储当前活跃的天气线程
        self.active_weather_thread = None

    # ---------------------------- UI Scaffolding ---------------------------- #
    def setup_navbar(self):
        """Top Navigation Bar"""
        navbar = QFrame()
        navbar.setFixedHeight(78)
        navbar.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-bottom: 1px solid #e5e7eb;
            }
            """
        )

        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(20, 0, 20, 0)

        # Logo: GoSport
        logo = QLabel("GoSport")
        logo.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #111827;"
            f" letter-spacing: 0.5px;"
        )
        logo.setText(f"Go<span style='color:{self.brand_color};'>Sport</span>")
        nav_layout.addWidget(logo)

        nav_layout.addStretch(2)

        # Navigation Links
        self.nav_buttons = []
        self.nav_order = [
            ("Home", "home"),
            ("场馆", "venues"),
            ("公告/论坛", "announcements"),
            ("校园赛事", "events"),
            ("管理课表", "schedule"),
            ("个人中心", "profile"),
            ("后台管理", "admin"),
            ("设置", "settings"),
        ]

        for index, (label, key) in enumerate(self.nav_order):
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, b=btn, k=key: self.handle_nav_click(b, k))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            if index < len(self.nav_order) - 1:
                nav_layout.addSpacing(6)

        # Auth Buttons / User Chip
        nav_layout.addStretch(2)

        # 天气信息显示区域 (Always add to layout, visibility controlled by logic)
        self.weather_label = QLabel("天气获取中...")
        self.weather_label.setStyleSheet(
            """
            QLabel {
                background-color: #e0f2fe;
                color: #0f172a;
                padding: 8px 12px;
                border-radius: 12px;
                font-weight: 600;
            }
            """
        )
        self.weather_label.setVisible(False)  # 默认隐藏，登录后显示
        nav_layout.addWidget(self.weather_label)
        nav_layout.addSpacing(10)

        self.login_btn = QPushButton("Login")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.open_login_window)
        self.login_btn.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: transparent;
                color: #1f2937;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #84cc16;
            }
            """
        )

        self.register_btn = QPushButton("Sign up")
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.clicked.connect(self.open_register_window)
        self.register_btn.setFixedSize(100, 48)
        self.register_btn.setStyleSheet(
            """
            QPushButton {
                border: 2px solid #84cc16;
                background-color: white;
                color: #84cc16;
                font-size: 24px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #84cc16;
                color: white;
            }
            """
        )

        self.user_chip = QLabel("")
        self.user_chip.setVisible(False)
        self.user_chip.setStyleSheet(
            """
            QLabel {
                background-color: #e0f2fe;
                color: #0f172a;
                padding: 10px 14px;
                border-radius: 18px;
                font-weight: 700;
            }
            """
        )

        self.logout_btn = QPushButton("退出")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(self.on_logout_success)
        self.logout_btn.setVisible(False)
        self.logout_btn.setStyleSheet(
            """
            QPushButton {
                border: none;
                color: #6b7280;
                font-weight: 600;
                padding: 10px 12px;
                background: transparent;
            }
            QPushButton:hover { color: #ef4444; }
            """
        )

        nav_layout.addWidget(self.login_btn)
        nav_layout.addWidget(self.register_btn)
        nav_layout.addWidget(self.user_chip)
        nav_layout.addWidget(self.logout_btn)

        self.main_layout.addWidget(navbar)
        if self.nav_buttons:
            self.set_active_nav(self.nav_buttons[0])

    def set_active_nav(self, active_btn):
        """Updates the style of navigation buttons to show the active one"""
        base_style = """
            QPushButton {
                border: none;
                background: transparent;
                color: #4b5563;
                font-size: 16px;
                font-weight: 600;
                padding: 12px 10px;
                border-bottom: 3px solid transparent;
            }
            QPushButton:hover { color: #111827; }
        """

        active_style = f"""
            QPushButton {{
                border: none;
                background: transparent;
                color: {self.brand_color};
                font-size: 16px;
                font-weight: 800;
                padding: 12px 10px;
                border-bottom: 3px solid {self.brand_color};
            }}
        """

        for btn in self.nav_buttons:
            btn.setStyleSheet(active_style if btn == active_btn else base_style)

    def fetch_weather_for_today(self):
        """获取今天天气信息并显示"""
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        # 创建并启动爬虫线程
        self.weather_thread = WeatherCrawlerThread(today)
        self.weather_thread.weather_fetched.connect(self.update_weather_display)
        self.weather_thread.error_occurred.connect(self.handle_weather_error)
        self.weather_thread.start()

    def update_weather_display(self, weather_desc, date_str):
        """更新天气显示"""
        # 根据天气描述设置不同的图标和样式
        if any(keyword in weather_desc for keyword in ['晴']):
            icon = "☀️"
        elif any(keyword in weather_desc for keyword in ['多云']):
            icon = "⛅"
        elif any(keyword in weather_desc for keyword in ['阴']):
            icon = "☁️"
        elif any(keyword in weather_desc for keyword in ['雨']):
            icon = "🌧️"
        elif any(keyword in weather_desc for keyword in ['雪']):
            icon = "❄️"
        elif any(keyword in weather_desc for keyword in ['雾']):
            icon = "🌫️"
        elif any(keyword in weather_desc for keyword in ['雷']):
            icon = "⛈️"
        elif any(keyword in weather_desc for keyword in ['沙']):
            icon = "🌪️"
        elif any(keyword in weather_desc for keyword in ['霾']):
            icon = "😷"
        else:
            icon = "🌤️"  # 默认天气图标

        self.weather_label.setText(f"{icon} {weather_desc}")
        self.weather_label.setVisible(True)

    def handle_weather_error(self, error_msg):
        """处理天气获取错误"""
        print(f"【天气获取错误】{error_msg}")
        self.weather_label.setText("天气信息获取失败")
        self.weather_label.setVisible(True)

    # ---------------------------- Home Page ---------------------------- #
    def setup_home_page(self):
        self.home_page = QWidget()
        self.home_layout = QVBoxLayout(self.home_page)
        self.home_layout.setContentsMargins(0, 0, 0, 0)
        self.home_layout.setSpacing(0)

        self.setup_hero_section(self.home_layout)
        self.setup_search_card(self.home_layout)
        self.setup_quick_sections(self.home_layout)

        self.content_stack.addWidget(self.home_page)

    def setup_hero_section(self, parent_layout):
        """Center Title and Background Area"""
        hero_frame = QFrame()
        hero_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        hero_frame.setStyleSheet(
            """
            QFrame {
                background-color: #0f172a;
                background-image: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a,
                    stop:1 #1f2937
                );
            }
            QLabel { color: white; }
            """
        )

        hero_layout = QVBoxLayout(hero_frame)
        hero_layout.setAlignment(Qt.AlignCenter)
        hero_layout.setContentsMargins(0, 120, 0, 60)

        title = QLabel("一站式校园场馆服务")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 44px; font-weight: 900; letter-spacing: 0.5px;"
        )

        subtitle = QLabel("预约 · 课程 · 赛事 · 公告，一屏直达")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 18px; color: #cbd5e1; margin-top: 10px;")

        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)

        stats_row = QHBoxLayout()
        stats = [
            ("32", "开放场馆"),
            ("120+", "今日可预约时段"),
            ("8", "校园赛事进行中"),
        ]
        for number, desc in stats:
            card = self.make_stat_card(number, desc)
            stats_row.addWidget(card)
        hero_layout.addLayout(stats_row)

        parent_layout.addWidget(hero_frame, 2)

    def make_stat_card(self, number, desc):
        box = QFrame()
        box.setStyleSheet(
            """
            QFrame {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
            QLabel { color: white; }
            """
        )
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 14, 18, 14)
        num_label = QLabel(number)
        num_label.setStyleSheet("font-size: 28px; font-weight: 900;")
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #cbd5e1;")
        layout.addWidget(num_label)
        layout.addWidget(desc_label)
        return box

    def setup_search_card(self, parent_layout):
        """The floating search box at the bottom"""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(120, -60, 120, 0)

        card = QFrame()
        card.setFixedHeight(200)
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }
            """
        )

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(26)
        shadow.setColor(QColor(0, 0, 0, 18))
        shadow.setOffset(0, 12)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 22, 26, 22)
        card_layout.setSpacing(14)

        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(24)

        # Venue Selection
        self.venue_combo_box, self.venue_combo = self.build_labeled_combo(
            "场馆",
            [
                "请选择场馆",
                "足球场",
                "篮球馆",
                "排球场",
                "网球场",
                "羽毛球馆",
                "乒乓球馆",
                "健身房",
                "台球室",
                "游泳馆",
            ],
        )
        self.refresh_venue_combo()

        # Date Selection
        date_container = QWidget()
        date_layout = QVBoxLayout(date_container)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(6)
        date_label = QLabel("日期")
        date_label.setStyleSheet("font-size: 14px; color: #4b5563;")
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedHeight(40)
        self.date_edit.setStyleSheet(
            """
            QDateEdit {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 6px 10px;
                color: #374151;
                background-color: white;
            }
            """
        )
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)

        # Time slot
        self.time_combo_box, self.time_combo = self.build_labeled_combo(
            "时间段",
            [
                "任何时间",
                "06:00 - 10:00 早间",
                "10:00 - 14:00 午间",
                "14:00 - 18:00 下午",
                "18:00 - 22:00 夜间",
            ],
        )

        inputs_layout.addWidget(self.venue_combo_box)
        inputs_layout.addWidget(date_container)
        inputs_layout.addWidget(self.time_combo_box)
        card_layout.addLayout(inputs_layout)

        search_btn = QPushButton("查找可预约时间")
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.clicked.connect(self.handle_search)
        search_btn.setFixedHeight(48)
        search_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #111827;
                color: white;
                font-weight: 800;
                font-size: 16px;
                border-radius: 8px;
                letter-spacing: 1px;
            }
            QPushButton:hover { background-color: #0b1220; }
            """
        )

        card_layout.addWidget(search_btn)
        container_layout.addWidget(card)
        parent_layout.addWidget(container)

    def build_labeled_combo(self, label_text, items):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 14px; color: #4b5563;")

        combo = QComboBox()
        combo.addItems(items)
        combo.setFixedHeight(40)
        combo.setStyleSheet(
            """
            QComboBox {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 6px 10px;
                color: #374151;
                background-color: white;
            }
            QComboBox::drop-down { border: none; }
            """
        )

        layout.addWidget(label)
        layout.addWidget(combo)
        return box, combo

    def setup_quick_sections(self, parent_layout):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(32, 16, 32, 24)
        layout.setSpacing(16)

        title = QLabel("常用功能直达")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0f172a;")
        layout.addWidget(title)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards = [
            ("预约场馆", "快速查看剩余时段、提交预约", "#eef2ff"),
            ("查看公告", "获取场馆开放与维护通知", "#ecfeff"),
            ("赛事活动", "校内赛事、训练营最新安排", "#fefce8"),
            ("课程/课表", "教师排课与学生选课", "#f0fdf4"),
        ]
        for title_text, desc, bg in cards:
            cards_row.addWidget(self.feature_card(title_text, desc, bg))

        layout.addLayout(cards_row)

        # Info board
        board = QHBoxLayout()
        board.setSpacing(16)
        board.addWidget(self.list_card("今日公告", ["篮球馆 18:00 后关闭维护", "游泳馆 14:00 开始补水", "周末校内联赛占用部分场地"]))
        board.addWidget(self.list_card("推荐赛事", ["羽毛球学院杯 · 本周六", "夜跑俱乐部 · 每周二", "校队开放训练观摩"]))
        layout.addLayout(board)

        parent_layout.addWidget(section)
        parent_layout.addStretch(1)

    def feature_card(self, title, desc, bg):
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg};
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }}
            """
        )
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(8)

        t = QLabel(title)
        t.setStyleSheet("font-size: 16px; font-weight: 800;")
        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet("color: #4b5563; font-size: 13px;")
        v.addWidget(t)
        v.addWidget(d)
        return card

    def list_card(self, title, lines):
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }
            """
        )
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(8)
        header = QLabel(title)
        header.setStyleSheet("font-size: 16px; font-weight: 800;")
        v.addWidget(header)
        for line in lines:
            lbl = QLabel(f"• {line}")
            lbl.setStyleSheet("color: #4b5563;")
            v.addWidget(lbl)
        return card

    def action_button(self, text):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(40)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.brand_color};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 800;
                padding: 8px 14px;
            }}
            QPushButton:hover {{ background-color: #65a30d; }}
            """
        )
        return btn

    # ---------------------------- Other Pages ---------------------------- #
    def setup_static_pages(self):
        self.pages = {}
        self.pages["venues"] = self.build_venues_page()
        self.pages["announcements"] = self.build_announcements_page()
        self.pages["events"] = self.build_cards_page(
            "校园赛事",
            [
                ("阳光长跑 · 打卡第 5 周", "体育场 400m × 5圈，完成即得学时", "#ecfeff"),
                ("三对三篮球赛 · 复赛", "今晚 19:00 1/2/3 号场", "#eef2ff"),
                ("羽毛球学院杯", "本周六全天，场馆对外开放至 12:00", "#f0fdf4"),
            ],
        )
        self.pages["profile"] = self.build_profile_page()
        self.pages["settings"] = self.build_settings_page()

        for page in self.pages.values():
            self.content_stack.addWidget(page)

    def build_cards_page(self, title, cards):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        header = QLabel(title)
        header.setStyleSheet("font-size: 22px; font-weight: 900;")
        layout.addWidget(header)

        row = QHBoxLayout()
        row.setSpacing(16)
        for text, desc, bg in cards:
            row.addWidget(self.feature_card(text, desc, bg))
        layout.addLayout(row)
        layout.addStretch(1)
        return page

    def build_venues_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        header = QLabel("场馆一览")
        header.setStyleSheet("font-size: 22px; font-weight: 900;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        container = QWidget()
        self.venues_layout = QVBoxLayout(container)
        self.venues_layout.setContentsMargins(0, 0, 0, 0)
        self.venues_layout.setSpacing(12)
        scroll.setWidget(container)

        self.refresh_venues_page()
        return page

    def build_venue_card(self, venue):
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        name = QLabel(venue.get("venue_name", "未命名场馆"))
        name.setStyleSheet("font-size: 16px; font-weight: 800;")
        layout.addWidget(name)

        venue_type = "室外" if venue.get("is_outdoor") else "室内"
        location = venue.get("location") or "未填写位置"
        desc = venue.get("description") or "暂无介绍"
        meta = QLabel(f"类型：{venue_type} · 位置：{location}")
        meta.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(meta)

        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #374151;")
        layout.addWidget(desc_label)

        return card

    def refresh_venues_page(self):
        if not hasattr(self, "venues_layout"):
            return

        self.clear_layout(self.venues_layout)
        try:
            resp = self.network.send_request("admin_get_venues")
        except Exception as e:
            resp = {"status": "error", "message": str(e)}

        if not resp or resp.get("status") != "success":
            msg = resp.get("message", "场馆信息获取失败")
            error_label = QLabel(f"场馆信息获取失败：{msg}")
            error_label.setStyleSheet("color: #ef4444; font-size: 14px;")
            self.venues_layout.addWidget(error_label)
            self.venues_layout.addStretch(1)
            return

        data = resp.get("data", [])
        if not data:
            empty_label = QLabel("暂无场馆信息。")
            empty_label.setStyleSheet("color: #6b7280; font-size: 14px;")
            self.venues_layout.addWidget(empty_label)
            self.venues_layout.addStretch(1)
            return

        for venue in data:
            self.venues_layout.addWidget(self.build_venue_card(venue))
        self.venues_layout.addStretch(1)

    def refresh_venue_combo(self, preserve_selection=True):
        if not self.venue_combo:
            return False

        current_text = self.venue_combo.currentText() if preserve_selection else None
        try:
            resp = self.network.send_request("admin_get_venues")
        except Exception as e:
            resp = {"status": "error", "message": str(e)}

        if resp and resp.get("status") == "success":
            venues = resp.get("data", [])
            self.venue_combo.blockSignals(True)
            self.venue_combo.clear()
            self.venue_combo.addItem("请选择场馆")
            self.venue_name_to_id = {}
            for venue in venues:
                name = venue.get("venue_name")
                if not name:
                    continue
                self.venue_combo.addItem(name)
                self.venue_name_to_id[name] = venue.get("venue_id")
            self.venue_combo.blockSignals(False)
            if preserve_selection and current_text in self.venue_name_to_id:
                idx = self.venue_combo.findText(current_text)
                if idx >= 0:
                    self.venue_combo.setCurrentIndex(idx)
            return True

        fallback_names = list(self.venue_name_to_id.keys())
        if not fallback_names:
            fallback_names = [
                "足球场",
                "篮球馆",
                "排球场",
                "网球场",
                "羽毛球馆",
                "乒乓球馆",
                "健身房",
                "台球室",
                "游泳馆",
            ]
        self.venue_combo.blockSignals(True)
        self.venue_combo.clear()
        self.venue_combo.addItem("请选择场馆")
        for name in fallback_names:
            self.venue_combo.addItem(name)
        self.venue_combo.blockSignals(False)
        if preserve_selection and current_text in fallback_names:
            idx = self.venue_combo.findText(current_text)
            if idx >= 0:
                self.venue_combo.setCurrentIndex(idx)
        return False

    def build_announcements_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header = QLabel("公告 / 论坛")
        header.setStyleSheet("font-size: 22px; font-weight: 900;")
        header_row.addWidget(header)
        header_row.addStretch(1)
        self.post_btn = self.action_button("发帖")
        self.post_btn.clicked.connect(self.prompt_add_post)
        header_row.addWidget(self.post_btn)
        layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        container = QWidget()
        self.announcements_layout = QVBoxLayout(container)
        self.announcements_layout.setContentsMargins(0, 0, 0, 0)
        self.announcements_layout.setSpacing(12)
        scroll.setWidget(container)

        self.refresh_announcements_page()
        return page

    def build_announcement_card(self, ann):
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel(ann.get("title", "未命名公告"))
        title.setStyleSheet("font-size: 16px; font-weight: 800;")
        layout.addWidget(title)

        author_name = ann.get("author_name") or "管理员"
        author_role = ann.get("author_role") or "admin"
        start_date = ann.get("start_date", "")
        end_date = ann.get("end_date", "")
        meta = QLabel(f"作者：{author_name} ({author_role}) · 有效期：{start_date} ~ {end_date}")
        meta.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(meta)

        content = QLabel(ann.get("content", ""))
        content.setWordWrap(True)
        content.setStyleSheet("color: #374151;")
        layout.addWidget(content)

        return card

    def refresh_announcements_page(self):
        if not hasattr(self, "announcements_layout"):
            return

        self.clear_layout(self.announcements_layout)
        try:
            resp = self.network.send_request("get_announcements")
        except Exception as e:
            resp = {"status": "error", "message": str(e)}

        if not resp or resp.get("status") != "success":
            msg = resp.get("message", "公告获取失败")
            error_label = QLabel(f"公告获取失败：{msg}")
            error_label.setStyleSheet("color: #ef4444; font-size: 14px;")
            self.announcements_layout.addWidget(error_label)
            self.announcements_layout.addStretch(1)
            self.update_post_button_state()
            return

        data = resp.get("data", [])
        if not data:
            empty_label = QLabel("暂无公告。")
            empty_label.setStyleSheet("color: #6b7280; font-size: 14px;")
            self.announcements_layout.addWidget(empty_label)
            self.announcements_layout.addStretch(1)
            self.update_post_button_state()
            return

        for ann in data:
            self.announcements_layout.addWidget(self.build_announcement_card(ann))
        self.announcements_layout.addStretch(1)

        self.update_post_button_state()

    def update_post_button_state(self):
        if not hasattr(self, "post_btn"):
            return
        if self.current_user:
            self.post_btn.setEnabled(True)
            self.post_btn.setText("发帖")
        else:
            self.post_btn.setEnabled(True)
            self.post_btn.setText("登录后发帖")

    def prompt_add_post(self):
        if not self.current_user:
            self.open_login_window()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("发布帖子")
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel("标题")
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("请输入标题")
        layout.addWidget(title_label)
        layout.addWidget(title_edit)

        content_label = QLabel("内容")
        content_edit = QTextEdit()
        content_edit.setPlaceholderText("请输入内容")
        content_edit.setFixedHeight(180)
        layout.addWidget(content_label)
        layout.addWidget(content_edit)

        btn_row = QHBoxLayout()
        submit_btn = self.action_button("发布")
        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(submit_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        def submit():
            title = title_edit.text().strip()
            content = content_edit.toPlainText().strip()
            if not title or not content:
                QMessageBox.warning(dialog, "提示", "标题和内容不能为空")
                return
            resp = self.network.send_request(
                "add_post",
                {"title": title, "content": content, "account": self.current_user["account"]},
            )
            if resp and resp.get("status") == "success":
                QMessageBox.information(dialog, "成功", "发帖成功")
                dialog.accept()
                self.refresh_announcements_page()
            else:
                QMessageBox.warning(dialog, "失败", resp.get("message", "发帖失败"))

        submit_btn.clicked.connect(submit)
        dialog.exec_()

    def build_profile_page(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(32, 24, 32, 24)
        page_layout.setSpacing(16)

        header = QLabel("个人中心")
        header.setStyleSheet("font-size: 22px; font-weight: 900;")
        page_layout.addWidget(header)

        self.profile_body = QVBoxLayout()
        self.profile_body.setSpacing(12)
        page_layout.addLayout(self.profile_body)

        self.refresh_profile_body()
        page_layout.addStretch(1)
        return page

    def refresh_profile_body(self):
        self.clear_layout(self.profile_body)
        if not self.current_user:
            prompt = QLabel("请先登录以查看个人信息和预约记录。")
            prompt.setStyleSheet("color: #4b5563; font-size: 14px;")
            action = QPushButton("前往登录")
            action.setCursor(Qt.PointingHandCursor)
            action.clicked.connect(self.open_login_window)
            action.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {self.brand_color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 800;
                    padding: 10px 14px;
                }}
                QPushButton:hover {{ background-color: #65a30d; }}
                """
            )
            self.profile_body.addWidget(prompt)
            self.profile_body.addWidget(action)
        else:
            user = self.current_user
            info_card = self.list_card(
                "账户信息",
                [
                    f"姓名：{user.get('name', '')}",
                    f"角色：{user.get('role', '')}",
                    f"账号：{user.get('account', '')}",
                    f"信用分：{user.get('credit_score', 'N/A')}",
                ],
            )
            self.profile_body.addWidget(info_card)
            
            # Fetch reservations
            res_list = []
            try:
                resp = self.network.send_request("get_my_reservations", {"user_account": user['account']})
                if resp and resp.get("status") == "success":
                    data = resp.get("data", [])
                    self.latest_reservations = data
                    if data:
                        for r in data:
                            # r: {id, venue, court, date, time, status}
                            status_map = {
                                "confirmed": "已预约",
                                "cancelled": "已取消",
                                "queued": "排队中",
                                "checked_in": "已签到",
                                "no_show": "爽约",
                                "cancelled_by_teacher": "教师取消",
                                "completed": "已完成",
                                "finished": "已完成",
                            }
                            status_text = status_map.get(r['status'], r['status'])
                            res_list.append(f"{r['date']} {r['time']} | {r['venue']} {r['court']} | {status_text}")
                    else:
                        res_list.append("暂无预约记录")
                else:
                    self.latest_reservations = []
                    res_list.append("获取预约失败")
            except Exception as e:
                print(f"Error fetching reservations: {e}")
                self.latest_reservations = []
                res_list.append("获取预约出错")

            self.profile_body.addWidget(
                self.list_card("最近预约", res_list)
            )

            action_card = QFrame()
            action_card.setStyleSheet(
                """
                QFrame {
                    background-color: white;
                    border-radius: 12px;
                    border: 1px solid #e5e7eb;
                }
                """
            )
            action_layout = QVBoxLayout(action_card)
            action_layout.setContentsMargins(16, 16, 16, 16)
            action_layout.setSpacing(10)
            action_title = QLabel("预约操作")
            action_title.setStyleSheet("font-size: 16px; font-weight: 800;")
            action_layout.addWidget(action_title)

            btn_row = QHBoxLayout()
            check_in_btn = self.action_button("签到")
            check_in_btn.clicked.connect(self.prompt_check_in)
            btn_row.addWidget(check_in_btn)
            cancel_btn = self.action_button("取消预约")
            cancel_btn.clicked.connect(self.prompt_cancel_reservation)
            btn_row.addWidget(cancel_btn)
            btn_row.addStretch(1)
            action_layout.addLayout(btn_row)

            self.profile_body.addWidget(action_card)

    def build_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        header = QLabel("偏好设置")
        header.setStyleSheet("font-size: 22px; font-weight: 900;")
        layout.addWidget(header)
        layout.addWidget(self.list_card("外观", ["浅色主题（当前）", "品牌色：青柠绿"]))
        layout.addWidget(
            self.list_card("通知", ["预约成功/取消提醒", "公告推送", "赛事提醒"])
        )
        layout.addStretch(1)
        return page

    @staticmethod
    def clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                HomeWindow.clear_layout(item.layout())

    # ---------------------------- Auth / Actions ---------------------------- #
    def open_login_window(self):
        """Opens the login/register window"""
        self.login_window = LoginWindow(self.network, login_callback=self.on_login_success)
        self.login_window.show()

    def open_register_window(self):
        """Opens the register window directly"""
        self.login_window = LoginWindow(self.network, login_callback=self.on_login_success)
        self.login_window.show_register()
        self.login_window.show()

    def prompt_check_in(self):
        if not self.current_user:
            self.open_login_window()
            return

        candidates = [
            r for r in self.latest_reservations if r.get("status") == "confirmed"
        ]
        if not candidates:
            QMessageBox.information(self, "提示", "当前没有可签到的预约。")
            return

        display_items = []
        for r in candidates:
            display_items.append(
                f"{r.get('date')} {r.get('time')} | {r.get('venue')} {r.get('court')} (ID:{r.get('id')})"
            )

        selection, ok = QInputDialog.getItem(
            self, "预约签到", "选择要签到的预约：", display_items, 0, False
        )
        if not ok:
            return

        selected_index = display_items.index(selection)
        reservation_id = candidates[selected_index].get("id")
        if not reservation_id:
            QMessageBox.warning(self, "提示", "预约信息异常，无法签到。")
            return

        resp = self.network.send_request(
            "check_in",
            {
                "user_account": self.current_user["account"],
                "reservation_id": reservation_id,
            },
        )
        if resp and resp.get("status") == "success":
            QMessageBox.information(self, "签到成功", resp.get("message", "签到成功"))
            self.refresh_profile_body()
        else:
            QMessageBox.warning(self, "签到失败", resp.get("message", "签到失败，请稍后重试"))

    def prompt_cancel_reservation(self):
        if not self.current_user:
            self.open_login_window()
            return

        candidates = [
            r
            for r in self.latest_reservations
            if r.get("status") in ("confirmed", "queued")
        ]
        if not candidates:
            QMessageBox.information(self, "提示", "当前没有可取消的预约。")
            return

        status_map = {"confirmed": "已预约", "queued": "排队中"}
        display_items = []
        for r in candidates:
            status_label = status_map.get(r.get("status"), r.get("status"))
            display_items.append(
                f"{r.get('date')} {r.get('time')} | {r.get('venue')} {r.get('court')} "
                f"| {status_label} (ID:{r.get('id')})"
            )

        selection, ok = QInputDialog.getItem(
            self, "取消预约", "选择要取消的预约：", display_items, 0, False
        )
        if not ok:
            return

        selected_index = display_items.index(selection)
        reservation_id = candidates[selected_index].get("id")
        if not reservation_id:
            QMessageBox.warning(self, "提示", "预约信息异常，无法取消。")
            return

        resp = self.network.send_request(
            "cancel_booking",
            {
                "user_account": self.current_user["account"],
                "reservation_id": reservation_id,
            },
        )
        if resp and resp.get("status") == "success":
            QMessageBox.information(self, "取消成功", resp.get("message", "取消成功"))
            self.refresh_profile_body()
        else:
            QMessageBox.warning(self, "取消失败", resp.get("message", "取消失败，请稍后重试"))

    def show_available_slots(self, search_params):
        venue_text = search_params["venue"]
        date = search_params["date"]
        time_text = search_params["time"]
        venue_id = search_params["venue_id"]

        resp = self.network.send_request(
            "get_available_slots", {"venue_id": venue_id, "date": date}
        )
        if not resp or resp.get("status") != "success":
            QMessageBox.warning(
                self, "提示", resp.get("message", "可预约时段查询失败")
            )
            return

        slots = resp.get("data", [])
        time_ranges = {
            "06:00 - 10:00 早间": ("06:00:00", "10:00:00"),
            "10:00 - 14:00 午间": ("10:00:00", "14:00:00"),
            "14:00 - 18:00 下午": ("14:00:00", "18:00:00"),
            "18:00 - 22:00 夜间": ("18:00:00", "22:00:00"),
        }
        if time_text in time_ranges:
            start_time, end_time = time_ranges[time_text]
            slots = [
                slot
                for slot in slots
                if start_time <= slot.get("start_time", "") < end_time
            ]

        available_slots = [
            slot for slot in slots if slot.get("current", 0) < slot.get("max", 0)
        ]
        if not available_slots:
            QMessageBox.information(
                self, "提示", f"{date} 的 {venue_text} 暂无可预约时段。"
            )
            return

        grouped = {}
        for slot in available_slots:
            time_key = f"{slot.get('start_time', '')[:5]}-{slot.get('end_time', '')[:5]}"
            info = grouped.setdefault(
                time_key, {"courts": 0, "remaining": 0, "slots": []}
            )
            info["courts"] += 1
            remaining = max(0, slot.get("max", 0) - slot.get("current", 0))
            info["remaining"] += remaining
            info["slots"].append(slot)

        display_items = []
        time_keys = []
        for time_key in sorted(grouped.keys()):
            info = grouped[time_key]
            display_items.append(
                f"{time_key}（可约场地：{info['courts']}，剩余名额：{info['remaining']}）"
            )
            time_keys.append(time_key)

        prompt = f"{date} 的 {venue_text} 可预约时间段："
        if time_text != "任何时间":
            prompt = f"{prompt}\n筛选：{time_text}"

        selection, ok = QInputDialog.getItem(
            self, "选择预约时间段", prompt, display_items, 0, False
        )
        if not ok:
            return

        selected_index = display_items.index(selection)
        selected_time_key = time_keys[selected_index]
        slots_for_time = grouped[selected_time_key]["slots"]

        def slot_sort_key(slot):
            remaining = max(0, slot.get("max", 0) - slot.get("current", 0))
            return (-remaining, slot.get("court_name", ""), slot.get("slot_id", 0))

        chosen_slot = sorted(slots_for_time, key=slot_sort_key)[0]
        slot_id = chosen_slot.get("slot_id")
        if not slot_id:
            QMessageBox.warning(self, "提示", "预约失败：时间段信息异常")
            return

        resp = self.network.send_request(
            "book_venue",
            {"user_account": self.current_user["account"], "slot_id": slot_id},
        )
        if resp and resp.get("status") == "success":
            court_name = chosen_slot.get("court_name", "")
            QMessageBox.information(
                self,
                "预约成功",
                f"{date} {selected_time_key} | {venue_text} {court_name}\n{resp.get('message', '预约成功')}",
            )
        else:
            QMessageBox.warning(
                self, "预约失败", resp.get("message", "预约失败，请稍后重试")
            )

    def handle_search(self):
        """Handle search button click"""
        if not self.current_user:
            self.open_login_window()
            return
        self.refresh_venue_combo(preserve_selection=True)
        venue_text = self.venue_combo.currentText() if self.venue_combo else "未选择"
        date = self.date_edit.date().toString("yyyy-MM-dd")
        time_text = self.time_combo.currentText() if self.time_combo else "任何时间"

        if venue_text.startswith("请选择"):
            QMessageBox.warning(self, "提示", "请选择一个场馆")
            return
        venue_id = self.venue_name_to_id.get(venue_text)
        if not venue_id:
            QMessageBox.warning(self, "提示", "场馆信息异常，请重新选择")
            return
        try:
            query_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            QMessageBox.warning(self, "提示", "日期格式错误，请重新选择")
            return
        today = datetime.date.today()
        if query_date < today or query_date > today + datetime.timedelta(days=2):
            QMessageBox.warning(self, "提示", "仅支持查询今天、明天、后天的可预约时段")
            return

        # 如果存在活跃的天气线程，先停止它
        if self.active_weather_thread and self.active_weather_thread.isRunning():
            self.active_weather_thread.wait()  # 等待线程结束

        # 爬取当天天气信息
        weather_thread = WeatherCrawlerThread(date)
        # 存储当前线程引用
        self.active_weather_thread = weather_thread
        
        # 创建临时变量存储参数，以便传递给回调函数
        search_params = {
            "venue": venue_text,
            "date": date,
            "time": time_text,
            "venue_id": venue_id,
        }
        weather_thread.weather_fetched.connect(
            lambda weather, date: self.check_weather_and_show_reservation(search_params, weather)
        )
        weather_thread.error_occurred.connect(
            lambda error: self.handle_weather_error_during_search(search_params, error)
        )
        weather_thread.start()

    def check_weather_and_show_reservation(self, search_params, weather_desc):
        """检查天气并显示预约信息"""
        venue_text = search_params['venue']
        date = search_params['date']
        time_text = search_params['time']
        
        # 提取天气类型（去除温度信息）
        # 分割字符串并获取第一个词作为天气类型
        weather_parts = weather_desc.split()
        weather_type = weather_parts[0] if weather_parts else ""
        
        # 检查是否为恶劣天气 - 现在包括小雨和小雪
        bad_weather_keywords = ["小雨", "中雨", "大雨", "暴雨", "小雪", "中雪", "大雪", "暴雪"]
        is_bad_weather = any(keyword in weather_type for keyword in bad_weather_keywords)
        
        if is_bad_weather:
            # 显示天气警告
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("天气提醒")
            msg.setText(f"当前为{weather_type}天气，建议进行室内体育活动")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        self.show_available_slots(search_params)

    def handle_weather_error_during_search(self, search_params, error_msg):
        """处理搜索过程中的天气获取错误"""
        print(f"【搜索时天气获取错误】{error_msg}")
        self.show_available_slots(search_params)

    def on_login_success(self, user):
        """Callback when login is successful"""
        self.current_user = user
        print(f"User logged in: {user['name']} ({user['role']})")
        self.user_chip.setText(f"{user['name']} · {user['role']}")
        self.user_chip.setVisible(True)
        self.logout_btn.setVisible(True)
        self.login_btn.setVisible(False)
        self.register_btn.setVisible(False)
        
        # 显示天气信息
        self.weather_label.setVisible(True)
        # 获取今天天气
        self.fetch_weather_for_today()
        
        self.refresh_profile_body()
        self.refresh_venue_combo()
        self.update_post_button_state()

    def on_logout_success(self):
        """Callback when user logs out from dashboard"""
        self.current_user = None
        print("User logged out")

        self.user_chip.setVisible(False)
        self.logout_btn.setVisible(False)
        self.login_btn.setVisible(True)
        self.register_btn.setVisible(True)
        self.weather_label.setVisible(False)  # 登出时隐藏天气信息
        self.refresh_profile_body()
        self.update_post_button_state()

        # Clean up dashboards
        if hasattr(self, "teacher_page"):
            self.content_stack.removeWidget(self.teacher_page)
            del self.teacher_page

        if hasattr(self, "admin_page"):
            self.content_stack.removeWidget(self.admin_page)
            del self.admin_page

        # Switch back to Home (after cleanup to avoid blank current widget)
        if hasattr(self, "home_page"):
            self.content_stack.setCurrentWidget(self.home_page)
        else:
            self.content_stack.setCurrentIndex(0)
        if self.nav_buttons:
            self.set_active_nav(self.nav_buttons[0])

    def handle_nav_click(self, btn, key):
        """Handle navigation button clicks with permission checks"""
        if key == "home":
            self.refresh_venue_combo(preserve_selection=True)
            self.content_stack.setCurrentIndex(0)
            self.set_active_nav(btn)
            return

        if key == "schedule":
            if not self.current_user:
                self.open_login_window()
                return

            if self.current_user["role"] == "student":
                QMessageBox.warning(self, "权限不足", "此为教师/管理员功能，你没有该权限。")
                return

            if not hasattr(self, "teacher_page"):
                self.teacher_page = TeacherDashboard(
                    self.network, self.current_user, self.on_logout_success
                )
                self.content_stack.addWidget(self.teacher_page)

            self.content_stack.setCurrentWidget(self.teacher_page)
            self.set_active_nav(btn)
            return

        if key == "admin":
            if not self.current_user:
                self.open_login_window()
                return

            if self.current_user["role"] != "admin":
                QMessageBox.warning(self, "权限不足", "此为管理员功能，你没有该权限。")
                return

            if not hasattr(self, "admin_page"):
                self.admin_page = AdminWidget(self.network, self.current_user)
                self.content_stack.addWidget(self.admin_page)

            self.content_stack.setCurrentWidget(self.admin_page)
            self.set_active_nav(btn)
            return

        # Other static tabs
        page = self.pages.get(key)
        if page:
            # Restricted pages
            if key in ["profile", "settings"]:
                if not self.current_user:
                    self.open_login_window()
                    return

        if key == "profile":
            self.refresh_profile_body()
        if key == "announcements":
            self.refresh_announcements_page()
        if key == "venues":
            self.refresh_venues_page()
        self.content_stack.setCurrentWidget(page)
        self.set_active_nav(btn)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = HomeWindow()
    window.show()
    
    sys.exit(app.exec_())
 
