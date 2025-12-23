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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt, QDate


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
        
        if not new_account:
            QMessageBox.warning(dialog, "错误", "账号不能为空")
            return

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
