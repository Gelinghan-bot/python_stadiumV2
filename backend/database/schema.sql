-- 1. 用户表 (users)
CREATE TABLE IF NOT EXISTS users (
    user_account TEXT PRIMARY KEY, -- 登录账号 (学号/工号)
    password TEXT NOT NULL, -- 加密后的密码
    name TEXT NOT NULL, -- 真实姓名
    role TEXT NOT NULL, -- 角色 (student/teacher/admin)
    phone TEXT, -- 联系方式
    credit_score INTEGER DEFAULT 100, -- 信用分
    create_time DATETIME NOT NULL -- 注册时间
);

-- 2. 场馆表 (venues)
CREATE TABLE IF NOT EXISTS venues (
    venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_name TEXT NOT NULL, -- 场馆名称 (如 "羽毛球馆")
    is_outdoor BOOLEAN NOT NULL, -- 是否户外 (0 = 室内, 1 = 户外)
    location TEXT, -- 场馆位置
    description TEXT -- 场馆描述
);

-- 3. 场地表 (courts)
CREATE TABLE IF NOT EXISTS courts (
    court_id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id INTEGER, -- 关联场馆 ID
    court_name TEXT NOT NULL, -- 场地名称 (如 "1 号场")
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
);

-- 4. 时间段表 (time_slots)
CREATE TABLE IF NOT EXISTS time_slots (
    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER, -- 关联场地 ID
    date DATE NOT NULL, -- 日期
    start_time TIME NOT NULL, -- 开始时间
    end_time TIME NOT NULL, -- 结束时间
    max_reservations INTEGER NOT NULL, -- 最大预约人数
    current_reservations INTEGER DEFAULT 0, -- 当前预约人数
    is_hot BOOLEAN DEFAULT 0, -- 是否热门时段 (0 = 否, 1 = 是)
    FOREIGN KEY (court_id) REFERENCES courts(court_id)
);

-- 5. 预约表 (reservations)
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_account TEXT, -- 关联用户账号
    slot_id INTEGER, -- 关联时间段 ID
    status TEXT NOT NULL, -- 状态 (confirmed/cancelled/no_show/pending_...)
    create_time DATETIME NOT NULL, -- 预约创建时间
    cancel_time DATETIME, -- 取消时间 (可空)
    FOREIGN KEY (user_account) REFERENCES users(user_account),
    FOREIGN KEY (slot_id) REFERENCES time_slots(slot_id)
);

-- 6. 信用记录表 (credit_logs)
CREATE TABLE IF NOT EXISTS credit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_account TEXT, -- 关联用户账号
    change_amount INTEGER NOT NULL, -- 分数变化 (正数加分, 负数扣分)
    reason TEXT NOT NULL, -- 变化原因 (如 "爽约扣分")
    time DATETIME NOT NULL, -- 记录时间
    FOREIGN KEY (user_account) REFERENCES users(user_account)
);

-- 7. 公告表 (announcements)
CREATE TABLE IF NOT EXISTS announcements (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, -- 公告标题
    content TEXT NOT NULL, -- 公告内容
    related_venue_id INTEGER, -- 关联场馆 ID (可空)
    start_date DATE NOT NULL, -- 生效日期
    end_date DATE NOT NULL, -- 失效日期
    create_time DATETIME NOT NULL, -- 创建时间
    FOREIGN KEY (related_venue_id) REFERENCES venues(venue_id)
);

-- 8. 天气表 (weather_info)
CREATE TABLE IF NOT EXISTS weather_info (
    weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL, -- 日期
    weather_text TEXT NOT NULL, -- 天气情况 (如 "中雨")
    temp_low INTEGER NOT NULL, -- 最低温度
    temp_high INTEGER NOT NULL, -- 最高温度
    update_time DATETIME NOT NULL -- 更新时间
);
-- 9. 教师课表 (class_schedules)
CREATE TABLE IF NOT EXISTS class_schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_account TEXT,
    venue_id INTEGER,
    day_of_week INTEGER, -- 0=Monday, 6=Sunday
    start_time TIME,
    end_time TIME,
    end_date DATE, -- 课表有效截止日期
    FOREIGN KEY (teacher_account) REFERENCES users(user_account),
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
);
