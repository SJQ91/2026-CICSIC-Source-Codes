import paho.mqtt.client as mqtt
from winotify import Notification, audio
import os
import sys
import winreg as reg


# ==========================================
# 1. Autonomous Startup Injection
# ==========================================
def enable_auto_startup():
    # Get the absolute path of this exact file
    script_path = os.path.abspath(sys.argv[0])

    # The name of our background task in Windows
    task_name = "ESP32_MQTT_Monitor"

    try:
        # Open the Windows Startup Registry Key
        registry_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, registry_path, 0, reg.KEY_ALL_ACCESS)

        try:
            # Check if our script is already in the registry
            reg.QueryValueEx(key, task_name)
        except OSError:
            # If it's missing, add it!
            # sys.executable ensures it uses pythonw.exe (invisible mode)
            run_command = f'"{sys.executable}" "{script_path}"'
            reg.SetValueEx(key, task_name, 0, reg.REG_SZ, run_command)

        reg.CloseKey(key)
    except Exception:
        # If anything fails (like strict antivirus blocking registry edits),
        # fail silently so the main program still runs.
        pass

# Run the startup check the moment the script starts
enable_auto_startup()

# ==========================================
# 2. The MQTT Notifier Logic
# ==========================================
BROKER_IP = "127.0.0.1"
PORT = 1883
TOPIC = "esp32/status"

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    if payload == "Offline":
        toast = Notification(app_id="ESP32 Monitor",
                             title="⚠️ ESP32 Disconnected",
                             msg="The device has dropped off the network unexpectedly!",
                             duration="short")  # <-- CHANGED FROM "long" TO "short"
        toast.set_audio(audio.Mail, loop=False)
        toast.show()

    elif payload == "Online":
        toast = Notification(app_id="ESP32 Monitor",
                             title="✅ ESP32 Connected",
                             msg="The device is online and streaming telemetry.",
                             duration="short")  # This one was already short
        toast.show()

# Setup the MQTT Client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Connect and wait forever
client.connect(BROKER_IP, PORT, 60)
client.loop_forever()