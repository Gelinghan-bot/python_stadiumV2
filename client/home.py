import sys
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QMainWindow,
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor, QFont

# Import LoginWindow and NetworkClient
try:
    from log_in import LoginWindow, NetworkClient
    from import_class import TeacherDashboard
    from admin import AdminWidget
except ImportError:
    from client.log_in import LoginWindow, NetworkClient
    from client.import_class import TeacherDashboard
    from client.admin import AdminWidget


class HomeWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_user = None  # Track login state
        self.brand_color = "#84cc16"
        self.dark_text = "#111827"

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

        self.login_btn = QPushButton("登录")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.open_login_window)
        self.login_btn.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: transparent;
                color: #111827;
                font-size: 16px;
                font-weight: 600;
                padding: 10px 16px;
            }
            QPushButton:hover { color: #4f46e5; }
            """
        )

        self.register_btn = QPushButton("注册")
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.clicked.connect(self.open_register_window)
        self.register_btn.setFixedHeight(40)
        self.register_btn.setStyleSheet(
            f"""
            QPushButton {{
                border: 2px solid {self.brand_color};
                background-color: white;
                color: {self.brand_color};
                font-size: 15px;
                font-weight: 700;
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {self.brand_color};
                color: white;
            }}
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
        nav_layout.addSpacing(4)
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
        desc_label.setStyleSheet("font-size: 12px; color: #cbd5e1;")
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
            "场馆", ["请选择场馆", "篮球馆", "羽毛球馆", "网球馆", "游泳馆", "综合训练馆"]
        )

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

    # ---------------------------- Other Pages ---------------------------- #
    def setup_static_pages(self):
        self.pages = {}
        self.pages["venues"] = self.build_cards_page(
            "场馆一览",
            [
                ("篮球馆 · 4 块场地", "余量充足 · 提前 3 天可约", "#eef2ff"),
                ("羽毛球馆 · 12 块场地", "晚间热门，请提前预约", "#ecfeff"),
                ("游泳馆", "10 条泳道 · 需携带学生证入场", "#fefce8"),
                ("室外田径场", "全天开放 · 每周一早间维护", "#f0fdf4"),
            ],
        )
        self.pages["announcements"] = self.build_cards_page(
            "公告 / 论坛",
            [
                ("场馆维护", "本周五 18:00-22:00 篮球馆封闭维护", "#fff7ed"),
                ("预约规则", "爽约将扣信用分，连续 3 次将限制预约 7 天", "#e0f2fe"),
                ("招募", "羽毛球校队招募助教与陪练", "#fef2f2"),
            ],
        )
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
                ],
            )
            self.profile_body.addWidget(info_card)
            self.profile_body.addWidget(
                self.list_card("最近预约", ["暂无数据，预约后将出现在这里。"])
            )

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

    def handle_search(self):
        """Handle search button click"""
        if not self.current_user:
            self.open_login_window()
            return
        venue_text = self.venue_combo.currentText() if self.venue_combo else "未选择"
        date = self.date_edit.date().toString("yyyy-MM-dd")
        time_text = self.time_combo.currentText() if self.time_combo else "任何时间"

        if venue_text.startswith("请选择"):
            QMessageBox.warning(self, "提示", "请选择一个场馆")
            return

        QMessageBox.information(
            self,
            "提示",
            f"正在查询 {date} 的 {venue_text}（{time_text}）可预约时段。\n（接口对接中）",
        )

    def on_login_success(self, user):
        """Callback when login is successful"""
        self.current_user = user
        print(f"User logged in: {user['name']} ({user['role']})")
        self.user_chip.setText(f"{user['name']} · {user['role']}")
        self.user_chip.setVisible(True)
        self.logout_btn.setVisible(True)
        self.login_btn.setVisible(False)
        self.register_btn.setVisible(False)
        self.refresh_profile_body()

    def on_logout_success(self):
        """Callback when user logs out from dashboard"""
        self.current_user = None
        print("User logged out")

        self.user_chip.setVisible(False)
        self.logout_btn.setVisible(False)
        self.login_btn.setVisible(True)
        self.register_btn.setVisible(True)
        self.refresh_profile_body()

        # Switch back to Home
        self.content_stack.setCurrentIndex(0)
        self.set_active_nav(self.nav_buttons[0])

        # Clean up dashboards
        if hasattr(self, "teacher_page"):
            self.content_stack.removeWidget(self.teacher_page)
            del self.teacher_page

        if hasattr(self, "admin_page"):
            self.content_stack.removeWidget(self.admin_page)
            del self.admin_page

    def handle_nav_click(self, btn, key):
        """Handle navigation button clicks with permission checks"""
        if key == "home":
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
            if key == "profile":
                self.refresh_profile_body()
            self.content_stack.setCurrentWidget(page)
            self.set_active_nav(btn)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = HomeWindow()
    window.show()
    sys.exit(app.exec_())
