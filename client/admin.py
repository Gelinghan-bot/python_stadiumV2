import io
import os
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap


class AdminWidget(QWidget):
    def __init__(self, network_client, user_info):
        super().__init__()
        self.network = network_client
        self.user_info = user_info
        self.brand_color = "#84cc16"

        self.setStyleSheet(
            """
            QWidget { background-color: #f8fafc; color: #0f172a; }
            QTableWidget { background: white; border: 1px solid #e5e7eb; }
            QHeaderView::section { background: #f1f5f9; padding: 6px; border: none; }
            """
        )

        self.layout = QVBoxLayout(self)

        self.header = QLabel(f"欢迎管理员 {user_info.get('name', 'Admin')}")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        self.layout.addWidget(self.header)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.setup_venue_tab()
        self.setup_user_tab()
        self.setup_reservation_tab()
        self.setup_announcement_tab()
        self.setup_analytics_tab()

    def setup_analytics_tab(self):
        self.analytics_tab = QWidget()
        self.tabs.addTab(self.analytics_tab, "数据分析")
        layout = QVBoxLayout(self.analytics_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(16)

        control_row = QHBoxLayout()
        control_row.addWidget(QLabel("用户账号"))
        self.stats_user_input = QLineEdit()
        self.stats_user_input.setPlaceholderText("用于生成个人运动趋势图")
        self.stats_user_input.setText(self.user_info.get("account", ""))
        control_row.addWidget(self.stats_user_input)

        refresh_btn = QPushButton("刷新图表")
        refresh_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.brand_color};
                color: white;
                border: none;
                padding: 8px 14px;
                border-radius: 8px;
                font-weight: 800;
            }}
            QPushButton:hover {{ background-color: #65a30d; }}
            """
        )
        refresh_btn.clicked.connect(self.refresh_analytics_images)
        control_row.addWidget(refresh_btn)
        control_row.addStretch(1)
        container_layout.addLayout(control_row)

        self.analytics_output_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "stats_output")
        )
        self.analytics_use_disk = False
        self.analytics_show_heatmap_values = True
        self.analytics_images = [
            ("场馆预约热力图", "heatmap.png"),
            ("用户运动趋势", "user_stats.png"),
            ("场馆预约统计", "venue_stats.png"),
        ]
        self.analytics_image_labels = {}
        self.analytics_pixmaps = {}

        for title, filename in self.analytics_images:
            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 16px; font-weight: 800;")
            container_layout.addWidget(title_label)

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            container_layout.addWidget(img_label)
            self.analytics_image_labels[filename] = img_label

        self.refresh_analytics_images()

    def refresh_analytics_images(self):
        if not self.generate_analytics_images():
            return
        if self.analytics_use_disk:
            self.load_analytics_images()
        else:
            self.apply_analytics_pixmaps()

    def load_analytics_images(self):
        for _, filename in self.analytics_images:
            img_label = self.analytics_image_labels.get(filename)
            if not img_label:
                continue
            img_path = os.path.join(self.analytics_output_dir, filename)
            pixmap = QPixmap(img_path)
            if pixmap.isNull():
                img_label.setText(f"未找到图片：{filename}")
            else:
                img_label.setPixmap(pixmap.scaledToWidth(900, Qt.SmoothTransformation))

    def apply_analytics_pixmaps(self):
        for _, filename in self.analytics_images:
            img_label = self.analytics_image_labels.get(filename)
            if not img_label:
                continue
            pixmap = self.analytics_pixmaps.get(filename)
            if not pixmap or pixmap.isNull():
                img_label.setText(f"未生成图片：{filename}")
            else:
                img_label.setPixmap(pixmap.scaledToWidth(900, Qt.SmoothTransformation))

    def generate_analytics_images(self):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
        except Exception as e:
            QMessageBox.warning(self, "错误", f"图表依赖缺失: {e}")
            return False

        matplotlib.rcParams["font.sans-serif"] = ["SimHei"]
        matplotlib.rcParams["axes.unicode_minus"] = False

        self.analytics_pixmaps = {}
        os.makedirs(self.analytics_output_dir, exist_ok=True)

        def finalize_figure(filename, fig):
            if self.analytics_use_disk:
                path = os.path.join(self.analytics_output_dir, filename)
                fig.savefig(path)
                plt.close(fig)
                return

            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            plt.close(fig)
            buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            self.analytics_pixmaps[filename] = pixmap

        def save_empty_chart(path, title, message):
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.axis("off")
            ax.text(0.5, 0.6, title, ha="center", va="center", fontsize=14)
            ax.text(0.5, 0.4, message, ha="center", va="center", fontsize=12, color="#6b7280")
            fig.tight_layout()
            finalize_figure(os.path.basename(path), fig)

        # 1) 场馆预约统计
        venue_path = os.path.join(self.analytics_output_dir, "venue_stats.png")
        resp = self.network.send_request("get_venue_stats", {})
        if not resp or resp.get("status") != "success":
            message = resp.get("message", "获取失败") if resp else "获取失败"
            save_empty_chart(venue_path, "场馆预约统计", message)
        else:
            data = resp.get("data", [])
            if not data:
                save_empty_chart(venue_path, "场馆预约统计", "暂无数据")
            else:
                venues = [item.get("venue_name", "") for item in data]
                counts = [item.get("reservation_count", 0) for item in data]
                rates = [item.get("utilization_rate", 0) for item in data]
                fig, ax1 = plt.subplots(figsize=(10, 6))
                ax1.bar(venues, counts, color="#93c5fd", label="预约次数")
                ax1.set_xlabel("场馆")
                ax1.set_ylabel("预约次数", color="#2563eb")
                ax1.tick_params(axis="y", labelcolor="#2563eb")

                ax2 = ax1.twinx()
                ax2.plot(venues, rates, color="#ef4444", marker="o", label="预约率(%)")
                ax2.set_ylabel("预约率 (%)", color="#ef4444")
                ax2.tick_params(axis="y", labelcolor="#ef4444")
                plt.title("场馆预约情况统计")
                fig.tight_layout()
                finalize_figure("venue_stats.png", fig)

        # 2) 热力图
        heatmap_path = os.path.join(self.analytics_output_dir, "heatmap.png")
        resp = self.network.send_request("get_heatmap_data", {})
        if not resp or resp.get("status") != "success":
            message = resp.get("message", "获取失败") if resp else "获取失败"
            save_empty_chart(heatmap_path, "场馆预约热力图", message)
        else:
            result = resp.get("data", {})
            x_labels = result.get("x_axis", [])
            y_labels = result.get("y_axis", [])
            raw_data = result.get("data", [])
            if not x_labels or not y_labels:
                save_empty_chart(heatmap_path, "场馆预约热力图", "暂无数据")
            else:
                matrix = np.zeros((len(y_labels), len(x_labels)))
                for x, y, val in raw_data:
                    if 0 <= y < len(y_labels) and 0 <= x < len(x_labels):
                        matrix[y, x] = val
                fig, ax = plt.subplots(figsize=(10, 8))
                im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
                ax.set_xticks(range(len(x_labels)))
                ax.set_xticklabels(x_labels)
                ax.set_yticks(range(len(y_labels)))
                ax.set_yticklabels(y_labels)
                if self.analytics_show_heatmap_values:
                    for i in range(len(y_labels)):
                        for j in range(len(x_labels)):
                            val = matrix[i, j]
                            if val > 0:
                                ax.text(j, i, int(val), ha="center", va="center", color="black")
                fig.colorbar(im, ax=ax, label="预约热度")
                ax.set_title("场馆预约热力图 (星期 x 时间段)")
                fig.tight_layout()
                finalize_figure("heatmap.png", fig)

        # 3) 用户运动趋势
        user_path = os.path.join(self.analytics_output_dir, "user_stats.png")
        user_account = self.stats_user_input.text().strip()
        if not user_account:
            save_empty_chart(user_path, "用户运动趋势", "请输入用户账号")
        else:
            resp = self.network.send_request(
                "get_user_stats", {"user_account": user_account}
            )
            if not resp or resp.get("status") != "success":
                message = resp.get("message", "获取失败") if resp else "获取失败"
                save_empty_chart(user_path, "用户运动趋势", message)
            else:
                result = resp.get("data", {})
                trend = result.get("weekly_trend", {})
                dates = trend.get("dates", [])
                counts = trend.get("counts", [])
                if not dates or not counts:
                    save_empty_chart(user_path, "用户运动趋势", "暂无数据")
                else:
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.plot(dates, counts, marker="o", linestyle="-", color="#22c55e")
                    ax.set_title(f"用户 {user_account} 最近7天运动趋势")
                    ax.set_xlabel("日期")
                    ax.set_ylabel("运动次数")
                    ax.grid(True)
                    fig.tight_layout()
                    finalize_figure("user_stats.png", fig)

        return True

    # ---------------- 场馆管理 ---------------- #
    def setup_venue_tab(self):
        self.venue_tab = QWidget()
        self.tabs.addTab(self.venue_tab, "场馆管理")
        layout = QVBoxLayout(self.venue_tab)

        btn_layout = QHBoxLayout()
        self.btn_add_venue = QPushButton("添加场馆")
        self.btn_add_venue.clicked.connect(self.add_venue_dialog)
        self.btn_refresh_venue = QPushButton("刷新列表")
        self.btn_refresh_venue.clicked.connect(self.load_venues)
        btn_layout.addWidget(self.btn_add_venue)
        btn_layout.addWidget(self.btn_refresh_venue)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.venue_table = QTableWidget()
        self.venue_table.setColumnCount(6)
        self.venue_table.setHorizontalHeaderLabels(["ID", "名称", "类型", "位置", "描述", "操作"])
        self.venue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.venue_table)

        self.load_venues()

    def load_venues(self):
        req = {"action": "admin_get_venues"}
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            venues = res.get("data", [])
            self.venue_table.setRowCount(len(venues))
            for i, v in enumerate(venues):
                self.venue_table.setItem(i, 0, QTableWidgetItem(str(v["venue_id"])))
                self.venue_table.setItem(i, 1, QTableWidgetItem(v["venue_name"]))
                self.venue_table.setItem(i, 2, QTableWidgetItem("室外" if v["is_outdoor"] else "室内"))
                self.venue_table.setItem(i, 3, QTableWidgetItem(v["location"]))
                self.venue_table.setItem(i, 4, QTableWidgetItem(v["description"]))

                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(0, 0, 0, 0)

                btn_courts = QPushButton("场地")
                btn_courts.clicked.connect(
                    lambda checked, vid=v["venue_id"], vname=v["venue_name"]: self.manage_courts(
                        vid, vname
                    )
                )

                btn_edit = QPushButton("编辑")
                btn_edit.clicked.connect(lambda checked, venue=v: self.edit_venue_dialog(venue))

                btn_del = QPushButton("删除")
                btn_del.setStyleSheet("color: red;")
                btn_del.clicked.connect(lambda checked, vid=v["venue_id"]: self.delete_venue(vid))

                btn_layout.addWidget(btn_courts)
                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_del)
                self.venue_table.setCellWidget(i, 5, btn_widget)
        else:
            QMessageBox.warning(self, "错误", res.get("message", "获取场馆失败"))

    def edit_venue_dialog(self, venue):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑场馆 - {venue['venue_name']}")
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(venue["venue_name"])
        type_combo = QComboBox()
        type_combo.addItems(["室内", "室外"])
        type_combo.setCurrentText("室外" if venue["is_outdoor"] else "室内")
        loc_edit = QLineEdit(venue["location"])
        desc_edit = QLineEdit(venue["description"])

        layout.addRow("名称:", name_edit)
        layout.addRow("类型:", type_combo)
        layout.addRow("位置:", loc_edit)
        layout.addRow("描述:", desc_edit)

        btn_submit = QPushButton("保存")
        btn_submit.clicked.connect(
            lambda: self.submit_edit_venue(
                dialog, venue["venue_id"], name_edit.text(), type_combo.currentText(), loc_edit.text(), desc_edit.text()
            )
        )
        layout.addRow(btn_submit)

        dialog.exec_()

    def submit_edit_venue(self, dialog, venue_id, name, v_type, loc, desc):
        if not name:
            QMessageBox.warning(dialog, "错误", "名称不能为空")
            return

        is_outdoor = 1 if v_type == "室外" else 0
        req = {
            "action": "admin_update_venue",
            "data": {
                "venue_id": venue_id,
                "name": name,
                "is_outdoor": is_outdoor,
                "location": loc,
                "description": desc,
            },
        }
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            QMessageBox.information(dialog, "成功", "更新成功")
            dialog.accept()
            self.load_venues()
        else:
            QMessageBox.warning(dialog, "错误", res.get("message", "更新失败"))

    def add_venue_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加场馆")
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        type_combo = QComboBox()
        type_combo.addItems(["室内", "室外"])
        loc_edit = QLineEdit()
        desc_edit = QLineEdit()

        layout.addRow("名称:", name_edit)
        layout.addRow("类型:", type_combo)
        layout.addRow("位置:", loc_edit)
        layout.addRow("描述:", desc_edit)

        btn_submit = QPushButton("提交")
        btn_submit.clicked.connect(
            lambda: self.submit_add_venue(dialog, name_edit.text(), type_combo.currentText(), loc_edit.text(), desc_edit.text())
        )
        layout.addRow(btn_submit)

        dialog.exec_()

    def submit_add_venue(self, dialog, name, v_type, loc, desc):
        if not name:
            QMessageBox.warning(dialog, "错误", "名称不能为空")
            return

        is_outdoor = 1 if v_type == "室外" else 0
        req = {
            "action": "admin_add_venue",
            "data": {
                "name": name,
                "is_outdoor": is_outdoor,
                "location": loc,
                "description": desc,
            },
        }
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            QMessageBox.information(dialog, "成功", "添加成功")
            dialog.accept()
            self.load_venues()
        else:
            QMessageBox.warning(dialog, "错误", res.get("message", "添加失败"))

    def delete_venue(self, venue_id):
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要删除该场馆吗？这将删除关联的所有场地。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            req = {"action": "admin_delete_venue", "data": {"venue_id": venue_id}}
            res = self.network.send_request(req)
            if res and res.get("status") == "success":
                self.load_venues()
            else:
                QMessageBox.warning(self, "错误", res.get("message", "删除失败"))

    def manage_courts(self, venue_id, venue_name):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"管理场地 - {venue_name}")
        dialog.resize(600, 400)
        layout = QVBoxLayout(dialog)

        add_layout = QHBoxLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("场地名称 (如：1号场)")
        btn_add = QPushButton("添加场地")
        btn_add.clicked.connect(lambda: self.add_court(venue_id, name_edit.text(), dialog))
        add_layout.addWidget(name_edit)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        self.court_table = QTableWidget()
        self.court_table.setColumnCount(3)
        self.court_table.setHorizontalHeaderLabels(["ID", "名称", "操作"])
        self.court_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.court_table)

        self.load_courts(venue_id)

        dialog.exec_()

    def load_courts(self, venue_id):
        req = {"action": "admin_get_courts", "data": {"venue_id": venue_id}}
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            courts = res.get("data", [])
            self.court_table.setRowCount(len(courts))
            for i, c in enumerate(courts):
                self.court_table.setItem(i, 0, QTableWidgetItem(str(c["court_id"])))
                self.court_table.setItem(i, 1, QTableWidgetItem(c["court_name"]))

                btn_del = QPushButton("删除")
                btn_del.setStyleSheet("color: red;")
                btn_del.clicked.connect(lambda checked, cid=c["court_id"]: self.delete_court(cid, venue_id))
                self.court_table.setCellWidget(i, 2, btn_del)

    def add_court(self, venue_id, name, dialog):
        if not name:
            return
        req = {"action": "admin_add_court", "data": {"venue_id": venue_id, "name": name}}
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            self.load_courts(venue_id)
        else:
            QMessageBox.warning(dialog, "错误", res.get("message", "添加失败"))

    def delete_court(self, court_id, venue_id):
        req = {"action": "admin_delete_court", "data": {"court_id": court_id}}
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            self.load_courts(venue_id)
        else:
            QMessageBox.warning(self, "错误", res.get("message", "删除失败"))

    # ---------------- 用户管理 ---------------- #
    def setup_user_tab(self):
        self.user_tab = QWidget()
        self.tabs.addTab(self.user_tab, "用户管理")
        layout = QVBoxLayout(self.user_tab)

        btn_refresh = QPushButton("刷新列表")
        btn_refresh.clicked.connect(self.load_users)
        layout.addWidget(btn_refresh)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["账号", "姓名", "角色", "电话", "信用分", "操作"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.user_table)

        self.load_users()

    def load_users(self):
        req = {"action": "admin_get_users"}
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            users = res.get("data", [])
            self.user_table.setRowCount(len(users))
            for i, u in enumerate(users):
                self.user_table.setItem(i, 0, QTableWidgetItem(u["account"]))
                self.user_table.setItem(i, 1, QTableWidgetItem(u["name"]))
                self.user_table.setItem(i, 2, QTableWidgetItem(u["role"]))
                self.user_table.setItem(i, 3, QTableWidgetItem(u["phone"]))
                self.user_table.setItem(i, 4, QTableWidgetItem(str(u["credit_score"])))

                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(0, 0, 0, 0)

                btn_edit = QPushButton("编辑")
                btn_edit.clicked.connect(lambda checked, user=u: self.edit_user_dialog(user))

                btn_del = QPushButton("删除")
                btn_del.setStyleSheet("color: red;")
                btn_del.clicked.connect(lambda checked, acc=u["account"]: self.delete_user(acc))

                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_del)
                self.user_table.setCellWidget(i, 5, btn_widget)

    def edit_user_dialog(self, user):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑用户 - {user['account']}")
        layout = QFormLayout(dialog)

        # 账号 (允许修改)
        account_edit = QLineEdit(user["account"])
        
        # 密码 (留空不修改)
        password_edit = QLineEdit()
        password_edit.setPlaceholderText("留空则不修改密码")
        password_edit.setEchoMode(QLineEdit.Password)

        name_edit = QLineEdit(user["name"])
        role_combo = QComboBox()
        role_combo.addItems(["student", "teacher", "admin"])
        role_combo.setCurrentText(user["role"])
        phone_edit = QLineEdit(user["phone"])
        score_edit = QLineEdit(str(user["credit_score"]))

        layout.addRow("账号:", account_edit)
        layout.addRow("新密码:", password_edit)
        layout.addRow("姓名:", name_edit)
        layout.addRow("角色:", role_combo)
        layout.addRow("电话:", phone_edit)
        layout.addRow("信用分:", score_edit)

        btn_save = QPushButton("保存")
        btn_save.clicked.connect(
            lambda: self.submit_edit_user(
                dialog, 
                user["account"], # old_account
                account_edit.text(), # new_account
                password_edit.text(), # password
                name_edit.text(), 
                role_combo.currentText(), 
                phone_edit.text(), 
                score_edit.text()
            )
        )
        layout.addRow(btn_save)

        dialog.exec_()

    def submit_edit_user(self, dialog, old_account, new_account, password, name, role, phone, score):
        try:
            score_int = int(score)
        except ValueError:
            QMessageBox.warning(dialog, "错误", "信用分必须是整数")
            return
        
        new_account = new_account.strip()
        if not new_account:
            QMessageBox.warning(dialog, "错误", "账号不能为空")
            return

        password = password.strip()
        req = {
            "action": "admin_update_user",
            "data": {
                "old_account": old_account,
                "new_account": new_account,
                "password": password,
                "name": name, 
                "role": role, 
                "phone": phone, 
                "credit_score": score_int
            },
        }
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            QMessageBox.information(dialog, "成功", "更新成功")
            dialog.accept()
            self.load_users() # 刷新列表
            self.load_users()
        else:
            QMessageBox.warning(dialog, "错误", res.get("message", "更新失败"))

    def delete_user(self, account):
        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要删除用户 {account} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            req = {"action": "admin_delete_user", "data": {"account": account}}
            res = self.network.send_request(req)
            if res and res.get("status") == "success":
                self.load_users()
            else:
                QMessageBox.warning(self, "错误", res.get("message", "删除失败"))

    # ---------------- 预约管理 ---------------- #
    def setup_reservation_tab(self):
        self.res_tab = QWidget()
        self.tabs.addTab(self.res_tab, "预约管理")
        layout = QVBoxLayout(self.res_tab)

        btn_refresh = QPushButton("刷新列表")
        btn_refresh.clicked.connect(self.load_reservations)
        layout.addWidget(btn_refresh)

        self.res_table = QTableWidget()
        self.res_table.setColumnCount(7)
        self.res_table.setHorizontalHeaderLabels(["ID", "用户", "场馆", "场地", "日期", "时间", "状态/操作"])
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.res_table)

        self.load_reservations()

    def load_reservations(self):
        req = {"action": "admin_get_all_reservations"}
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            reservations = res.get("data", [])
            self.res_table.setRowCount(len(reservations))
            for i, r in enumerate(reservations):
                self.res_table.setItem(i, 0, QTableWidgetItem(str(r["id"])))
                self.res_table.setItem(i, 1, QTableWidgetItem(r["user"]))
                self.res_table.setItem(i, 2, QTableWidgetItem(r["venue"]))
                self.res_table.setItem(i, 3, QTableWidgetItem(r["court"]))
                self.res_table.setItem(i, 4, QTableWidgetItem(r["date"]))
                self.res_table.setItem(i, 5, QTableWidgetItem(r["time"]))

                status = r["status"]
                if status == "confirmed":
                    btn_cancel = QPushButton("强制取消")
                    btn_cancel.setStyleSheet("color: red;")
                    btn_cancel.clicked.connect(lambda checked, rid=r["id"]: self.cancel_reservation(rid))
                    self.res_table.setCellWidget(i, 6, btn_cancel)
                else:
                    self.res_table.setItem(i, 6, QTableWidgetItem(status))

    def cancel_reservation(self, res_id):
        reply = QMessageBox.question(
            self, "确认", "确定要强制取消该预约吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            req = {"action": "admin_cancel_reservation", "data": {"reservation_id": res_id}}
            res = self.network.send_request(req)
            if res and res.get("status") == "success":
                self.load_reservations()
            else:
                QMessageBox.warning(self, "错误", res.get("message", "取消失败"))

    # ---------------- 公告管理 ---------------- #
    def setup_announcement_tab(self):
        self.ann_tab = QWidget()
        self.tabs.addTab(self.ann_tab, "公告管理")
        layout = QVBoxLayout(self.ann_tab)

        form_layout = QFormLayout()
        self.ann_title = QLineEdit()
        self.ann_content = QTextEdit()
        self.ann_content.setMaximumHeight(100)
        self.ann_start = QDateEdit()
        self.ann_start.setDate(QDate.currentDate())
        self.ann_end = QDateEdit()
        self.ann_end.setDate(QDate.currentDate().addDays(7))

        btn_pub = QPushButton("发布公告")
        btn_pub.clicked.connect(self.publish_announcement)

        form_layout.addRow("标题:", self.ann_title)
        form_layout.addRow("内容:", self.ann_content)
        form_layout.addRow("开始日期:", self.ann_start)
        form_layout.addRow("结束日期:", self.ann_end)
        form_layout.addRow(btn_pub)
        layout.addLayout(form_layout)

        layout.addWidget(QLabel("有效公告列表:"))
        self.ann_table = QTableWidget()
        self.ann_table.setColumnCount(5)
        self.ann_table.setHorizontalHeaderLabels(["ID", "标题", "内容", "有效期", "操作"])
        self.ann_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.ann_table)

        btn_refresh = QPushButton("刷新列表")
        btn_refresh.clicked.connect(self.load_announcements)
        layout.addWidget(btn_refresh)

        self.load_announcements()

    def publish_announcement(self):
        title = self.ann_title.text()
        content = self.ann_content.toPlainText()
        start = self.ann_start.date().toString("yyyy-MM-dd")
        end = self.ann_end.date().toString("yyyy-MM-dd")

        if not title or not content:
            QMessageBox.warning(self, "错误", "标题和内容不能为空")
            return

        req = {
            "action": "admin_add_announcement",
            "data": {"title": title, "content": content, "start_date": start, "end_date": end},
        }
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            QMessageBox.information(self, "成功", "发布成功")
            self.ann_title.clear()
            self.ann_content.clear()
            self.load_announcements()
        else:
            QMessageBox.warning(self, "错误", res.get("message", "发布失败"))

    def load_announcements(self):
        req = {"action": "get_announcements"}
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            anns = res.get("data", [])
            self.ann_table.setRowCount(len(anns))
            for i, a in enumerate(anns):
                self.ann_table.setItem(i, 0, QTableWidgetItem(str(a["id"])))
                self.ann_table.setItem(i, 1, QTableWidgetItem(a["title"]))
                self.ann_table.setItem(i, 2, QTableWidgetItem(a["content"]))
                self.ann_table.setItem(i, 3, QTableWidgetItem(f"{a['start_date']} ~ {a['end_date']}"))

                btn_del = QPushButton("删除")
                btn_del.setStyleSheet("color: red;")
                btn_del.clicked.connect(lambda checked, aid=a["id"]: self.delete_announcement(aid))
                self.ann_table.setCellWidget(i, 4, btn_del)

    def delete_announcement(self, ann_id):
        req = {"action": "admin_delete_announcement", "data": {"ann_id": ann_id}}
        res = self.network.send_request(req)
        if res and res.get("status") == "success":
            self.load_announcements()
        else:
            QMessageBox.warning(self, "错误", res.get("message", "删除失败"))
