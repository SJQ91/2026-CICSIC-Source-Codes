from fastapi import APIRouter, Query
import sqlite3
from datetime import datetime, date, time, timedelta


router = APIRouter(
    prefix="/box",
    tags=["药仓管理接口"]
)

import sqlite3

def get_db_connection():
    conn = sqlite3.connect("medicine_box.db", timeout=10.0)
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


    #服药计划表
    cur.execute('''
    CREATE TABLE IF NOT EXISTS medicine_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        box_num INTEGER NOT NULL,
        plan_type TEXT NOT NULL DEFAULT 'daily',
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        week_days TEXT,
        date_start TEXT,
        date_end TEXT,
        FOREIGN KEY (box_num) REFERENCES medicine_box(box_num)
    )
    ''')

    try:
        cur.execute("ALTER TABLE medicine_plan DROP COLUMN plan_hour;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE medicine_plan DROP COLUMN plan_minute;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE medicine_plan DROP COLUMN time_range;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE medicine_plan ADD COLUMN plan_type TEXT NOT NULL DEFAULT 'daily';")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE medicine_plan ADD COLUMN week_days TEXT;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE medicine_plan ADD COLUMN date_start TEXT;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE medicine_plan ADD COLUMN date_end TEXT;")
    except Exception:
        pass


    #服药记录表
    cur.execute('''
    CREATE TABLE IF NOT EXISTS medicine_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        box_num INTEGER,
        record_date TEXT,
        plan_time TEXT,
        actual_open_time TEXT,
        status TEXT, -- taken 已服药 / missed 漏服
        create_time TEXT
    )''')

    #开锁超时未关锁提醒记录表
    cur.execute('''
    CREATE TABLE IF NOT EXISTS overtime_alert (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        box_num INTEGER,
        open_time TEXT,
        alert_time TEXT,
        overtime_min INTEGER,
        status TEXT DEFAULT "unhandled", -- unhandled未处理 / handled已处理
        remark TEXT
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


#设置服药时间接口
from datetime import datetime

@router.post("/plan/save/{box_num}", summary="统一设置药仓服药时段，支持每日/一周中的某几天/日期区间（可设置个多时段）")
def save_plan_rule(
    box_num: int,
    plan_type: str = Query(..., description="生效类型：daily每日 / weekday指定星期 / date_range日期区间"),
    start_time: str = Query(..., description="服药起始时刻 HH:MM，例19:30"),
    end_time: str = Query(..., description="服药结束时刻 HH:MM，例20:20"),
    week_days: str | None = Query(None, description="仅weekday生效，多选逗号分隔，1=周一 7=周日，示例：1,3,5"),
    date_start: str | None = Query(None, description="仅date_range生效，起始日期 YYYY-MM-DD"),
    date_end: str | None = Query(None, description="仅date_range生效，结束日期 YYYY-MM-DD")
):

    try:
        datetime.strptime(start_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")
    except ValueError:
        return {"msg": "时间格式错误，时刻必须为 HH:MM 格式"}

  
    if plan_type == "daily":
      
        pass

    elif plan_type == "weekday":
        if not week_days:
            return {"msg": "选择「每周指定日期」时，必须选【weekday指定星期】"}
        try:
            week_nums = [int(w.strip()) for w in week_days.split(",") if w.strip()]
        except Exception:
            return {"msg": "星期参数格式错误，只能用数字逗号分隔"}
        for w in week_nums:
            if not 1 <= w <= 7:
                return {"msg": "取值范围只能是1~7（周一至周日）"}

    elif plan_type == "date_range":
        if not date_start or not date_end:
            return {"msg": "选择「自定义日期区间」时，必须填写起止日期"}
        try:
            datetime.strptime(date_start, "%Y-%m-%d")
            datetime.strptime(date_end, "%Y-%m-%d")
        except ValueError:
            return {"msg": "日期格式错误，必须为 YYYY-MM-DD"}

    else:
        return {"msg": "plan_type 只能填写 daily / weekday / date_range 三者之一"}

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
        INSERT INTO medicine_plan
        (box_num, plan_type, start_time, end_time, week_days, date_start, date_end)
        VALUES (?,?,?,?,?,?,?)
        ''', (box_num, plan_type, start_time, end_time, week_days, date_start, date_end))
        conn.commit()
        return {"msg": f"{box_num}号药仓成功新增一条服药时段"}
    except Exception as e:
        return {"msg": f"保存失败：{str(e)}"}
    finally:
        if conn is not None:
            conn.close()

