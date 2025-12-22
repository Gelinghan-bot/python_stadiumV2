import json
import socket
import sys
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt


class NetworkClient:
    def __init__(self, host="127.0.0.1", port=8888):
        self.host = host
        self.port = port
        self.client_socket = None

    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"连接服务器失败: {e}")
            return False

    def send_request(self, action, data=None):
        if isinstance(action, dict) and data is None:
            data = action.get("data", {})
            action = action.get("action")

        if not self.client_socket:
            if not self.connect():
                return {"status": "error", "message": "无法连接到服务器"}

        try:
            request = {"action": action, "data": data}
            self.client_socket.send(
                json.dumps(request, ensure_ascii=False).encode("utf-8")
            )

            response_data = self.client_socket.recv(4096).decode("utf-8")
            return json.loads(response_data)
        except Exception as e:
            return {"status": "error", "message": f"通信错误: {str(e)}"}

    def close(self):
        if self.client_socket:
            self.client_socket.close()


class LoginWindow(QWidget):
    def __init__(self, network_client=None, login_callback=None):
        super().__init__()
        self.login_callback = login_callback
        self.network = network_client or NetworkClient()

        self.brand_color = "#84cc16"
        self.setWindowTitle("GoSport 登录 / 注册")
        self.resize(460, 520)

        self.stacked_widget = QStackedWidget()
        self.init_login_ui()
        self.init_register_ui()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        self.show_login()

    # ------------------------ UI ------------------------ #
    def base_card(self, title, subtitle):
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-radius: 14px;
                border: 1px solid #e5e7eb;
            }
            QLabel { color: #111827; }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        header = QLabel(title)
        header.setStyleSheet("font-size: 22px; font-weight: 900;")
        sub = QLabel(subtitle)
        sub.setStyleSheet("color: #6b7280; margin-top: 4px;")
        layout.addWidget(header)
        layout.addWidget(sub)
        return card, layout

    def style_line_edit(self, widget, placeholder):
        widget.setPlaceholderText(placeholder)
        widget.setFixedHeight(40)
        widget.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 8px 10px;
                background: #f8fafc;
            }
            """
        )
        return widget

    def primary_button(self, text):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.brand_color};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 800;
                padding: 10px 14px;
            }}
            QPushButton:hover {{ background-color: #65a30d; }}
            """
        )
        return btn

    def ghost_button(self, text):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                color: #374151;
                padding: 10px 14px;
                font-weight: 700;
            }
            QPushButton:hover { border-color: #cbd5e1; }
            """
        )
        return btn

    def init_login_ui(self):
        self.login_page = QWidget()
        page_layout = QVBoxLayout(self.login_page)
        page_layout.setContentsMargins(24, 24, 24, 24)

        card, layout = self.base_card("欢迎回来", "使用学工号登录 GoSport")

        self.login_account = self.style_line_edit(QLineEdit(), "账号（学号/工号）")
        self.login_password = self.style_line_edit(QLineEdit(), "密码")
        self.login_password.setEchoMode(QLineEdit.Password)

        layout.addWidget(self.login_account)
        layout.addWidget(self.login_password)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        login_btn = self.primary_button("登录")
        login_btn.clicked.connect(self.handle_login)
        reg_btn = self.ghost_button("去注册")
        reg_btn.clicked.connect(self.show_register)
        btn_row.addWidget(login_btn)
        btn_row.addWidget(reg_btn)
        layout.addLayout(btn_row)

        card.setLayout(layout)
        page_layout.addWidget(card)
        page_layout.addStretch(1)
        self.stacked_widget.addWidget(self.login_page)

    def init_register_ui(self):
        self.register_page = QWidget()
        page_layout = QVBoxLayout(self.register_page)
        page_layout.setContentsMargins(24, 24, 24, 24)

        card, layout = self.base_card("创建新账号", "完善信息后提交注册")

        self.reg_account = self.style_line_edit(QLineEdit(), "账号（必填）")
        self.reg_password = self.style_line_edit(QLineEdit(), "密码（≥6 位）")
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_name = self.style_line_edit(QLineEdit(), "姓名（必填）")
        self.reg_role = QComboBox()
        self.reg_role.addItems(["student", "teacher"])
        self.reg_role.setFixedHeight(40)
        self.reg_role.setStyleSheet(
            """
            QComboBox {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 6px 10px;
                background: #f8fafc;
            }
            """
        )
        self.reg_phone = self.style_line_edit(QLineEdit(), "电话（选填）")

        for widget in [
            self.reg_account,
            self.reg_password,
            self.reg_name,
            self.reg_role,
            self.reg_phone,
        ]:
            layout.addWidget(widget)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        submit_btn = self.primary_button("提交注册")
        submit_btn.clicked.connect(self.handle_register)
        back_btn = self.ghost_button("返回登录")
        back_btn.clicked.connect(self.show_login)
        btn_row.addWidget(submit_btn)
        btn_row.addWidget(back_btn)
        layout.addLayout(btn_row)

        card.setLayout(layout)
        page_layout.addWidget(card)
        page_layout.addStretch(1)
        self.stacked_widget.addWidget(self.register_page)

    # ------------------------ Actions ------------------------ #
    def show_login(self):
        self.stacked_widget.setCurrentWidget(self.login_page)
        self.setWindowTitle("GoSport - 登录")

    def show_register(self):
        self.stacked_widget.setCurrentWidget(self.register_page)
        self.setWindowTitle("GoSport - 注册")

    def handle_login(self):
        account = self.login_account.text().strip()
        password = self.login_password.text().strip()

        if not account or not password:
            QMessageBox.warning(self, "提示", "请输入账号和密码")
            return

        resp = self.network.send_request(
            "login", {"account": account, "password": password}
        )

        if resp.get("status") == "success":
            user = resp.get("user")
            if self.login_callback:
                self.login_callback(user)

            role = user.get("role", "")
            QMessageBox.information(
                self, "提示", f"登录成功，当前身份：{role}\n欢迎 {user.get('name','')}"
            )
            self.close()
        else:
            QMessageBox.critical(self, "登录失败", resp.get("message", "未知错误"))

    def handle_register(self):
        account = self.reg_account.text().strip()
        password = self.reg_password.text().strip()
        name = self.reg_name.text().strip()
        role = self.reg_role.currentText()
        phone = self.reg_phone.text().strip()

        if not account:
            QMessageBox.warning(self, "验证失败", "账号不能为空")
            return
        if len(password) < 6:
            QMessageBox.warning(self, "验证失败", "密码长度必须大于等于 6 位")
            return
        if not name:
            QMessageBox.warning(self, "验证失败", "姓名不能为空")
            return

        data = {
            "account": account,
            "password": password,
            "name": name,
            "role": role,
            "phone": phone,
        }

        resp = self.network.send_request("register", data)

        if resp.get("status") == "success":
            QMessageBox.information(self, "成功", "注册成功！请返回登录。")
            self.show_login()
        else:
            QMessageBox.critical(self, "注册失败", resp.get("message"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())