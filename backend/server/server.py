import socket
import threading
import json
import sys
import os

# 将项目根目录添加到 sys.path，以便导入 server.db_manager
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from server.db_manager import DBManager
    from server.statistics_manager import StatisticsManager
except ImportError:
    # Fallback for direct execution
    sys.path.append(current_dir)
    from db_manager import DBManager
    from statistics_manager import StatisticsManager

class SportsVenueServer:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.db_manager = DBManager()
        self.stats_manager = StatisticsManager()
        self.running = True

    def handle_client(self, client_socket):
        try:
            while True:
                # 接收数据 (最大 4096 字节)
                request_data = client_socket.recv(4096).decode('utf-8')
                if not request_data:
                    break
                
                print(f"[>] 收到请求: {request_data}")
                
                try:
                    request = json.loads(request_data)
                    response = self.process_request(request)
                except json.JSONDecodeError:
                    response = {"status": "error", "message": "无效的 JSON 格式"}
                except Exception as e:
                    response = {"status": "error", "message": f"服务器内部错误: {str(e)}"}
                
                # 发送响应
                # ensure_ascii=False 允许直接输出中文，而不是 Unicode 编码
                response_data = json.dumps(response, ensure_ascii=False)
                print(f"[<] 发送响应: {response_data}")
                client_socket.send(response_data.encode('utf-8'))
                
        except ConnectionResetError:
            print(f"[*] 客户端强制断开连接")
        except Exception as e:
            print(f"[!] 客户端处理错误: {e}")
        finally:
            print(f"[*] 连接关闭")
            client_socket.close()

    def process_request(self, request):
        """
        根据请求的 action 字段分发处理逻辑
        """
        action = request.get('action')
        data = request.get('data')
        # 请求不同的操作——>调用不同的处理函数
        if action == 'login':
            return self.handle_login(data)
        elif action == 'register':
            return self.handle_register(data)
        elif action == 'get_available_slots':  #获取场馆各个场地时间段(各场地预约情况)
            return self.handle_get_slots(data)
        elif action == 'book_venue':  #预约操作
            return self.handle_book(data)
        elif action == 'get_my_reservations':  #查看我的预约
            return self.handle_get_reservations(data)
        elif action == 'cancel_booking':
            return self.handle_cancel(data)
        elif action == 'add_schedule':  #教室导课
            return self.handle_add_schedule(data)
        elif action == 'remove_schedule':  #教室删课
            return self.handle_remove_schedule(data)
        elif action == 'get_my_schedules':  #获取教师课表
            return self.handle_get_schedules(data)
        elif action == 'check_in':    # 签到(完成预约，否则扣信用分)
            return self.handle_check_in(data)
        elif action == 'delete_my_account': # 用户自行注销
            return self.handle_delete_my_account(data)
        # --- Admin Actions ---
        elif action == 'admin_get_venues':
            return self.handle_admin_get_venues(data)
        elif action == 'admin_add_venue':
            return self.handle_admin_add_venue(data)
        elif action == 'admin_update_venue':
            return self.handle_admin_update_venue(data)
        elif action == 'admin_delete_venue':
            return self.handle_admin_delete_venue(data)
        elif action == 'admin_get_courts':
            return self.handle_admin_get_courts(data)
        elif action == 'admin_add_court':
            return self.handle_admin_add_court(data)
        elif action == 'admin_delete_court':
            return self.handle_admin_delete_court(data)
        elif action == 'admin_get_users':
            return self.handle_admin_get_users(data)
        elif action == 'admin_update_user':
            return self.handle_admin_update_user(data)
        elif action == 'admin_delete_user':
            return self.handle_admin_delete_user(data)
        elif action == 'admin_get_all_reservations':  #管理员获取预约列表
            return self.handle_admin_get_all_reservations(data)
        elif action == 'admin_cancel_reservation':  #管理员强制取消预约
            return self.handle_admin_cancel_reservation(data)
        elif action == 'admin_add_announcement':   #管理员发布公告
            return self.handle_admin_add_announcement(data)
        elif action == 'get_announcements':
            return self.handle_get_announcements(data)
        elif action == 'admin_delete_announcement':
            return self.handle_admin_delete_announcement(data)
        elif action == 'add_post': # 用户发帖
            return self.handle_add_post(data)
        # --- Statistics Actions ---
        elif action == 'get_venue_stats':
            return self.handle_get_venue_stats(data)
        elif action == 'get_heatmap_data':
            return self.handle_get_heatmap_data(data)
        elif action == 'get_user_stats':
            return self.handle_get_user_stats(data)
        else:
            return {"status": "error", "message": f"未知的请求类型: {action}"}

    def handle_register(self, data):
        if not data:
            return {"status": "error", "message": "缺少请求数据"}
            
        account = data.get('account')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role')
        phone = data.get('phone')
        
        # 简单校验
        if not all([account, password, name, role]):
             return {"status": "error", "message": "账号、密码、姓名、角色为必填项"}
             
        success, message = self.db_manager.register_user(account, password, name, role, phone)
        
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_login(self, data):
        if not data:
            return {"status": "error", "message": "缺少请求数据"}
            
        account = data.get('account')
        password = data.get('password')
        
        if not account or not password:
            return {"status": "error", "message": "账号或密码不能为空"}
            
        success, result = self.db_manager.validate_login(account, password)
        
        if success:
            return {"status": "success", "message": "登录成功", "user": result}
        else:
            return {"status": "fail", "message": result}

    def handle_get_slots(self, data):
        venue_id = data.get('venue_id')
        date_str = data.get('date')
        if not venue_id or not date_str:
            return {"status": "error", "message": "缺少场馆ID或日期"}
        
        success, result = self.db_manager.get_available_slots(venue_id, date_str)
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_book(self, data):
        user_account = data.get('user_account')
        slot_id = data.get('slot_id')
        
        if not user_account or not slot_id:
            return {"status": "error", "message": "缺少用户账号或时间段ID"}
            
        success, message = self.db_manager.create_reservation(user_account, slot_id)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_get_reservations(self, data):
        user_account = data.get('user_account')
        if not user_account:
            return {"status": "error", "message": "缺少用户账号"}
            
        success, result = self.db_manager.get_user_reservations(user_account)
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_cancel(self, data):
        user_account = data.get('user_account')
        reservation_id = data.get('reservation_id')
        
        if not user_account or not reservation_id:
            return {"status": "error", "message": "缺少必要参数"}
            
        success, message = self.db_manager.cancel_reservation(user_account, reservation_id)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_add_schedule(self, data):
        teacher_account = data.get('teacher_account')
        venue_id = data.get('venue_id')
        day_of_week = data.get('day_of_week') # 0-6
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not all([teacher_account, venue_id, day_of_week is not None, start_time, end_time]):
            return {"status": "error", "message": "缺少必要参数"}
            
        success, message = self.db_manager.add_teacher_schedule(teacher_account, venue_id, int(day_of_week), start_time, end_time)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_remove_schedule(self, data):
        teacher_account = data.get('teacher_account')
        schedule_id = data.get('schedule_id')
        
        if not teacher_account or not schedule_id:
            return {"status": "error", "message": "缺少必要参数"}
            
        success, message = self.db_manager.remove_teacher_schedule(teacher_account, schedule_id)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_get_schedules(self, data):
        teacher_account = data.get('teacher_account')
        if not teacher_account:
            return {"status": "error", "message": "缺少必要参数"}
            
        success, result = self.db_manager.get_teacher_schedules(teacher_account)
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_check_in(self, data):
        user_account = data.get('user_account')
        reservation_id = data.get('reservation_id')
        
        if not user_account or not reservation_id:
            return {"status": "error", "message": "缺少必要参数"}
            
        success, message = self.db_manager.check_in_reservation(user_account, reservation_id)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_delete_my_account(self, data):
        account = data.get('account')
        password = data.get('password')
        if not account or not password:
            return {"status": "error", "message": "缺少账号或密码"}
            
        success, message = self.db_manager.delete_user_account(account, password)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    # --- Admin Handlers ---

    def handle_admin_get_venues(self, data):
        success, result = self.db_manager.admin_get_venues()
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_admin_add_venue(self, data):
        name = data.get('name')
        is_outdoor = data.get('is_outdoor')
        location = data.get('location')
        description = data.get('description')
        success, message = self.db_manager.admin_add_venue(name, is_outdoor, location, description)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_admin_update_venue(self, data):
        venue_id = data.get('venue_id')
        name = data.get('name')
        is_outdoor = data.get('is_outdoor')
        location = data.get('location')
        description = data.get('description')
        success, message = self.db_manager.admin_update_venue(venue_id, name, is_outdoor, location, description)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_admin_delete_venue(self, data):
        venue_id = data.get('venue_id')
        success, message = self.db_manager.admin_delete_venue(venue_id)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_admin_get_courts(self, data):
        venue_id = data.get('venue_id')
        success, result = self.db_manager.admin_get_courts(venue_id)
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_admin_add_court(self, data):
        venue_id = data.get('venue_id')
        name = data.get('name')
        success, message = self.db_manager.admin_add_court(venue_id, name)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_admin_delete_court(self, data):
        court_id = data.get('court_id')
        success, message = self.db_manager.admin_delete_court(court_id)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_admin_get_users(self, data):
        success, result = self.db_manager.admin_get_users()
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_admin_update_user(self, data):
        old_account = data.get('old_account') # 原账号
        new_account = data.get('new_account') # 新账号 (可选)
        password = data.get('password')       # 新密码 (可选)
        name = data.get('name')
        role = data.get('role')
        phone = data.get('phone')
        credit_score = data.get('credit_score')
        
        # 兼容旧接口：如果只传了 account，视为 old_account
        if not old_account and data.get('account'):
            old_account = data.get('account')

        success, message = self.db_manager.admin_update_user(old_account, new_account, password, name, role, phone, credit_score)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_admin_delete_user(self, data):
        account = data.get('account')
        success, message = self.db_manager.admin_delete_user(account)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_admin_get_all_reservations(self, data):
        success, result = self.db_manager.admin_get_all_reservations()
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_admin_cancel_reservation(self, data):
        reservation_id = data.get('reservation_id')
        success, message = self.db_manager.admin_cancel_reservation(reservation_id)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_admin_add_announcement(self, data):
        title = data.get('title')
        content = data.get('content')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        author_account = data.get('account') # 尝试获取管理员账号
        success, message = self.db_manager.add_announcement(title, content, start_date, end_date, author_account)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    def handle_add_post(self, data):
        """处理用户发帖"""
        title = data.get('title')
        content = data.get('content')
        author_account = data.get('account')
        
        if not all([title, content, author_account]):
             return {"status": "error", "message": "标题、内容和账号不能为空"}

        # 用户帖子默认有效期一年
        import datetime
        start_date = datetime.date.today().isoformat()
        end_date = (datetime.date.today() + datetime.timedelta(days=365)).isoformat()
        
        success, message = self.db_manager.add_announcement(title, content, start_date, end_date, author_account)
        if success:
            return {"status": "success", "message": "发帖成功"}
        else:
            return {"status": "fail", "message": message}

    def handle_get_announcements(self, data):
        success, result = self.db_manager.get_announcements()
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_admin_delete_announcement(self, data):
        ann_id = data.get('ann_id')
        success, message = self.db_manager.admin_delete_announcement(ann_id)
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "fail", "message": message}

    # --- Statistics Handlers ---
    def handle_get_venue_stats(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        success, result = self.stats_manager.get_venue_stats(start_date, end_date)
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_get_heatmap_data(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        success, result = self.stats_manager.get_heatmap_data(start_date, end_date)
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def handle_get_user_stats(self, data):
        user_account = data.get('user_account')
        if not user_account:
            return {"status": "error", "message": "缺少用户账号"}
        success, result = self.stats_manager.get_user_stats(user_account)
        if success:
            return {"status": "success", "data": result}
        else:
            return {"status": "fail", "message": result}

    def start_scheduler(self):
        """
        启动后台定时任务线程
        """
        import time
        import datetime
        
        def run_schedule():
            print("[Scheduler] 定时任务线程已启动")
            while self.running:
                now = datetime.datetime.now()
                # 每小时的 00 分执行一次 (例如 10:00, 11:00, 12:00...)
                if now.minute == 0:
                    print(f"[Scheduler] 开始执行定时维护任务 @ {now}")
                    self.db_manager.process_daily_tasks()
                    # 休眠 61 秒防止重复执行
                    time.sleep(61)
                else:
                    # 每 30 秒检查一次时间
                    time.sleep(30)
        
        scheduler_thread = threading.Thread(target=run_schedule)
        scheduler_thread.daemon = True
        scheduler_thread.start()

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[*] 服务器已启动，监听 {self.host}:{self.port}")
            
            # 启动时立即执行一次维护任务 (确保号源更新)
            print("[*] 正在执行启动时自检维护...")
            self.db_manager.process_daily_tasks()

            # 启动定时任务
            self.start_scheduler()
            
            print(f"[*] 等待客户端连接...")
            
            while self.running:
                client_sock, addr = self.server_socket.accept()
                print(f"[*] 接受连接来自: {addr}")
                
                # 为每个客户端创建一个独立的线程进行处理
                client_handler = threading.Thread(target=self.handle_client, args=(client_sock,))
                client_handler.daemon = True # 设置为守护线程，主程序退出时自动结束
                client_handler.start()
        except Exception as e:
            print(f"[!] 服务器启动失败: {e}")
        finally:
            self.server_socket.close()

if __name__ == '__main__':
    # 可以在这里配置 IP 和 端口
    server = SportsVenueServer()
    server.start()
