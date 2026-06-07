from fastapi import APIRouter, Query
import sqlite3
from datetime import datetime, date

router = APIRouter(
    prefix="/box",
    tags=["药仓管理接口"]
)

def get_db_connection():
    conn = sqlite3.connect("medicine_box.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS medicine_box (
        box_num INTEGER PRIMARY KEY,
        box_name TEXT,
        lock_status INTEGER DEFAULT 1,
        open_count INTEGER DEFAULT 0,
        lock_count INTEGER DEFAULT 0
    )''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS device (
        device_id TEXT PRIMARY KEY,
        status INTEGER DEFAULT 0
    )''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS box_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        box_num INTEGER,
        operate_type TEXT,
        operate_time TEXT
    )''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS system_config (
        id INTEGER PRIMARY KEY,
        last_reset_date TEXT
    )''')

    boxes = [(1,"一号药仓",1,0,0),(2,"二号药仓",1,0,0),(3,"三号药仓",1,0,0),(4,"四号药仓",1,0,0)]
    for b in boxes:
        cur.execute("INSERT OR IGNORE INTO medicine_box VALUES (?,?,?,?,?)", b)

    conn.commit()
    conn.close()

init_database()

#每日零点开锁+关锁次数清零
def reset_daily_count():
    today = str(date.today())
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT last_reset_date FROM system_config WHERE id=1")
    res = cur.fetchone()
    if not res or res["last_reset_date"] != today:
        cur.execute("UPDATE medicine_box SET open_count=0, lock_count=0")
        cur.execute("REPLACE INTO system_config (id, last_reset_date) VALUES (1, ?)", (today,))
        conn.commit()
    conn.close()

#查询接口
@router.get("/all", summary="查询全部药仓")
def get_all_box():
    conn = get_db_connection()
    boxes = conn.execute("SELECT * FROM medicine_box").fetchall()
    conn.close()
    return {"boxes": [dict(b) for b in boxes]}

@router.get("/{box_num}", summary="查询单个药仓")
def get_single_box(box_num: int):
    conn = get_db_connection()
    box = conn.execute("SELECT * FROM medicine_box WHERE box_num=?", (box_num,)).fetchone()
    conn.close()
    if not box:
        return {"msg": "药仓不存在"}
    return dict(box)

@router.get("/lock/{box_num}", summary="查询锁状态")
def get_lock_status(box_num: int):
    conn = get_db_connection()
    box = conn.execute("SELECT lock_status FROM medicine_box WHERE box_num=?", (box_num,)).fetchone()
    conn.close()
    if not box:
        return {"msg": "药仓不存在"}
    status = "已上锁" if box["lock_status"] == 1 else "已开锁"
    return {"box_num": box_num, "lock_status": status}

@router.get("/device/status/{device_id}", summary="查询设备状态")
def get_device_status(device_id: str):
    conn = get_db_connection()
    dev = conn.execute("SELECT * FROM device WHERE device_id=?", (device_id,)).fetchone()
    conn.close()
    if not dev:
        return {"msg": "设备不存在"}
    status = "在线" if dev["status"] == 1 else "离线"
    return {"device_id": device_id, "status": status}

#开锁（开锁计数+1）
@router.put("/open/{box_num}", summary="药仓开锁")
def open_box(box_num: int):
    reset_daily_count()
    conn = get_db_connection()
    cur = conn.cursor()
    box = cur.execute("SELECT * FROM medicine_box WHERE box_num=?", (box_num,)).fetchone()
    if not box:
        conn.close()
        return {"msg": "药仓不存在"}
    if box["lock_status"] == 0:
        conn.close()
        return {"msg": "已开锁"}

    cur.execute("UPDATE medicine_box SET lock_status=0, open_count=open_count+1 WHERE box_num=?", (box_num,))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO box_log (box_num, operate_type, operate_time) VALUES (?,?,?)", (box_num, "远程接口开锁", now))
    conn.commit()
    conn.close()
    return {"msg": f"{box_num}号药仓开锁成功"}

#上锁（关锁计数+1）
@router.put("/lock/{box_num}", summary="药仓上锁")
def lock_box(box_num: int):
    reset_daily_count()
    conn = get_db_connection()
    cur = conn.cursor()
    box = cur.execute("SELECT * FROM medicine_box WHERE box_num=?", (box_num,)).fetchone()
    if not box:
        conn.close()
        return {"msg": "药仓不存在"}
    if box["lock_status"] == 1:
        conn.close()
        return {"msg": "已上锁"}

    cur.execute("UPDATE medicine_box SET lock_status=1, lock_count=lock_count+1 WHERE box_num=?", (box_num,))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO box_log (box_num, operate_type, operate_time) VALUES (?,?,?)", (box_num, "远程接口上锁", now))
    conn.commit()
    conn.close()
    return {"msg": f"{box_num}号药仓上锁成功"}

#按日期筛选日志
@router.get("/log/date", summary="按日期范围查询日志")
def get_log_by_date(
    start_date: str = Query(..., description="开始日期"),
    end_date: str = Query(..., description="结束日期")
):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM box_log
        WHERE DATE(operate_time) BETWEEN ? AND ?
        ORDER BY id DESC
    ''', (start_date, end_date))
    logs = [dict(row) for row in cur.fetchall()]

    open_num = len([x for x in logs if "开锁" in x["operate_type"]])
    lock_num = len([x for x in logs if "上锁" in x["operate_type"]])

    conn.close()
    return {
        "开锁次数": open_num,
        "关锁次数": lock_num,
        "总操作": len(logs),
        "日志列表": logs
    }

#按药仓+日期查日志
@router.get("/log/box/date/{box_num}", summary="查询某个药仓指定日期的操作记录")
def get_box_log_by_date(
    box_num: int,
    log_date: str = Query(..., description="日期")
):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM box_log
        WHERE box_num=? AND DATE(operate_time)=?
        ORDER BY id DESC
    ''', (box_num, log_date))
    logs = [dict(row) for row in cur.fetchall()]

    open_num = len([x for x in logs if "开锁" in x["operate_type"]])
    lock_num = len([x for x in logs if "上锁" in x["operate_type"]])

    conn.close()
    return {
        "药仓": box_num,
        "日期": log_date,
        "开锁次数": open_num,
        "关锁次数": lock_num,
        "日志": logs
    }