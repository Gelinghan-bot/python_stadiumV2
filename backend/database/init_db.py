import sqlite3
import os

def init_db(db_path='database/sports_venue.db', schema_path='database/schema.sql'):
    """
    初始化数据库
    """
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
            cursor.executescript(schema_sql)
        print(f"数据库已成功初始化: {db_path}")
        print("表结构已根据 schema.sql 创建。")
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    # 假设脚本在项目根目录下运行，或者直接运行
    # 如果直接运行此脚本，需要调整路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    db_file = os.path.join(current_dir, 'sports_venue.db')
    schema_file = os.path.join(current_dir, 'schema.sql')
    
    init_db(db_file, schema_file)
