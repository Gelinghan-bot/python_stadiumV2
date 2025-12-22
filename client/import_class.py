from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)


class TeacherDashboard(QWidget):
    def __init__(self, network_client, user_info, on_logout):
        super().__init__()
        self.network = network_client
        self.user = user_info
        self.on_logout = on_logout
        self.brand_color = "#84cc16"

        self.setWindowTitle(f"教师管理系统 - {self.user['name']}")
        self.resize(700, 560)
        self.setStyleSheet("background-color: #f8fafc; color: #0f172a;")

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet(
            """
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #e5e7eb; }
            QLabel { color: #0f172a; }
            """
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)

        welcome_label = QLabel(f"欢迎，{self.user['name']} 老师")
        welcome_label.setStyleSheet("font-size: 18px; font-weight: 800;")
        header_layout.addWidget(welcome_label)
        header_layout.addStretch()

        logout_btn = QPushButton("退出登录")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #dc2626; }
            """
        )
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(logout_btn)
        main_layout.addWidget(header_frame)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        main_layout.addLayout(content_layout)

        title_label = QLabel("添加长期课表（自动锁定未来 4 个月）")
        title_label.setStyleSheet("font-size: 16px; font-weight: 900;")
        content_layout.addWidget(title_label)

        form_group = QGroupBox("课表信息")
        form_group.setStyleSheet(
            """
            QGroupBox {
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                margin-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
            """
        )
        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(10)
        form_group.setLayout(form_layout)

        form_layout.addWidget(QLabel("场馆 ID"), 0, 0)
        self.entry_venue_id = QLineEdit()
        self.entry_venue_id.setPlaceholderText("如：1")
        form_layout.addWidget(self.entry_venue_id, 0, 1)

        form_layout.addWidget(QLabel("星期"), 1, 0)
        self.combo_day = QComboBox()
        self.combo_day.addItems(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        form_layout.addWidget(self.combo_day, 1, 1)

        form_layout.addWidget(QLabel("开始时间"), 2, 0)
        self.entry_start_time = QLineEdit("08:00")
        self.entry_start_time.setPlaceholderText("HH:MM")
        form_layout.addWidget(self.entry_start_time, 2, 1)

        form_layout.addWidget(QLabel("结束时间"), 3, 0)
        self.entry_end_time = QLineEdit("10:00")
        self.entry_end_time.setPlaceholderText("HH:MM")
        form_layout.addWidget(self.entry_end_time, 3, 1)

        submit_btn = QPushButton("添加课表")
        submit_btn.setCursor(Qt.PointingHandCursor)
        submit_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.brand_color};
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 8px;
                font-weight: 800;
            }}
            QPushButton:hover {{ background-color: #65a30d; }}
            """
        )
        submit_btn.clicked.connect(self.add_schedule)
        form_layout.addWidget(submit_btn, 4, 1)

        content_layout.addWidget(form_group)

        log_label = QLabel("操作日志")
        log_label.setStyleSheet("font-size: 14px; font-weight: 800;")
        content_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px;"
        )
        content_layout.addWidget(self.log_text)

    def log(self, message):
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_schedule(self):
        venue_id = self.entry_venue_id.text().strip()
        day_str = self.combo_day.currentText()
        start_time = self.entry_start_time.text().strip()
        end_time = self.entry_end_time.text().strip()

        if not venue_id or not start_time or not end_time:
            QMessageBox.warning(self, "输入错误", "请填写完整信息")
            return

        day_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
        day_of_week = day_map.get(day_str, 0)

        data = {
            "teacher_account": self.user["account"],
            "venue_id": int(venue_id),
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
        }

        self.log(f"正在请求添加课表: {day_str} {start_time}-{end_time} @ 场馆 {venue_id}...")

        try:
            response = self.network.send_request("add_schedule", data)

            if response.get("status") == "success":
                self.log("✅ 添加成功！未来 4 个月的对应时段已自动锁定。")
                QMessageBox.information(self, "成功", "课表添加成功，已锁定未来 4 个月。")
            else:
                error_msg = response.get("message", "未知错误")
                self.log(f"❌ 添加失败: {error_msg}")
                QMessageBox.critical(self, "失败", f"添加失败: {error_msg}")
        except Exception as e:
            self.log(f"❌ 通信错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"通信错误: {str(e)}")

    def logout(self):
        reply = QMessageBox.question(
            self, "退出登录", "确定要退出登录吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.on_logout()
