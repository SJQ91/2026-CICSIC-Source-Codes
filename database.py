import sqlite3

def init_db():
    conn = sqlite3.connect("medicine_box.db")
    cursor = conn.cursor()

    #设备表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS device (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_name TEXT NOT NULL,
        device_id TEXT UNIQUE NOT NULL, --设备编号
        online_status INTEGER DEFAULT 0,
        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    #药仓表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS medicine_box (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        box_num INTEGER NOT NULL UNIQUE,
        device_id INTEGER NOT NULL,
        status INTEGER DEFAULT 0,
        open_count INTEGER DEFAULT 0,
        FOREIGN KEY(device_id) REFERENCES device(id)
    )
    ''')

    # 初始化设备(携带唯一设备编号)
    cursor.execute("INSERT OR IGNORE INTO device(device_name,device_id,online_status) VALUES ('智能药盒01','dev_001',1)")
    for i in range(1,5):
        cursor.execute('''
        INSERT OR IGNORE INTO medicine_box(box_num,device_id,status,open_count)
        VALUES (?,1,0,0)
        ''',(i,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()