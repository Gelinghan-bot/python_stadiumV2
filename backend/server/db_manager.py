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

    @staticmethod
    def _normalize_time_str(time_str):
        parts = time_str.strip().split(":")
        if len(parts) == 2:
            hour, minute = parts
            second = "00"
        elif len(parts) == 3:
            hour, minute, second = parts
        else:
            raise ValueError("invalid time format")
        return f"{int(hour):02d}:{int(minute):02d}:{int(second):02d}"

    @staticmethod
    def _time_to_seconds(time_str):
        normalized = DBManager._normalize_time_str(time_str)
        hour, minute, second = normalized.split(":")
        return int(hour) * 3600 + int(minute) * 60 + int(second)

    @staticmethod
    def _iter_hour_blocks(start_time, end_time):
        import datetime
        start_norm = DBManager._normalize_time_str(start_time)
        end_norm = DBManager._normalize_time_str(end_time)
        start_dt = datetime.datetime.strptime(start_norm, "%H:%M:%S")
        end_dt = datetime.datetime.strptime(end_norm, "%H:%M:%S")
        if end_dt <= start_dt:
            raise ValueError("end_time must be after start_time")
        start_floor = start_dt.replace(minute=0, second=0)
        if start_floor > start_dt:
            start_floor -= datetime.timedelta(hours=1)
        if end_dt.minute == 0 and end_dt.second == 0:
            end_ceil = end_dt
        else:
            end_ceil = end_dt.replace(minute=0, second=0) + datetime.timedelta(hours=1)
        blocks = []
        current = start_floor
        while current < end_ceil:
            next_dt = current + datetime.timedelta(hours=1)
            blocks.append((current.strftime("%H:%M:%S"), next_dt.strftime("%H:%M:%S")))
            current = next_dt
        return blocks

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
            cursor.execute("SELECT user_account, name, role, credit_score FROM users WHERE user_account=? AND password=?", (account, password))
            user = cursor.fetchone()
            
            if user:  # 登录成功，返回用户信息
                user_info = {
                    "account": user[0],
                    "name": user[1],
                    "role": user[2],
                    "credit_score": user[3]
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

    def delete_user_account(self, account, password):
        """
        用户自行注销账号
        1. 验证密码
        2. 取消所有未完成的预约（释放名额）
        3. 删除用户
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 1. 验证密码
            cursor.execute("SELECT user_account FROM users WHERE user_account=? AND password=?", (account, password))
            if not cursor.fetchone():
                return False, "密码错误"

            # 2. 处理未完成的预约 (confirmed/queued)
            # 查找所有需要取消的预约
            cursor.execute("SELECT reservation_id, slot_id, status FROM reservations WHERE user_account=? AND status IN ('confirmed', 'queued')", (account,))
            active_reservations = cursor.fetchall()

            import datetime
            cancel_time = datetime.datetime.now()

            for res_id, slot_id, status in active_reservations:
                # 更新预约状态为 cancelled
                cursor.execute("UPDATE reservations SET status='cancelled', cancel_time=? WHERE reservation_id=?", (cancel_time, res_id))
                
                # 如果是 confirmed，需要释放名额并检查候补
                if status == 'confirmed':
                    # 释放名额
                    cursor.execute("UPDATE time_slots SET current_reservations = current_reservations - 1 WHERE slot_id=?", (slot_id,))
                    
                    # 检查候补 (复用之前的逻辑)
                    cursor.execute("""
                        SELECT r.reservation_id, r.user_account 
                        FROM reservations r
                        JOIN users u ON r.user_account = u.user_account
                        WHERE r.slot_id = ? AND r.status = 'queued'
                        ORDER BY u.credit_score DESC, r.create_time ASC
                        LIMIT 1
                    """, (slot_id,))
                    queued_user = cursor.fetchone()
                    if queued_user:
                        q_res_id, q_user_acc = queued_user
                        # 候补转正
                        cursor.execute("UPDATE reservations SET status = 'confirmed' WHERE reservation_id = ?", (q_res_id,))
                        # 占用名额
                        cursor.execute("UPDATE time_slots SET current_reservations = current_reservations + 1 WHERE slot_id = ?", (slot_id,))

            # 3. 清理其他关联数据
            cursor.execute("DELETE FROM credit_logs WHERE user_account=?", (account,))
            cursor.execute("DELETE FROM class_schedules WHERE teacher_account=?", (account,))

            # 4. 删除用户
            cursor.execute("DELETE FROM users WHERE user_account=?", (account,))
            
            conn.commit()
            return True, "账号已注销"
        except Exception as e:
            conn.rollback()
            return False, f"注销失败: {str(e)}"
        finally:
            conn.close()

    def get_available_slots(self, venue_id, date_str):
        """
        查询某场馆某天的可用时间段
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            # 校验日期范围：只能查询未来3天 (Today ~ Today+2)
            today = datetime.date.today()
            query_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            
            max_date = today + datetime.timedelta(days=2)
            
            if query_date < today or query_date > max_date:
                return False, "只能查询未来3天内的号源"
            
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
            # 1. 检查用户信用分与角色
            cursor.execute("SELECT credit_score, role FROM users WHERE user_account=?", (user_account,))
            user_res = cursor.fetchone()
            if not user_res:
                return False, "用户不存在"
            credit_score, role = user_res
            
            # 逻辑：信用分限制 (低于60分禁止预约)
            if credit_score <= 60:
                return False, "您的信用分过低(≤60)，已被禁止预约。请等待一周后恢复。"
            
            # 2. 检查时间段状态 (容量、是否热门)
            cursor.execute("""
                SELECT ts.current_reservations, ts.max_reservations, ts.is_hot,
                       ts.start_time, ts.end_time, ts.date, c.venue_id
                FROM time_slots ts
                JOIN courts c ON ts.court_id = c.court_id
                WHERE ts.slot_id = ?
            """, (slot_id,))
            slot_res = cursor.fetchone()
            if not slot_res:
                return False, "时间段不存在"
            current_res, max_res, is_hot, start_time, end_time, date_str, venue_id = slot_res
            
            if role == "student":
                try:
                    slot_start = self._normalize_time_str(start_time)
                    slot_end = self._normalize_time_str(end_time)
                except ValueError:
                    return False, "时间段格式异常"
                slot_start_sec = self._time_to_seconds(slot_start)
                slot_end_sec = self._time_to_seconds(slot_end)
                slot_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                slot_weekday = slot_date.weekday()

                cursor.execute("""
                    SELECT start_time, end_time, end_date
                    FROM class_schedules
                    WHERE venue_id = ? AND day_of_week = ? AND (end_date IS NULL OR end_date >= ?)
                """, (venue_id, slot_weekday, date_str))
                for sched_start, sched_end, sched_end_date in cursor.fetchall():
                    try:
                        sched_start_norm = self._normalize_time_str(sched_start)
                        sched_end_norm = self._normalize_time_str(sched_end)
                    except ValueError:
                        continue
                    sched_start_sec = self._time_to_seconds(sched_start_norm)
                    sched_end_sec = self._time_to_seconds(sched_end_norm)
                    if sched_start_sec < slot_end_sec and sched_end_sec > slot_start_sec:
                        return False, "该时段已被教师课表占用，暂不可预约"
            
            # --- 热门时段信用分优先排队逻辑 ---
            # 判断是否为指定热门时段: 周六/周日 19:00-21:00 且 max_reservations > 1
            is_special_hot = False
            try:
                slot_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                weekday = slot_date.weekday() # 0=Mon, 5=Sat, 6=Sun
                hour = int(start_time.split(':')[0])
                
                if (weekday == 5 or weekday == 6) and (19 <= hour < 21) and max_res > 1:
                    is_special_hot = True
            except:
                pass

            if is_special_hot:
                # 逻辑: 如果已满，进入候补队列(queued)
                if current_res >= max_res:
                    # 检查是否已在队列中
                    cursor.execute("SELECT reservation_id FROM reservations WHERE user_account=? AND slot_id=? AND status='queued'", (user_account, slot_id))
                    if cursor.fetchone():
                        return False, "您已在候补队列中"
                    
                    # 插入候补记录
                    create_time = datetime.datetime.now()
                    cursor.execute("""
                        INSERT INTO reservations (user_account, slot_id, status, create_time)
                        VALUES (?, ?, 'queued', ?)
                    """, (user_account, slot_id, create_time))
                    conn.commit()
                    return True, "预约已满，已加入候补队列（信用分优先）"
            else:
                # 普通逻辑: 如果满了，无法预约
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
                WHERE r.user_account = ? AND r.slot_id = ? AND r.status IN ('confirmed', 'queued')
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
            
            if status == 'cancelled':
                return False, "预约已取消"
            
            # 2. 执行取消 (事务)
            cancel_time = datetime.datetime.now()
            
            # 更新预约状态
            cursor.execute("""
                UPDATE reservations 
                SET status = 'cancelled', cancel_time = ?
                WHERE reservation_id = ?
            """, (cancel_time, reservation_id))
            
            # 如果是排队状态，直接取消，不影响名额
            if status == 'queued':
                conn.commit()
                return True, "排队已取消"

            # 如果是已确认状态，释放名额并检查候补
            if status == 'confirmed':
                # 先减少人数
                cursor.execute("""
                    UPDATE time_slots 
                    SET current_reservations = current_reservations - 1 
                    WHERE slot_id = ?
                """, (slot_id,))
                
                # 检查候补队列 (信用分优先: 分数高优先，同分先到先得)
                cursor.execute("""
                    SELECT r.reservation_id, r.user_account 
                    FROM reservations r
                    JOIN users u ON r.user_account = u.user_account
                    WHERE r.slot_id = ? AND r.status = 'queued'
                    ORDER BY u.credit_score DESC, r.create_time ASC
                    LIMIT 1
                """, (slot_id,))
                
                queued_user = cursor.fetchone()
                if queued_user:
                    q_res_id, q_user_acc = queued_user
                    # 候补转正
                    cursor.execute("""
                        UPDATE reservations 
                        SET status = 'confirmed' 
                        WHERE reservation_id = ?
                    """, (q_res_id,))
                    
                    # 占用名额
                    cursor.execute("""
                        UPDATE time_slots 
                        SET current_reservations = current_reservations + 1 
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
            
            try:
                start_time = self._normalize_time_str(start_time)
                end_time = self._normalize_time_str(end_time)
                time_blocks = self._iter_hour_blocks(start_time, end_time)
            except ValueError:
                return False, "时间格式错误，应为 HH:MM 或 HH:MM:SS"
            
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
                        for block_start, block_end in time_blocks:
                            start_prefix = f"{block_start[:5]}%"
                            end_prefix = f"{block_end[:5]}%"
                            # 检查时间段是否存在
                            cursor.execute("""
                                SELECT slot_id, max_reservations, current_reservations 
                                FROM time_slots 
                                WHERE court_id = ? AND date = ? AND start_time LIKE ? AND end_time LIKE ?
                            """, (court_id, date_str, start_prefix, end_prefix))
                            
                            slot_rows = cursor.fetchall()
                            
                            if slot_rows:
                                # --- 情况A: 时间段已存在 ---
                                for s_id, s_max, s_curr in slot_rows:
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
                                    
                                    # A3. 为教师创建预约
                                    cursor.execute("""
                                        SELECT reservation_id FROM reservations 
                                        WHERE slot_id = ? AND user_account = ? AND status = 'confirmed'
                                    """, (s_id, teacher_account))
                                    
                                    if not cursor.fetchone():
                                        cursor.execute("""
                                            INSERT INTO reservations (user_account, slot_id, status, create_time)
                                            VALUES (?, ?, 'confirmed', ?)
                                        """, (teacher_account, s_id, datetime.datetime.now()))
                                
                            else:
                                # --- 情况B: 时间段不存在 (按需生成) ---
                                s_max = 1 # 默认容量
                                
                                cursor.execute("""
                                    INSERT INTO time_slots (court_id, date, start_time, end_time, max_reservations, current_reservations, is_hot)
                                    VALUES (?, ?, ?, ?, ?, ?, 0)
                                """, (court_id, date_str, block_start, block_end, s_max, s_max)) # 直接设为满员
                                s_id = cursor.lastrowid

                                # --- 为教师创建预约 ---
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
            cursor.execute("SELECT venue_id, day_of_week, start_time, end_time, end_date FROM class_schedules WHERE schedule_id=?", (schedule_id,))
            schedule = cursor.fetchone()
            if not schedule:
                return False, "课表不存在"
            
            venue_id, day_of_week, start_time, end_time, end_date_str = schedule
            try:
                start_time = self._normalize_time_str(start_time)
                end_time = self._normalize_time_str(end_time)
                time_blocks = self._iter_hour_blocks(start_time, end_time)
            except ValueError:
                return False, "课表时间格式错误"
            
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

            cursor.execute("SELECT court_id FROM courts WHERE venue_id = ?", (venue_id,))
            courts = cursor.fetchall()
            court_ids = [c[0] for c in courts]
            
            for court_id in court_ids:
                for block_start, block_end in time_blocks:
                    start_prefix = f"{block_start[:5]}%"
                    end_prefix = f"{block_end[:5]}%"
                    cursor.execute("""
                        SELECT slot_id, date, start_time, end_time 
                        FROM time_slots 
                        WHERE court_id = ? AND date >= ? AND date <= ? AND start_time LIKE ? AND end_time LIKE ?
                    """, (court_id, today_str, end_date_str, start_prefix, end_prefix))
                    
                    slots = cursor.fetchall()
                    
                    for slot in slots:
                        s_id, s_date_str, s_start, s_end = slot
                        
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

                            # 如果该时间段在未来3天之外，直接删除该 time_slot 记录,如果在3天内，则保留（因为普通用户可见可约）
                            max_rolling_date = today + datetime.timedelta(days=2)
                            s_date_obj = datetime.datetime.strptime(s_date_str, '%Y-%m-%d').date()
                            
                            if s_date_obj > max_rolling_date:
                                cursor.execute("DELETE FROM time_slots WHERE slot_id = ?", (s_id,))
            
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
            
             # --- 任务3: 自动维护号源 (滚动3天) ---
            self._auto_manage_slots(cursor, today_date)

            conn.commit()
            return True, f"任务执行完毕. 处理爽约:{len(noshow_list)}人"
            
        except Exception as e:
            conn.rollback()
            print(f"[Task Error] {e}")
            return False, str(e)
        finally:
            conn.close()

    def _auto_manage_slots(self, cursor, today_date):
        """
        内部方法：自动维护号源
        1. 删除过期号源 (date <= today)
        2. 确保未来3天 (today+1, today+2, today+3) 的号源存在
        """
        import datetime
        print("[Task] 开始维护time_slots...")
        
        # 1. 清理过期号源
        # 策略修改：仅删除“过去且未被预约”的号源，保留有预约记录的号源以供历史查询
        # 这样既能清理垃圾数据，又能保证用户能查到历史订单
        cursor.execute("""
            DELETE FROM time_slots 
            WHERE date <= ? 
            AND slot_id NOT IN (SELECT DISTINCT slot_id FROM reservations)
        """, (today_date,))
        deleted_count = cursor.rowcount
        print(f"[Task] 已清理未使用的过期号源: {deleted_count} 条 (保留了有历史订单的号源)")
        
        # 2. 生成未来3天号源
        # 获取所有场地及其所属场馆名称
        cursor.execute("""
            SELECT c.court_id, v.venue_name 
            FROM courts c
            JOIN venues v ON c.venue_id = v.venue_id
        """)
        courts = cursor.fetchall()
        
        if not courts:
            print("[Task] 无场地，跳过生成")
            return

        # 遍历未来3天 (1, 2, 3)
        for i in range(3):
            target_date = today_date + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            
            # 遍历时间 9:00 - 22:00
            for h in range(9, 22):
                start_time = f"{h:02d}:00:00"
                end_time = f"{h+1:02d}:00:00"
                
                for cid, v_name in courts:
                    # 根据场馆类型设置最大预约人数
                    # 健身房和游泳馆容量为100，其他场馆（如羽毛球、网球等）为1
                    if v_name in ["健身房", "游泳馆"]:
                        max_res = 100
                    else:
                        max_res = 1

                    # 检查是否存在
                    cursor.execute("""
                        SELECT slot_id FROM time_slots 
                        WHERE court_id=? AND date=? AND start_time=?
                    """, (cid, date_str, start_time))
                    
                    if not cursor.fetchone():
                        # 插入新号源
                        cursor.execute("""
                            INSERT INTO time_slots (court_id, date, start_time, end_time, max_reservations, current_reservations, is_hot)
                            VALUES (?, ?, ?, ?, ?, 0, 0)
                        """, (cid, date_str, start_time, end_time, max_res))
        
        print("[Task] time_slots自动生成&删除维护已完成")

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

    def admin_update_user(self, old_account, new_account, password, name, role, phone, credit_score):
        """
        更新用户信息 (支持修改账号和密码)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if password is not None:
                password = password.strip()
            
            if new_account:
                new_account = new_account.strip()
            if old_account:
                old_account = old_account.strip()

            # 1. 如果修改了账号，先检查新账号是否存在
            if new_account and new_account != old_account:
                cursor.execute("SELECT 1 FROM users WHERE user_account=?", (new_account,))
                if cursor.fetchone():
                    return False, "新账号已存在"

            # 2. 构建更新语句
            # 基本字段
            update_fields = ["name=?", "role=?", "phone=?", "credit_score=?"]
            params = [name, role, phone, credit_score]

            # 如果有新密码
            if password:
                update_fields.append("password=?")
                params.append(password)

            # 如果修改了账号
            if new_account and new_account != old_account:
                update_fields.append("user_account=?")
                params.append(new_account)
            
            # WHERE 条件使用旧账号
            params.append(old_account)
            
            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE user_account=?"
            cursor.execute(sql, params)
            if cursor.rowcount == 0:
                conn.rollback()
                return False, "用户不存在或更新失败"

            # 3. 如果修改了账号，需要手动更新所有关联表 (因为 SQLite 默认不开启 FK 级联更新)
            if new_account and new_account != old_account:
                # 更新 reservations
                cursor.execute("UPDATE reservations SET user_account=? WHERE user_account=?", (new_account, old_account))
                # 更新 credit_logs
                cursor.execute("UPDATE credit_logs SET user_account=? WHERE user_account=?", (new_account, old_account))
                # 更新 announcements
                cursor.execute("UPDATE announcements SET author_account=? WHERE author_account=?", (new_account, old_account))
                # 更新 class_schedules
                cursor.execute("UPDATE class_schedules SET teacher_account=? WHERE teacher_account=?", (new_account, old_account))

            if password:
                target_account = new_account if new_account and new_account != old_account else old_account
                # 验证密码是否更新成功 (可选，但为了保险起见)
                # cursor.execute("SELECT password FROM users WHERE user_account=?", (target_account,))
                # pwd_row = cursor.fetchone()
                # if not pwd_row or pwd_row[0] != password:
                #     conn.rollback()
                #     return False, "密码更新失败"

            conn.commit()
            return True, "更新成功"
        except Exception as e:
            conn.rollback()
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
            # 获取 slot_id 与状态
            cursor.execute("SELECT slot_id, status FROM reservations WHERE reservation_id=?", (reservation_id,))
            res = cursor.fetchone()
            if not res:
                return False, "预约不存在"
            slot_id, status = res

            # 删除预约记录
            cursor.execute("DELETE FROM reservations WHERE reservation_id=?", (reservation_id,))
            
            # 释放名额（仅对占用名额的状态）
            if status in ("confirmed", "checked_in", "no_show"):
                cursor.execute("""
                    UPDATE time_slots
                    SET current_reservations = CASE
                        WHEN current_reservations > 0 THEN current_reservations - 1
                        ELSE 0
                    END
                    WHERE slot_id = ?
                """, (slot_id,))
            
            conn.commit()
            return True, "取消成功"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def add_announcement(self, title, content, start_date, end_date, author_account=None):
        """发布公告/帖子"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            create_time = datetime.datetime.now()
            cursor.execute("INSERT INTO announcements (title, content, start_date, end_date, create_time, author_account) VALUES (?, ?, ?, ?, ?, ?)",
                           (title, content, start_date, end_date, create_time, author_account))
            conn.commit()
            return True, "发布成功"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def get_announcements(self):
        """获取有效公告/帖子"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            today = datetime.date.today()
            # Join with users table to get author name and role
            sql = """
                SELECT a.announcement_id, a.title, a.content, a.start_date, a.end_date, a.create_time, 
                       u.name, u.role, a.author_account
                FROM announcements a
                LEFT JOIN users u ON a.author_account = u.user_account
                WHERE a.end_date >= ?
                ORDER BY a.create_time DESC
            """
            cursor.execute(sql, (today,))
            rows = cursor.fetchall()
            anns = []
            for row in rows:
                anns.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "start_date": row[3],
                    "end_date": row[4],
                    "create_time": row[5],
                    "author_name": row[6] if row[6] else "管理员", # Default if null (old data)
                    "author_role": row[7] if row[7] else "admin", # Default if null
                    "author_account": row[8]
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
