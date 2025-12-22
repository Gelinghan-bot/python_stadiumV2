import sqlite3
import os
import datetime
import random

# 获取数据库路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'sports_venue.db')

def test_addData():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"正在向 {DB_PATH} 插入测试数据...")
    
    try:
        # 1. 插入测试用户
        users = [
            ('2021001', '123456', '张三', 'student', '13800138000', 100, datetime.datetime.now()),
            ('2021002', '123456', '李四', 'teacher', '13900139000', 100, datetime.datetime.now()),
            ('admin', 'admin888', '管理员', 'admin', '10086', 100, datetime.datetime.now())
        ]
        
        for user in users:
            try:
                cursor.execute("""
                    INSERT INTO users (user_account, password, name, role, phone, credit_score, create_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, user)
                print(f"已添加用户: {user[0]} ({user[2]})")
            except sqlite3.IntegrityError:
                print(f"用户 {user[0]} 已存在，跳过。")

        # 2. 插入场馆和场地
        # 格式: (名称, 是否户外, 场地数量, 描述, max_reservations)
        venues_data = [
            ("足球场", True, 1, "标准11人制足球场", 1),
            ("篮球场", True, 6, "室外塑胶篮球场", 1),
            ("排球场", True, 2, "室外排球场", 1),
            ("网球场", True, 3, "标准硬地网球场", 1),
            ("羽毛球馆", False, 8, "室内木地板羽毛球场", 1),
            ("乒乓球馆", False, 8, "专业乒乓球台", 1),
            ("健身房", False, 1, "综合器械健身区", 100),
            ("台球室", False, 8, "英式斯诺克/美式黑八", 1),
            ("游泳馆", False, 1, "恒温标准泳池", 100)
        ]

        today = datetime.date.today()
        
        for v_name, is_outdoor, court_count, desc, max_res in venues_data:
            # 检查场馆是否存在
            cursor.execute("SELECT venue_id FROM venues WHERE venue_name=?", (v_name,))
            res = cursor.fetchone()
            
            if res:
                venue_id = res[0]
                print(f"场馆 {v_name} 已存在 (ID: {venue_id})")
            else:
                cursor.execute("""
                    INSERT INTO venues (venue_name, is_outdoor, location, description)
                    VALUES (?, ?, ?, ?)
                """, (v_name, is_outdoor, "北校区体育中心", desc))
                venue_id = cursor.lastrowid
                print(f"已添加场馆: {v_name} (ID: {venue_id})")

                # 添加场地
                for i in range(1, court_count + 1):
                    court_name = f"{v_name} {i}号场" if court_count > 1 else f"{v_name}"
                    cursor.execute("""
                        INSERT INTO courts (venue_id, court_name)
                        VALUES (?, ?)
                    """, (venue_id, court_name))
                    court_id = cursor.lastrowid
                    
                    # 3. 为每个场地生成未来 3 天的时间段 (9:00 - 22:00, 每小时一个)
                    # 恢复为仅生成3天，因为教师课表逻辑已改为按需生成
                    for day_offset in range(3):
                        target_date = today + datetime.timedelta(days=day_offset)
                        
                        for hour in range(9, 22):
                            start_time = datetime.time(hour, 0)
                            end_time = datetime.time(hour + 1, 0)
                            
                            # 简单逻辑：晚上 19-21 点设为热门
                            is_hot = 1 if 19 <= hour < 21 else 0
                            
                            cursor.execute("""
                                INSERT INTO time_slots (court_id, date, start_time, end_time, max_reservations, current_reservations, is_hot)
                                VALUES (?, ?, ?, ?, ?, 0, ?)
                            """, (court_id, target_date, start_time.strftime("%H:%M"), end_time.strftime("%H:%M"), max_res, is_hot))

        # 4. 添加一些示例预约
        # 获取一个时间段 ID
        cursor.execute("SELECT slot_id FROM time_slots LIMIT 1")
        slot_res = cursor.fetchone()
        if slot_res:
            slot_id = slot_res[0]
            try:
                cursor.execute("""
                    INSERT INTO reservations (user_account, slot_id, status, create_time)
                    VALUES (?, ?, ?, ?)
                """, ('2021001', slot_id, 'confirmed', datetime.datetime.now()))
                
                # 更新该时间段的预约人数
                cursor.execute("UPDATE time_slots SET current_reservations = current_reservations + 1 WHERE slot_id=?", (slot_id,))
                print("已添加示例预约")
            except Exception as e:
                print(f"添加预约失败 (可能已存在): {e}")

        conn.commit()
        print("所有测试数据插入完成。")
        
    except Exception as e:
        print(f"插入数据时出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    test_addData()
