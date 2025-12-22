import socket
import json
import time
import sys
import os
import sqlite3

#该py文件用于后端开发时模拟客户操作
# 配置
HOST = '127.0.0.1'
PORT = 8888

def send_request(sock, request):
    """发送请求并接收响应"""
    try:
        sock.send(json.dumps(request).encode('utf-8'))
        response_data = sock.recv(4096).decode('utf-8')
        return json.loads(response_data)
    except Exception as e:
        print(f"[!] 请求失败: {e}")
        return None

def verify_database(teacher_account):
    """直接查询数据库验证结果"""
    print("\n--- [数据库验证] ---")
    db_path = os.path.join(os.getcwd(), 'backend', 'database', 'sports_venue.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 验证 class_schedules
    print("[1] 检查 class_schedules 表:")
    cursor.execute("SELECT schedule_id, day_of_week, start_time, end_time, end_date FROM class_schedules WHERE teacher_account=?", (teacher_account,))
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"    √ 找到课表规则: ID={row[0]}, 星期={row[1]}, 时间={row[2]}-{row[3]}, 截止={row[4]}")
    else:
        print("    × 未找到课表规则")

    # 2. 验证 reservations
    print("\n[2] 检查 reservations 表 (前5条):")
    cursor.execute("""
        SELECT r.reservation_id, ts.date, ts.start_time, r.status 
        FROM reservations r
        JOIN time_slots ts ON r.slot_id = ts.slot_id
        WHERE r.user_account=?
        ORDER BY ts.date ASC
        LIMIT 5
    """, (teacher_account,))
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"    √ 自动预约: 日期={row[1]}, 时间={row[2]}, 状态={row[3]}")
    else:
        print("    × 未找到预约记录")

    conn.close()

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"[*] 连接服务器 {HOST}:{PORT}...")
        client.connect((HOST, PORT))
        
        # 1. 登录
        print("\n[*] 正在模拟李四登录...")
        login_req = {
            "action": "login",
            "data": {
                "account": "2021002",
                "password": "123456" # 假设密码是这个，基于 test_addData.py
            }
        }
        resp = send_request(client, login_req)
        print(f"[<] 登录响应: {resp}")
        
        if resp and resp.get('status') == 'success':
            user_info = resp.get('user')
            print(f"    -> 登录成功: {user_info['name']} ({user_info['role']})")
            
            # 2. 获取场地ID (为了构建请求)
            # 这里我们需要先知道篮球场的ID，实际GUI中会先调用 get_venues
            # 为了简化，我们假设篮球场ID是通过某种方式获取的，或者我们先发个请求查一下
            # 这里直接硬编码或者查库获取一个ID用于测试
            # 既然是模拟，我们先查一下库获取ID，保证请求有效
            db_path = os.path.join(os.getcwd(), 'backend', 'database', 'sports_venue.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT court_id FROM courts WHERE court_name LIKE '%篮球场%' LIMIT 1")
            res = cursor.fetchone()
            conn.close()
            
            if not res:
                print("[!] 错误: 数据库中没有篮球场")
                return
            court_id = res[0]
            
            # 3. 录入课表
            print(f"\n[*] 正在录入课表: 篮球场(ID={court_id}), 周一 10:00-11:00")
            schedule_req = {
                "action": "add_schedule",
                "data": {
                    "teacher_account": "2021002",
                    "court_id": court_id,
                    "day_of_week": 0, # 周一
                    "start_time": "10:00",
                    "end_time": "11:00"
                }
            }
            resp = send_request(client, schedule_req)
            print(f"[<] 录入响应: {resp}")
            
            if resp and resp.get('status') == 'success':
                print("    -> 课表录入成功！")
                
                # 4. 验证结果
                verify_database("2021002")
            else:
                print(f"    -> 录入失败: {resp.get('message')}")
                
        else:
            print("    -> 登录失败")

    except ConnectionRefusedError:
        print("[!] 无法连接服务器，请确认服务器已启动")
    except Exception as e:
        print(f"[!] 发生错误: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()