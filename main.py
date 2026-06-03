from fastapi import FastAPI
from database import init_db # type: ignore
from models import BoxStatus, DeviceOnline # type: ignore
import paho.mqtt.client as mqtt
from api.box_api import router as box_router
#初始化数据库
init_db()

#初始化FastAPI
app = FastAPI(title="智能药盒后端-MQTT通信",version="1.0")
app.include_router(box_router)

#MQTT配置
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "smart_box_server"
MQTT_TOPIC = "smart_device/dev_001/report"

#后端收到设备消息触发
def on_message(client, userdata, msg):
    print(f"【后端收到设备消息】主题:{msg.topic} 内容:{msg.payload.decode()}")

def on_connect(client,userdata,flags,rc):
    if rc == 0:
        print("MQTT客户端连接成功")
        client.subscribe(MQTT_TOPIC) #订阅设备消息
    else:
        print("MQTT连接失败")

#MQTT客户端接入
mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID,
                         callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER,MQTT_PORT,60)
mqtt_client.loop_start() #持续监听设备消息

#基础测试接口
@app.get("/")
def root():
    return {"msg":"智能药盒后端启动完成,Swagger:/docs","device_id":"dev_001"}
#程序启动入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app",host="127.0.0.1",port=8000)