#开锁（开锁计数+1）
@router.put("/open/{box_num}", summary="药仓开锁")
def open_box(box_num: int):
    reset_daily_count()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_date = now.date()
    today_week = now.isoweekday()
    today_str = today_date.strftime("%Y-%m-%d")
    curr_time = now.time()

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        box = cur.execute("SELECT * FROM medicine_box WHERE box_num=?", (box_num,)).fetchone()
        if not box:
            return {"msg": f"异常：药仓{box_num}不存在"}
        if box["lock_status"] == 0:
            return {"msg": f"异常：药仓{box_num}已开锁，不可重复开锁"}
        cur.execute("UPDATE medicine_box SET lock_status=0, open_count=open_count+1 WHERE box_num=?", (box_num,))
        cur.execute("INSERT INTO box_log (box_num, operate_type, operate_time) VALUES (?,?,?)",
                    (box_num, "远程开锁", now_str))

        rule_list = cur.execute('''
        SELECT id,plan_type,start_time,end_time,week_days,date_start,date_end
        FROM medicine_plan WHERE box_num=?
        ''', (box_num,)).fetchall()

        match_rule = None
        for r in rule_list:
            pt = r[1]
            st = r[2]
            et = r[3]
            wds = r[4]
            ds = r[5]
            de = r[6]

            if pt == "date_range":
                sdt = datetime.strptime(ds, "%Y-%m-%d").date()
                edt = datetime.strptime(de, "%Y-%m-%d").date()
                if sdt <= today_date <= edt:
                    match_rule = r
                    break
            elif pt == "weekday":
                w_list = [int(x) for x in wds.split(",")]
                if today_week in w_list:
                    match_rule = r
                    break
            elif pt == "daily":
                match_rule = r

        tip = ""
        status = None
        if match_rule:
            s_str = match_rule[2]
            e_str = match_rule[3]
            plan_s = datetime.strptime(s_str, "%H:%M").time()
            plan_e = datetime.strptime(e_str, "%H:%M").time()

            if curr_time < plan_s:
                status = "early"
                tip = f"过早服药，有效时段：{s_str} ~ {e_str}"
            elif curr_time > plan_e:
                status = "late"
                tip = f"过晚服药，有效时段：{s_str} ~ {e_str}"
            else:
                status = "taken"
                tip = f"正常按时服药，有效时段：{s_str} ~ {e_str}"

            exist = cur.execute('''
            SELECT 1 FROM medicine_record WHERE box_num=? AND record_date=?
            ''', (box_num, today_str)).fetchone()
            if not exist:
                cur.execute('''
                INSERT INTO medicine_record
                (box_num,record_date,plan_time,actual_open_time,status,create_time)
                VALUES (?,?,?,?,?,?)
                ''', (box_num, today_str, f"{s_str}~{e_str}", now_str, status, now_str))
        else:
            tip = "该药仓今日无匹配生效服药时段"

        conn.commit()
        return {"msg": f"药仓{box_num}开锁成功，{tip}"}
    except Exception as e:
        return {"msg": f"开锁异常：{str(e)}"}
    finally:
        if conn:
            conn.close()


#上锁（关锁计数+1）
@router.put("/lock/{box_num}", summary="药仓上锁")
def lock_box(box_num: int):
    reset_daily_count()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        box = cur.execute("SELECT * FROM medicine_box WHERE box_num=?", (box_num,)).fetchone()
        if not box:
            return {"msg": f"异常：药仓{box_num}不存在"}
        if box["lock_status"] == 1:
            return {"msg": f"异常：药仓{box_num}已经是上锁状态，不能重复上锁"}

        cur.execute("UPDATE medicine_box SET lock_status=1, lock_count=lock_count+1 WHERE box_num=?", (box_num,))
        cur.execute("INSERT INTO box_log (box_num, operate_type, operate_time) VALUES (?,?,?)", (box_num, "远程接口上锁", now))

        cur.execute('''
        UPDATE overtime_alert SET status="handled", remark="已手动关锁，异常解除"
        WHERE box_num=? AND status="unhandled"
        ''', (box_num,))

        conn.commit()
        return {"msg": f"药仓{box_num}上锁成功"}

    except Exception as e:
        return {"msg": f"上锁异常：{str(e)}"}
    finally:
        if conn is not None:
            conn.close()

#按日期筛选日志
@router.get("/log/date", summary="按日期范围查询日志")
def get_log_by_date(
    start_date: str = Query(..., description="开始日期"),
    end_date: str = Query(..., description="结束日期")
):
    try:
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
    except:
        return {"msg": "日志查询异常"}

