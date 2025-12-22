import sys
import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# 设置中文字体，防止乱码
matplotlib.rcParams['font.sans-serif'] = ['SimHei'] 
matplotlib.rcParams['axes.unicode_minus'] = False

# 添加 backend 路径以便导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'backend')
sys.path.append(backend_path)

from server.statistics_manager import StatisticsManager

def test_and_visualize():
    print("正在初始化统计管理器...")
    stats = StatisticsManager()
    
    # 创建输出目录
    output_dir = os.path.join(current_dir, 'stats_output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    print(f"图表将保存至: {output_dir}")

    # --- 1. 测试场馆利用率 (柱状图) ---
    print("\n[1/3] 生成场馆预约统计柱状图...")
    success, data = stats.get_venue_stats()
    if success and data:
        venues = [item['venue_name'] for item in data]
        counts = [item['reservation_count'] for item in data]
        rates = [item['utilization_rate'] for item in data]

        fig, ax1 = plt.subplots(figsize=(10, 6))

        # 柱状图 - 预约次数
        ax1.bar(venues, counts, color='skyblue', label='预约次数')
        ax1.set_xlabel('场馆')
        ax1.set_ylabel('预约次数', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')

        # 折线图 - 预约率
        ax2 = ax1.twinx()
        ax2.plot(venues, rates, color='red', marker='o', label='预约率(%)')
        ax2.set_ylabel('预约率 (%)', color='red')
        ax2.tick_params(axis='y', labelcolor='red')

        plt.title('场馆预约情况统计 (近30天)')
        plt.savefig(os.path.join(output_dir, 'venue_stats.png'))
        print("  -> 已保存 venue_stats.png")
        plt.close()
    else:
        print("  -> 获取数据失败或无数据")

    # --- 2. 测试热力图 ---
    print("\n[2/3] 生成预约热力图...")
    success, result = stats.get_heatmap_data()
    if success and result:
        x_labels = result['x_axis'] # 周一..周日
        y_labels = result['y_axis'] # 9:00..21:00
        raw_data = result['data']   # [[x, y, val], ...]

        # 转换数据为矩阵格式
        matrix = np.zeros((len(y_labels), len(x_labels)))
        for item in raw_data:
            x, y, val = item
            # 注意：matplotlib imshow 的 y 轴通常是从上到下的，
            # 我们的 y_axis 是 9:00, 10:00... 对应索引 0, 1...
            # 所以 matrix[y, x] = val 是正确的
            matrix[y, x] = val

        plt.figure(figsize=(10, 8))
        plt.imshow(matrix, cmap='YlOrRd', aspect='auto')
        
        # 设置轴标签
        plt.xticks(range(len(x_labels)), x_labels)
        plt.yticks(range(len(y_labels)), y_labels)
        
        plt.colorbar(label='预约热度')
        plt.title('场馆预约热力图 (星期 x 时间段)')
        
        # 在格子里显示数值
        for i in range(len(y_labels)):
            for j in range(len(x_labels)):
                val = matrix[i, j]
                if val > 0:
                    plt.text(j, i, int(val), ha='center', va='center', color='black')

        plt.savefig(os.path.join(output_dir, 'heatmap.png'))
        print("  -> 已保存 heatmap.png")
        plt.close()
    else:
        print("  -> 获取数据失败")

    # --- 3. 测试用户个人统计 (折线图) ---
    test_user = '李四' # 假设测试 admin 用户
    print(f"\n[3/3] 生成用户 {test_user} 的运动趋势图...")
    success, result = stats.get_user_stats(test_user)
    if success:
        trend = result['weekly_trend']
        dates = trend['dates']
        counts = trend['counts']
        
        plt.figure(figsize=(10, 5))
        plt.plot(dates, counts, marker='o', linestyle='-', color='green')
        plt.title(f'用户 {test_user} 最近7天运动趋势')
        plt.xlabel('日期')
        plt.ylabel('运动次数')
        plt.grid(True)
        
        # 标注数值
        for a, b in zip(dates, counts):
            plt.text(a, b, str(b), ha='center', va='bottom')
            
        plt.savefig(os.path.join(output_dir, 'user_stats.png'))
        print("  -> 已保存 user_stats.png")
        plt.close()
        
        print(f"  -> 最常去场馆: {result['top_venues']}")
    else:
        print("  -> 获取数据失败")

    print(f"\n所有图表已生成完毕，请查看 {output_dir} 目录。")

if __name__ == "__main__":
    test_and_visualize()
