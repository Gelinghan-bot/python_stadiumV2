import sqlite3
import os
import datetime
import calendar

# 获取数据库路径 (与 db_manager 保持一致)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'sports_venue.db')

class StatisticsManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_venue_stats(self, start_date_str=None, end_date_str=None):
        """
        【维度1：按场馆统计】
        分析指定日期范围内的：预约次数、使用时长、预约率
        
        :param start_date_str: 'YYYY-MM-DD' (默认30天前)
        :param end_date_str: 'YYYY-MM-DD' (默认今天)
        :return: list of dict
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 1. 处理日期范围
            today = datetime.date.today()
            if not end_date_str:
                end_date = today
            else:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            if not start_date_str:
                start_date = end_date - datetime.timedelta(days=30)
            else:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()

            days_count = (end_date - start_date).days + 1
            if days_count <= 0:
                return False, "结束日期必须晚于开始日期"

            # 2. 获取所有场馆及其场地数量 (用于计算理论容量)
            # 假设每天营业 9:00-22:00 共 13 个小时段
            OPERATING_HOURS = 13 
            
            cursor.execute("""
                SELECT v.venue_id, v.venue_name, COUNT(c.court_id)
                FROM venues v
                LEFT JOIN courts c ON v.venue_id = c.venue_id
                GROUP BY v.venue_id
            """)
            venues_info = cursor.fetchall() # [(id, name, court_count), ...]

            stats_list = []

            # 3. 遍历场馆进行统计
            for v_id, v_name, court_count in venues_info:
                if court_count == 0:
                    continue

                # 统计该场馆在范围内的有效预约数
                # 有效预约包括: confirmed (已预约), checked_in (已签到), no_show (爽约但占用了场地)
                # 不包括: cancelled (已取消)
                sql_count = """
                    SELECT COUNT(r.reservation_id)
                    FROM reservations r
                    JOIN time_slots ts ON r.slot_id = ts.slot_id
                    JOIN courts c ON ts.court_id = c.court_id
                    WHERE c.venue_id = ? 
                    AND ts.date >= ? AND ts.date <= ?
                    AND r.status IN ('confirmed', 'checked_in', 'no_show', 'completed')
                """
                cursor.execute(sql_count, (v_id, start_date, end_date))
                res_count = cursor.fetchone()[0]

                # 计算指标
                # 理论总容量 = 天数 * 每天工时 * 场地数
                total_capacity = days_count * OPERATING_HOURS * court_count
                
                # 预约率
                utilization_rate = round((res_count / total_capacity) * 100, 2) if total_capacity > 0 else 0
                
                # 使用时长 (假设每个 slot 是 1 小时)
                total_hours = res_count * 1

                stats_list.append({
                    "venue_name": v_name,
                    "reservation_count": res_count, # 用于柱状图
                    "total_hours": total_hours,
                    "utilization_rate": utilization_rate,
                    "capacity_info": f"{court_count}个场地 x {days_count}天"
                })

            # 按预约次数降序排列
            stats_list.sort(key=lambda x: x['reservation_count'], reverse=True)
            
            return True, stats_list

        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def get_heatmap_data(self, start_date_str=None, end_date_str=None):
        """
        【维度2：按时间段统计】
        生成热力图数据：统计一周中 星期几(X轴) x 时间段(Y轴) 的热门程度
        
        :return: dict { "x_axis": [周一...周日], "y_axis": [9:00...21:00], "data": [[x, y, value], ...] }
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 默认统计过去 90 天的数据，样本越多热力图越准
            today = datetime.date.today()
            if not end_date_str:
                end_date = today
            else:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            if not start_date_str:
                start_date = end_date - datetime.timedelta(days=90)
            else:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()

            # SQLite strftime('%w', date) 返回 0-6，0是周日，1是周一... 6是周六
            # 我们需要转换成 0=周一 ... 6=周日 以符合中国习惯
            
            sql = """
                SELECT 
                    strftime('%w', ts.date) as weekday,
                    substr(ts.start_time, 1, 2) as hour_str,
                    COUNT(r.reservation_id) as count
                FROM reservations r
                JOIN time_slots ts ON r.slot_id = ts.slot_id
                WHERE ts.date >= ? AND ts.date <= ?
                AND r.status IN ('confirmed', 'checked_in', 'no_show', 'completed')
                GROUP BY weekday, hour_str
            """
            cursor.execute(sql, (start_date, end_date))
            rows = cursor.fetchall()

            # 初始化矩阵 (7天 x 13个时段)
            # X轴: 0-6 (周一到周日)
            # Y轴: 0-12 (对应 9:00 到 21:00)
            # data格式: [[x, y, value], [x, y, value]...]
            
            heatmap_data = []
            
            # 建立映射字典以便快速填充
            # key: (weekday_iso, hour_index) -> value: count
            data_map = {}
            
            for row in rows:
                db_weekday = int(row[0]) # 0(Sun) - 6(Sat)
                hour_str = row[1] # "09", "10"...
                count = row[2]
                
                # 转换星期: SQLite 0=Sun -> ISO 6=Sun; SQLite 1=Mon -> ISO 0=Mon
                # 映射关系: (db_weekday - 1) % 7
                # Sun(0) -> -1 -> 6
                # Mon(1) -> 0 -> 0
                iso_weekday = (db_weekday - 1) % 7
                
                # 转换时间: 09:00 -> index 0
                hour_index = int(hour_str) - 9
                
                if 0 <= hour_index <= 12:
                    data_map[(iso_weekday, hour_index)] = count

            # 填充数据列表 (ECharts 格式)
            for d in range(7): # 0..6
                for h in range(13): # 0..12
                    val = data_map.get((d, h), 0)
                    heatmap_data.append([d, h, val])

            result = {
                "x_axis": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                "y_axis": [f"{h}:00" for h in range(9, 22)], # 9:00 - 21:00
                "data": heatmap_data,
                "max_value": max([x[2] for x in heatmap_data]) if heatmap_data else 0
            }
            
            return True, result

        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def get_user_stats(self, user_account):
        """
        【维度3：用户个人统计】
        1. 最近7天运动趋势 (折线图)
        2. 最常去场馆 Top3
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            import datetime
            today = datetime.date.today()
            seven_days_ago = today - datetime.timedelta(days=6) # 含今天共7天
            
            # --- Part 1: 最近7天运动趋势 ---
            # 初始化日期列表 (X轴)
            date_list = []
            activity_map = {}
            for i in range(7):
                d = seven_days_ago + datetime.timedelta(days=i)
                d_str = d.strftime("%Y-%m-%d")
                date_list.append(d_str)
                activity_map[d_str] = 0
            
            # 查询数据
            # 统计状态: confirmed, checked_in, completed. (排除 no_show 和 cancelled)
            sql_trend = """
                SELECT ts.date, COUNT(*)
                FROM reservations r
                JOIN time_slots ts ON r.slot_id = ts.slot_id
                WHERE r.user_account = ?
                AND ts.date >= ? AND ts.date <= ?
                AND r.status IN ('confirmed', 'checked_in', 'completed')
                GROUP BY ts.date
            """
            cursor.execute(sql_trend, (user_account, seven_days_ago, today))
            rows = cursor.fetchall()
            
            for r_date, count in rows:
                if r_date in activity_map:
                    activity_map[r_date] = count
            
            # 构造 Y轴数据
            counts_list = [activity_map[d] for d in date_list]
            
            # --- Part 2: 最常去场馆 Top3 ---
            sql_fav = """
                SELECT v.venue_name, COUNT(*) as cnt
                FROM reservations r
                JOIN time_slots ts ON r.slot_id = ts.slot_id
                JOIN courts c ON ts.court_id = c.court_id
                JOIN venues v ON c.venue_id = v.venue_id
                WHERE r.user_account = ?
                AND r.status IN ('confirmed', 'checked_in', 'completed')
                GROUP BY v.venue_name
                ORDER BY cnt DESC
                LIMIT 3
            """
            cursor.execute(sql_fav, (user_account,))
            fav_rows = cursor.fetchall()
            
            fav_venues = []
            for v_name, cnt in fav_rows:
                fav_venues.append({"name": v_name, "count": cnt})
                
            return True, {
                "weekly_trend": {
                    "dates": date_list,
                    "counts": counts_list
                },
                "top_venues": fav_venues
            }
            
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

# --- 单元测试代码 ---
if __name__ == "__main__":
    # 可以在这里直接运行此文件测试逻辑
    stats = StatisticsManager()
    
    print("--- 测试1: 场馆利用率 ---")
    success, data = stats.get_venue_stats()
    if success:
        for item in data:
            print(f"场馆: {item['venue_name']} | 预约数: {item['reservation_count']} | 预约率: {item['utilization_rate']}%")
    else:
        print("Error:", data)

    print("\n--- 测试2: 热力图数据 ---")
    success, data = stats.get_heatmap_data()
    if success:
        print(f"X轴: {data['x_axis']}")
        print(f"数据点示例 (前5个): {data['data'][:5]}")
        print(f"最大热度: {data['max_value']}")
    else:
        print("Error:", data)

    print("\n--- 测试3: 用户个人统计 (测试账号: admin) ---")
    # 注意: 如果数据库里没有 admin 的运动数据，这里可能全是0
    success, data = stats.get_user_stats("admin") 
    if success:
        print("最近7天趋势:", data['weekly_trend'])
        print("最常去场馆:", data['top_venues'])
    else:
        print("Error:", data)