#按药仓+日期查日志
@router.get("/log/box/date/{box_num}", summary="查询某个药仓指定日期的操作记录")
def get_box_log_by_date(
    box_num: int,
    log_date: str = Query(..., description="日期")
):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT * FROM box_log
            WHERE box_num=? AND DATE(operate_time)=?
            ORDER BY id DESC
        ''', (box_num, log_date))
        logs = [dict(row) for row in cur.fetchall()]
        open_num = len([x for x in logs if "开锁" in x["operate_type"]])
        lock_num = len([x for x in logs if "关锁" in x["operate_type"]])
        conn.close()
        return {
            "药仓": box_num,
            "日期": log_date,
            "开锁次数": open_num,
            "关锁次数": lock_num,
            "日志": logs
        }
    except:
        return {"msg": "日志查询异常"}
    

#查询全部/单个药仓已设置的服药时间段
from datetime import datetime
from fastapi import Query, Path

@router.get("/plan/{box_num}/list", summary="查询单个药仓所有已设置服药时段")
def get_single_box_plan_list(
    box_num: int = Path(..., description="药仓编号")
):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = '''
        SELECT id, box_num, plan_type, start_time, end_time, week_days, date_start, date_end
        FROM medicine_plan
        WHERE box_num = ?
        ORDER BY id DESC
        '''
        rows = cur.execute(sql, (box_num,)).fetchall()
        data = [dict(row) for row in rows]
        type_map = {
            "daily": "每日永久生效",
            "weekday": "每周指定日期",
            "date_range": "自定义日期区间"
        }
        for item in data:
            item["plan_type_cn"] = type_map.get(item["plan_type"], item["plan_type"])
        return {
            "code": 0,
            "msg": "查询成功",
            "data": data
        }
    except Exception as e:
        return {"code": -1, "msg": f"查询失败：{str(e)}"}
    finally:
        if conn is not None:
            conn.close()


#删除某一条时段
@router.delete("/plan/rule/{rule_id}", summary="删除某条服药时段设置")
def delete_single_plan_rule(
    rule_id: int = Path(..., description="时段id，查询列表里会返回id字段")
):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        exist = cur.execute("SELECT 1 FROM medicine_plan WHERE id=?", (rule_id,)).fetchone()
        if not exist:
            return {"code": -1, "msg": "该时段不存在，无需删除"}

        cur.execute("DELETE FROM medicine_plan WHERE id=?", (rule_id,))
        conn.commit()
        return {"code": 0, "msg": "该条时段配置删除成功"}
    except Exception as e:
        return {"code": -1, "msg": f"删除失败：{str(e)}"}
    finally:
        if conn is not None:
            conn.close()



#查询所有药仓异常服用日志（早服/晚服/漏服）
from datetime import date

@router.get("/record/abnormal/list", summary="查询所有药仓异常服用日志（早服/晚服/漏服）")
def get_abnormal_medicine_record(
    box_num: int | None = Query(None, description="指定药仓编号，不输入则查询全部药仓"),
    date_start: str | None = Query(None, description="起始日期 YYYY-MM-DD"),
    date_end: str | None = Query(None, description="结束日期 YYYY-MM-DD")
):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        #异常状态：早服、晚服、漏服
        abnormal_status = ("early", "late", "missed")
        base_sql = '''
        SELECT
            r.id,
            r.box_num,
            b.box_name,
            r.record_date,
            r.plan_time,
            r.actual_open_time,
            r.status,
            r.create_time
        FROM medicine_record r
        LEFT JOIN medicine_box b ON r.box_num = b.box_num
        WHERE r.status IN (?,?,?)
        '''
        params = list(abnormal_status)
        if box_num is not None:
            base_sql += " AND r.box_num = ?"
            params.append(box_num)
        if date_start:
            base_sql += " AND r.record_date >= ?"
            params.append(date_start)
        if date_end:
            base_sql += " AND r.record_date <= ?"
            params.append(date_end)
        base_sql += " ORDER BY r.record_date DESC, r.id DESC"

        res = cur.execute(base_sql, params).fetchall()
        data = [dict(row) for row in res]
        status_map = {
            "early": "过早服药",
            "late": "过晚服药",
            "missed": "漏服",
            "taken": "正常服药"
        }
        for item in data:
            item["status_cn"] = status_map.get(item["status"], item["status"])

        return {
            "code": 0,
            "msg": "success",
            "data": data
        }
    except Exception as e:
        return {"code": -1, "msg": f"查询异常日志失败：{str(e)}"}
    finally:
        if conn is not None:
            conn.close()