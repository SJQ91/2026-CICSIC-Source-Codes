from fastapi import APIRouter, HTTPException
import sqlite3
from typing import List, Dict, Optional

router = APIRouter(prefix="/box", tags=["药仓查询接口"])

def get_db_connection():
    conn = sqlite3.connect("medicine_box.db")
    conn.row_factory = sqlite3.Row
    return conn

# 1. 查询所有药仓状态
@router.get("/all")
def get_all_box_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicine_box")
    boxes = cursor.fetchall()
    conn.close()

    result = []
    for box in boxes:
        result.append({
            "id": box["id"],
            "device_id": box["device_id"],
            "box_num": box["box_num"],
            "status": box["status"],
            "lock_status": box["lock_status"],
            "open_count": box["open_count"]
        })
    return {"code": 200, "msg": "查询成功", "data": result}

# 2. 查询单个药仓状态（按药仓编号）
@router.get("/{box_num}")
def get_single_box(box_num: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicine_box WHERE box_num = ?", (box_num,))
    box = cursor.fetchone()
    conn.close()

    if not box:
        raise HTTPException(status_code=404, detail="药仓不存在")

    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "id": box["id"],
            "device_id": box["device_id"],
            "box_num": box["box_num"],
            "status": box["status"],
            "lock_status": box["lock_status"],
            "open_count": box["open_count"]
        }
    }

# 3. 查询药仓锁状态
@router.get("/lock/{box_num}")
def get_box_lock_status(box_num: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT lock_status FROM medicine_box WHERE box_num = ?", (box_num,))
    box = cursor.fetchone()
    conn.close()

    if not box:
        raise HTTPException(status_code=404, detail="药仓不存在")

    return {
        "code": 200,
        "msg": "查询成功",
        "box_num": box_num,
        "lock_status": box["lock_status"]
    }

# 4. 查询设备在线状态
@router.get("/device/status/{device_id}")
def get_device_online_status(device_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT online_status FROM device WHERE device_id = ?", (device_id,))
    device = cursor.fetchone()
    conn.close()

    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    return {
        "code": 200,
        "msg": "查询成功",
        "device_id": device_id,
        "online_status": device["online_status"]
    }