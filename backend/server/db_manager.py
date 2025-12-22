import sqlite3
import os

# 获取项目根目录 (假设此文件在 server/ 目录下)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'sports_venue.db')

class DBManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def validate_login(self, account, password):
        """
        验证登录
        :param account: 用户账号
        :param password: 密码 (暂未加密，实际应比对哈希)
        :return: (bool, str/dict) - (是否成功, 用户信息或错误消息)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 查询用户
            cursor.execute("SELECT user_account, name, role FROM users WHERE user_account=? AND password=?", (account, password))
            user = cursor.fetchone()
            
            if user:  # 登录成功，返回用户信息
                user_info = {
                    "account": user[0],
                    "name": user[1],
                    "role": user[2]
                }
                return True, user_info
            else:  #找不到user，登陆失败
                return False, "账号或密码错误"
        except Exception as e:
            return False, f"数据库错误: {str(e)}"
        finally:
            conn.close()

    def register_user(self, account, password, name, role, phone):
        """
        注册新用户
        :param account: 账号
        :param password: 密码
        :param name: 姓名
        :param role: 角色
        :param phone: 电话
        :return: (bool, str) - (是否成功, 消息)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            create_time = datetime.datetime.now()
            # 默认信用分 100
            cursor.execute("""
                INSERT INTO users (user_account, password, name, role, phone, credit_score, create_time)
                VALUES (?, ?, ?, ?, ?, 100, ?)
            """, (account, password, name, role, phone, create_time))
            conn.commit()
            return True, "注册成功"
        except sqlite3.IntegrityError:
            return False, "该账号已存在"
        except Exception as e:
            return False, f"注册失败: {str(e)}"
        finally:
            conn.close()

    def get_available_slots(self, venue_id, date_str):
        """
        查询某场馆某天的可用时间段
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 关联查询：时间段 -> 场地 -> 场馆
            # 查询所有时间段（包括已满），由前端判断是否可预约
            sql = """
                SELECT ts.slot_id, c.court_name, ts.start_time, ts.end_time, 
                       ts.current_reservations, ts.max_reservations, ts.is_hot
                FROM time_slots ts
                JOIN courts c ON ts.court_id = c.court_id
                WHERE c.venue_id = ? AND ts.date = ?
                ORDER BY ts.start_time, c.court_name
            """
            cursor.execute(sql, (venue_id, date_str))
            rows = cursor.fetchall()
            
            slots = []
            for row in rows:
                slots.append({
                    "slot_id": row[0],
                    "court_name": row[1],
                    "start_time": row[2],
                    "end_time": row[3],
                    "current": row[4],
                    "max": row[5],
                    "is_hot": row[6]
                })
            return True, slots
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def create_reservation(self, user_account, slot_id):
        """
        创建预约 (核心事务逻辑)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            # 1. 检查用户信用分
            cursor.execute("SELECT credit_score FROM users WHERE user_account=?", (user_account,))
            user_res = cursor.fetchone()
            if not user_res:
                return False, "用户不存在"
            credit_score = user_res[0]
            
            # 逻辑：信用分限制 (低于60分禁止预约)
            if credit_score <= 60:
                return False, "您的信用分过低(≤60)，已被禁止预约。请等待一周后恢复。"
            
            # 2. 检查时间段状态 (容量、是否热门)
            cursor.execute("SELECT current_reservations, max_reservations, is_hot, start_time FROM time_slots WHERE slot_id=?", (slot_id,))
            slot_res = cursor.fetchone()
            if not slot_res:
                return False, "时间段不存在"
            current_res, max_res, is_hot, start_time = slot_res
            # 逻辑：如果满了，无法预约
            if current_res >= max_res:
                return False, "该时段预约人数已满"
            
            # 逻辑：信用分限制 (示例：低于80分不能预约热门时段 - 可选)
            if is_hot and credit_score <= 80:
                 return False, "您的信用分低于80，无法预约热门时段"
            
            # 3. 检查用户是否在该时段已有预约 (防止冲突)
            # 这里简化处理，假设一个 slot_id 代表一个具体场地的具体时段
            # 如果是不同场地同一时间，可能需要更复杂的 SQL 判断 start_time
            cursor.execute("""
                SELECT r.reservation_id FROM reservations r
                WHERE r.user_account = ? AND r.slot_id = ? AND r.status = 'confirmed'
            """, (user_account, slot_id))
            if cursor.fetchone():
                return False, "您已预约过该时段，请勿重复预约"

            # 4. 执行预约 (事务开始)
            # 插入预约记录
            create_time = datetime.datetime.now()
            cursor.execute("""
                INSERT INTO reservations (user_account, slot_id, status, create_time)
                VALUES (?, ?, 'confirmed', ?)
            """, (user_account, slot_id, create_time))
            
            # 更新时间段的当前预约人数 (+1)
            cursor.execute("""
                UPDATE time_slots 
                SET current_reservations = current_reservations + 1 
                WHERE slot_id = ?
            """, (slot_id,))
            
            conn.commit() # 提交事务
            return True, "预约成功"
            
        except Exception as e:
            conn.rollback() # 发生错误回滚
            return False, f"预约失败: {str(e)}"
        finally:
            conn.close()

    def get_user_reservations(self, user_account):
        """
        获取用户的预约列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            sql = """
                SELECT r.reservation_id, v.venue_name, c.court_name, ts.date, ts.start_time, ts.end_time, r.status
                FROM reservations r
                JOIN time_slots ts ON r.slot_id = ts.slot_id
                JOIN courts c ON ts.court_id = c.court_id
                JOIN venues v ON c.venue_id = v.venue_id
                WHERE r.user_account = ?
                ORDER BY r.create_time DESC
            """
            cursor.execute(sql, (user_account,))
            rows = cursor.fetchall()
            
            res_list = []
            for row in rows:
                res_list.append({
                    "id": row[0],
                    "venue": row[1],
                    "court": row[2],
                    "date": row[3],
                    "time": f"{row[4]}-{row[5]}",
                    "status": row[6]
                })
            return True, res_list
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def cancel_reservation(self, user_account, reservation_id):
        """
        取消预约
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            
            # 1. 检查预约是否存在且属于该用户，且状态为 confirmed
            cursor.execute("""
                SELECT slot_id, status FROM reservations 
                WHERE reservation_id = ? AND user_account = ?
            """, (reservation_id, user_account))
            res = cursor.fetchone()
            
            if not res:
                return False, "预约不存在或无权操作"
            
            slot_id, status = res
            
            if status != 'confirmed':
                return False, f"当前状态({status})无法取消"
            
            # 2. 执行取消 (事务)
            cancel_time = datetime.datetime.now()
            
            # 更新预约状态
            cursor.execute("""
                UPDATE reservations 
                SET status = 'cancelled', cancel_time = ?
                WHERE reservation_id = ?
            """, (cancel_time, reservation_id))
            
            # 释放名额 (人数 -1)
            cursor.execute("""
                UPDATE time_slots 
                SET current_reservations = current_reservations - 1 
                WHERE slot_id = ?
            """, (slot_id,))
            
            conn.commit()
            return True, "取消成功"
            
        except Exception as e:
            conn.rollback()
            return False, f"取消失败: {str(e)}"
        finally:
            conn.close()

    def add_teacher_schedule(self, teacher_account, venue_id, day_of_week, start_time, end_time):
        """
        教师添加课表 (特权操作)
        :param venue_id: 场馆ID (锁定该场馆下所有场地)
        :param day_of_week: 0=周一 ... 6=周日
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            import calendar
            
            # 1. 验证身份
            cursor.execute("SELECT role FROM users WHERE user_account=?", (teacher_account,))
            user = cursor.fetchone()
            if not user or user[0] != 'teacher':
                return False, "只有教师可以执行此操作"

            # 2. 获取该场馆下的所有场地ID
            cursor.execute("SELECT court_id FROM courts WHERE venue_id = ?", (venue_id,))
            courts = cursor.fetchall()
            if not courts:
                return False, "该场馆下没有场地"
            
            court_ids = [c[0] for c in courts]

            # 3. 计算4个月后的日期 (作为课表截止日期)
            today = datetime.date.today()
            today_str = today.strftime('%Y-%m-%d')
            
            year = today.year + (today.month + 4 - 1) // 12
            month = (today.month + 4 - 1) % 12 + 1
            day = min(today.day, calendar.monthrange(year, month)[1])
            end_date_str = datetime.date(year, month, day).strftime('%Y-%m-%d')

            # 4. 插入课表记录 (记录截止日期)
            cursor.execute("""
                INSERT INTO class_schedules (teacher_account, venue_id, day_of_week, start_time, end_time, end_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (teacher_account, venue_id, day_of_week, start_time, end_time, end_date_str))
            
            # 5. 遍历未来4个月的每一天，按需生成或更新时间段
            current_date = today
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            while current_date <= end_date:
                if current_date.weekday() == day_of_week:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # 对该场馆下的每一个场地进行锁定
                    for court_id in court_ids:
                        # 检查时间段是否存在
                        cursor.execute("""
                            SELECT slot_id, max_reservations, current_reservations 
                            FROM time_slots 
                            WHERE court_id = ? AND date = ? AND start_time = ? AND end_time = ?
                        """, (court_id, date_str, start_time, end_time))
                        
                        slot_res = cursor.fetchone()
                        
                        if slot_res:
                            # --- 情况A: 时间段已存在 ---
                            s_id, s_max, s_curr = slot_res
                            
                            # A1. 取消冲突预约
                            cursor.execute("""
                                UPDATE reservations 
                                SET status = 'cancelled_by_teacher', cancel_time = ?
                                WHERE slot_id = ? AND user_account != ? AND status = 'confirmed'
                            """, (datetime.datetime.now(), s_id, teacher_account))
                            
                            # A2. 锁定场地
                            cursor.execute("""
                                UPDATE time_slots 
                                SET current_reservations = ? 
                                WHERE slot_id = ?
                            """, (s_max, s_id))
                            
                        else:
                            # --- 情况B: 时间段不存在 (按需生成) ---
                            s_max = 1 # 默认容量
                            
                            cursor.execute("""
                                INSERT INTO time_slots (court_id, date, start_time, end_time, max_reservations, current_reservations, is_hot)
                                VALUES (?, ?, ?, ?, ?, ?, 0)
                            """, (court_id, date_str, start_time, end_time, s_max, s_max)) # 直接设为满员
                            s_id = cursor.lastrowid

                        # --- 公共步骤: 为教师创建预约 ---
                        # 检查是否已预约
                        cursor.execute("""
                            SELECT reservation_id FROM reservations 
                            WHERE slot_id = ? AND user_account = ? AND status = 'confirmed'
                        """, (s_id, teacher_account))
                        
                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO reservations (user_account, slot_id, status, create_time)
                                VALUES (?, ?, 'confirmed', ?)
                            """, (teacher_account, s_id, datetime.datetime.now()))

                # 移动到下一天
                current_date += datetime.timedelta(days=1)

            conn.commit()
            return True, "课表导入成功，未来4个月的相关场地已锁定"
            
        except Exception as e:
            conn.rollback()
            return False, f"操作失败: {str(e)}"
        finally:
            conn.close()

    def remove_teacher_schedule(self, teacher_account, schedule_id):
        """
        教师移除课表 (解锁场地)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            import calendar
            
            # 1. 获取课表详情以用于查找受影响的 slot
            # 注意：这里需要获取 end_date，以便知道当初锁定了多久
            cursor.execute("SELECT court_id, day_of_week, start_time, end_time, end_date FROM class_schedules WHERE schedule_id=?", (schedule_id,))
            schedule = cursor.fetchone()
            if not schedule:
                return False, "课表不存在"
            
            court_id, day_of_week, start_time, end_time, end_date_str = schedule
            
            # 2. 删除课表记录
            cursor.execute("DELETE FROM class_schedules WHERE schedule_id=?", (schedule_id,))
            
            # 3. 解锁未来受影响的时间段 (使用当初记录的 end_date)
            today = datetime.date.today()
            today_str = today.strftime('%Y-%m-%d')
            
            # 如果 end_date 为空 (旧数据)，则默认按当前时间+4个月处理，或者直接跳过
            if not end_date_str:
                 # 兼容旧数据逻辑，或者直接报错。这里选择兼容：计算当前+4个月
                year = today.year + (today.month + 4 - 1) // 12
                month = (today.month + 4 - 1) % 12 + 1
                day = min(today.day, calendar.monthrange(year, month)[1])
                end_date_str = datetime.date(year, month, day).strftime('%Y-%m-%d')

            cursor.execute("""
                SELECT slot_id, date, start_time, end_time 
                FROM time_slots 
                WHERE court_id = ? AND date >= ? AND date <= ?
            """, (court_id, today_str, end_date_str))
            
            slots = cursor.fetchall()
            
            for slot in slots:
                s_id, s_date_str, s_start, s_end = slot
                
                if s_start[:5] != start_time[:5] or s_end[:5] != end_time[:5]:
                    continue
                
                s_date = datetime.datetime.strptime(s_date_str, '%Y-%m-%d').date()
                if s_date.weekday() != day_of_week:
                    continue
                
                # --- 匹配成功，执行解锁逻辑 ---
                
                # 检查该时间段是否确实被该教师预约了 (避免误操作其他人的预约)
                cursor.execute("""
                    SELECT reservation_id FROM reservations 
                    WHERE slot_id = ? AND user_account = ? AND status = 'confirmed'
                """, (s_id, teacher_account))
                
                if cursor.fetchone():
                    # A. 取消教师的预约
                    cursor.execute("""
                        UPDATE reservations 
                        SET status = 'cancelled', cancel_time = ?
                        WHERE slot_id = ? AND user_account = ? AND status = 'confirmed'
                    """, (datetime.datetime.now(), s_id, teacher_account))
                    
                    # B. 重置场地状态
                    # 只有在确认是教师锁定的情况下才重置
                    cursor.execute("""
                        UPDATE time_slots 
                        SET current_reservations = 0 
                        WHERE slot_id = ?
                    """, (s_id,))
            
            conn.commit()
            return True, "课表移除成功，场地已释放"
            
        except Exception as e:
            conn.rollback()
            return False, f"操作失败: {str(e)}"
        finally:
            conn.close()

    def get_teacher_schedules(self, teacher_account):
        """获取教师的课表列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            sql = """
                SELECT cs.schedule_id, v.venue_name, c.court_name, cs.day_of_week, cs.start_time, cs.end_time
                FROM class_schedules cs
                JOIN courts c ON cs.court_id = c.court_id
                JOIN venues v ON c.venue_id = v.venue_id
                WHERE cs.teacher_account = ?
            """
            cursor.execute(sql, (teacher_account,))
            rows = cursor.fetchall()
            
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            res = []
            for row in rows:
                res.append({
                    "id": row[0],
                    "venue": row[1],
                    "court": row[2],
                    "day_str": weekdays[row[3]],
                    "time": f"{row[4]}-{row[5]}"
                })
            return True, res
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def check_in_reservation(self, user_account, reservation_id):
        """
        用户签到 (防止爽约)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 检查预约状态
            cursor.execute("SELECT status FROM reservations WHERE reservation_id=? AND user_account=?", (reservation_id, user_account))
            res = cursor.fetchone()
            if not res:
                return False, "预约不存在"
            if res[0] != 'confirmed':
                return False, f"当前状态({res[0]})无法签到"
            
            # 更新状态为 checked_in
            cursor.execute("UPDATE reservations SET status='checked_in' WHERE reservation_id=?", (reservation_id,))
            conn.commit()
            return True, "签到成功"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def process_daily_tasks(self):
        """
        每日定时任务 (建议每晚10点执行)
        1. 扫描爽约记录 (已结束且未签到 -> 扣10分)
        2. 恢复信用分 (被禁用户一周后恢复)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            now = datetime.datetime.now()
            today_date = now.date()
            current_time_str = now.strftime('%H:%M:%S')
            
            # --- 任务1: 判定爽约 ---
            # 查找所有: 
            # 1. 状态为 'confirmed' (未签到)
            # 2. 对应的 slot 日期 < 今天 OR (日期=今天 AND 结束时间 < 当前时间)
            # 注意: 这里简化逻辑，假设只要结束时间过了且没签到就算爽约
            
            # 构造查询: 找出所有已结束但状态仍为 confirmed 的预约
            # 关联 time_slots 表比较时间
            sql_find_noshow = """
                SELECT r.reservation_id, r.user_account, ts.date, ts.end_time
                FROM reservations r
                JOIN time_slots ts ON r.slot_id = ts.slot_id
                WHERE r.status = 'confirmed'
                AND (ts.date < ? OR (ts.date = ? AND ts.end_time < ?))
            """
            cursor.execute(sql_find_noshow, (today_date, today_date, current_time_str))
            noshow_list = cursor.fetchall()
            
            for row in noshow_list:
                res_id, user_acc, r_date, r_end = row
                print(f"[Task] 发现爽约: 用户{user_acc} 预约ID{res_id} ({r_date} {r_end})")
                
                # 1. 更新预约状态
                cursor.execute("UPDATE reservations SET status='no_show' WHERE reservation_id=?", (res_id,))
                
                # 2. 扣除信用分 (10分)
                cursor.execute("UPDATE users SET credit_score = credit_score - 10 WHERE user_account=?", (user_acc,))
                
                # 3. 记录日志
                cursor.execute("""
                    INSERT INTO credit_logs (user_account, change_amount, reason, time)
                    VALUES (?, -10, '爽约扣分', ?)
                """, (user_acc, now))
            
            # --- 任务2: 恢复信用分 ---
            # 规则: 一周后用户信用分恢复100分
            # 逻辑: 查找当前信用分 <= 60 的用户
            # 检查他们最后一次扣分记录是否在 7 天前
            
            cursor.execute("SELECT user_account, credit_score FROM users WHERE credit_score <= 60")
            banned_users = cursor.fetchall()
            
            seven_days_ago = now - datetime.timedelta(days=7)
            
            for u_row in banned_users:
                u_acc, u_score = u_row
                
                # 查找该用户最后一次扣分时间
                cursor.execute("""
                    SELECT MAX(time) FROM credit_logs 
                    WHERE user_account = ? AND change_amount < 0
                """, (u_acc,))
                last_deduct_res = cursor.fetchone()
                
                should_restore = False
                if last_deduct_res and last_deduct_res[0]:
                    last_time_str = last_deduct_res[0]
                    # SQLite datetime 可能是字符串，需解析
                    # 假设格式为 YYYY-MM-DD HH:MM:SS.ssssss 或 YYYY-MM-DD HH:MM:SS
                    try:
                        # 尝试解析 (简化处理，直接比较字符串通常也行，如果格式标准)
                        last_time = datetime.datetime.strptime(last_time_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                        if last_time < seven_days_ago:
                            should_restore = True
                    except Exception as e:
                        print(f"[Task] 解析时间出错: {e}")
                else:
                    # 如果没有扣分记录但分低(可能是手动改的?)，或者记录丢失，默认恢复? 
                    # 为了安全，暂不恢复，或者直接恢复
                    pass

                if should_restore:
                    print(f"[Task] 用户 {u_acc} 封禁期已过，恢复信用分至 100")
                    cursor.execute("UPDATE users SET credit_score = 100 WHERE user_account=?", (u_acc,))
                    cursor.execute("""
                        INSERT INTO credit_logs (user_account, change_amount, reason, time)
                        VALUES (?, ?, '封禁期满恢复', ?)
                    """, (u_acc, 100 - u_score, now))

            conn.commit()
            return True, f"任务执行完毕. 处理爽约:{len(noshow_list)}人"
            
        except Exception as e:
            conn.rollback()
            print(f"[Task Error] {e}")
            return False, str(e)
        finally:
            conn.close()

    # 管理员功能↓--- Admin Functions ---

    def admin_get_venues(self):
        """获取所有场馆信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM venues")
            rows = cursor.fetchall()
            venues = []
            for row in rows:
                venues.append({
                    "venue_id": row[0],
                    "venue_name": row[1],
                    "is_outdoor": bool(row[2]),
                    "location": row[3],
                    "description": row[4]
                })
            return True, venues
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_add_venue(self, name, is_outdoor, location, description):
        """添加场馆"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO venues (venue_name, is_outdoor, location, description) VALUES (?, ?, ?, ?)",
                           (name, is_outdoor, location, description))
            conn.commit()
            return True, "添加成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_update_venue(self, venue_id, name, is_outdoor, location, description):
        """更新场馆"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE venues SET venue_name=?, is_outdoor=?, location=?, description=? WHERE venue_id=?",
                           (name, is_outdoor, location, description, venue_id))
            conn.commit()
            return True, "更新成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_delete_venue(self, venue_id):
        """删除场馆"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 级联删除场地? 或者检查是否有场地
            cursor.execute("DELETE FROM venues WHERE venue_id=?", (venue_id,))
            conn.commit()
            return True, "删除成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_get_courts(self, venue_id):
        """获取某场馆的所有场地"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM courts WHERE venue_id=?", (venue_id,))
            rows = cursor.fetchall()
            courts = []
            for row in rows:
                courts.append({
                    "court_id": row[0],
                    "venue_id": row[1],
                    "court_name": row[2]
                })
            return True, courts
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_add_court(self, venue_id, name):
        """添加场地"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO courts (venue_id, court_name) VALUES (?, ?)", (venue_id, name))
            conn.commit()
            return True, "添加成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_delete_court(self, court_id):
        """删除场地"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM courts WHERE court_id=?", (court_id,))
            conn.commit()
            return True, "删除成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_get_users(self):
        """获取所有用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_account, name, role, phone, credit_score FROM users")
            rows = cursor.fetchall()
            users = []
            for row in rows:
                users.append({
                    "account": row[0],
                    "name": row[1],
                    "role": row[2],
                    "phone": row[3],
                    "credit_score": row[4]
                })
            return True, users
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_update_user(self, account, name, role, phone, credit_score):
        """更新用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET name=?, role=?, phone=?, credit_score=? WHERE user_account=?",
                           (name, role, phone, credit_score, account))
            conn.commit()
            return True, "更新成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_delete_user(self, account):
        """删除用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE user_account=?", (account,))
            conn.commit()
            return True, "删除成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_get_all_reservations(self):
        """获取所有预约"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            sql = """
                SELECT r.reservation_id, r.user_account, v.venue_name, c.court_name, ts.date, ts.start_time, ts.end_time, r.status
                FROM reservations r
                JOIN time_slots ts ON r.slot_id = ts.slot_id
                JOIN courts c ON ts.court_id = c.court_id
                JOIN venues v ON c.venue_id = v.venue_id
                ORDER BY r.create_time DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            res_list = []
            for row in rows:
                res_list.append({
                    "id": row[0],
                    "user": row[1],
                    "venue": row[2],
                    "court": row[3],
                    "date": row[4],
                    "time": f"{row[5]}-{row[6]}",
                    "status": row[7]
                })
            return True, res_list
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_cancel_reservation(self, reservation_id):
        """管理员强制取消预约"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            # 获取 slot_id
            cursor.execute("SELECT slot_id FROM reservations WHERE reservation_id=?", (reservation_id,))
            res = cursor.fetchone()
            if not res:
                return False, "预约不存在"
            slot_id = res[0]

            # 更新状态
            cursor.execute("UPDATE reservations SET status='cancelled_by_admin', cancel_time=? WHERE reservation_id=?", 
                           (datetime.datetime.now(), reservation_id))
            
            # 释放名额
            cursor.execute("UPDATE time_slots SET current_reservations = current_reservations - 1 WHERE slot_id=?", (slot_id,))
            
            conn.commit()
            return True, "取消成功"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def admin_add_announcement(self, title, content, start_date, end_date):
        """发布公告"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            create_time = datetime.datetime.now()
            cursor.execute("INSERT INTO announcements (title, content, start_date, end_date, create_time) VALUES (?, ?, ?, ?, ?)",
                           (title, content, start_date, end_date, create_time))
            conn.commit()
            return True, "发布成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def get_announcements(self):
        """获取有效公告"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            today = datetime.date.today()
            cursor.execute("SELECT * FROM announcements WHERE end_date >= ? ORDER BY create_time DESC", (today,))
            rows = cursor.fetchall()
            anns = []
            for row in rows:
                anns.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "start_date": row[4],
                    "end_date": row[5]
                })
            return True, anns
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def admin_delete_announcement(self, ann_id):
        """删除公告"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM announcements WHERE announcement_id=?", (ann_id,))
            conn.commit()
            return True, "删除成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
