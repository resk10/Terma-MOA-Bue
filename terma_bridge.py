import asyncio
import paho.mqtt.client as mqtt
from bleak import BleakClient
import time

# --- YOUR SPECIFIC CONFIGURATION ---
MQTT_BROKER = "192.168.xxx.xxx" # change to your mqtt broker
MQTT_USER = "mqtt_user" 
MQTT_PASS = "mqtt_password"
DEVICE_MAC = "xx:xx:xx:xx:xx:xx" # change to your thermostat.
ADAPTER = "hci1" # Change to hci0 if only one BT adapter is present

# UUIDs for Terma BlueLine
ELEM_TEMP_UUID = "D97352B2-D19E-11E2-9E96-0800200C9A66"
MODE_UUID      = "D97352B3-D19E-11E2-9E96-0800200C9A66"
PIN_UUID       = "D97352B4-D19E-11E2-9E96-0800200C9A66"

# Default PIN for Terma is usually 123456
PIN_CODE = "123456"

# MQTT Topics
TOPIC_MODE_SET = "terma/living_room/mode_set"
TOPIC_MODE_STATE = "terma/living_room/mode_state"
TOPIC_TEMP_SET = "terma/element/set"
TOPIC_TEMP_STATE = "terma/element/status"
TOPIC_ACTUAL_TEMP = "terma/element/actual_status"

async def authenticate(client):
    """Unlocks the device using the PIN code."""
    try:
        _ = client.services 
        pin_data = PIN_CODE.encode('ascii')
        await client.write_gatt_char(PIN_UUID, pin_data, response=True)
        await asyncio.sleep(0.5) 
    except Exception as e:
        print(f"❌ Auth failed: {e}")

async def get_and_publish_actual_state():
    """Reads the current real temperature and mode from the device via BLE."""
    print(f"🔄 Polling radiator for actual status...")
    try:
        async with BleakClient(DEVICE_MAC, timeout=20.0, bluez={"adapter": ADAPTER}) as client:
            await authenticate(client)
            m_raw = await client.read_gatt_char(MODE_UUID)
            t_raw = await client.read_gatt_char(ELEM_TEMP_UUID)
            
            # Little-Endian Parsing
            raw_temp_val = int.from_bytes(t_raw[0:2], byteorder='little')
            actual_temp = raw_temp_val / 10.0

            raw_mode = m_raw[0]
            mode_ha = "heat" if raw_mode in [33, 35, 5, 6, 38] else "off"

            mqtt_client.publish(TOPIC_MODE_STATE, mode_ha, retain=True)
            mqtt_client.publish(TOPIC_ACTUAL_TEMP, str(actual_temp), retain=True)
            print(f"📊 Actual Status: {mode_ha} | Sensor: {actual_temp}°C")
    except Exception as e:
        print(f"⚠️ Poll failed: {e}")

async def write_terma_mode(ha_payload):
    """Sets the power mode (heat/off)."""
    print(f"📡 Changing Power Mode -> {ha_payload}")
    try:
        async with BleakClient(DEVICE_MAC, timeout=30.0, bluez={"adapter": ADAPTER}) as client:
            await authenticate(client)
            # Map 'heat' -> 33 (Little Endian: 21 00 00 00)
            bt_val = 33 if ha_payload == "heat" else 0
            data = int(bt_val).to_bytes(4, byteorder='little')
            await client.write_gatt_char(MODE_UUID, data, response=True)
            mqtt_client.publish(TOPIC_MODE_STATE, ha_payload, retain=True)
            print(f"✅ Mode applied.")
    except Exception as e:
        print(f"❌ Mode BT Error: {e}")

async def write_terma_temp(target_c):
    """Sets the target 'wanted' temperature."""
    print(f"📡 Setting Wanted Temp -> {target_c}°C")
    try:
        async with BleakClient(DEVICE_MAC, timeout=30.0, bluez={"adapter": ADAPTER}) as client:
            await authenticate(client)
            target_val = int(target_c * 10)
            target_bytes = target_val.to_bytes(2, byteorder='little')
            # Structure: [00][00][TargetL][TargetH]
            data = bytearray([0x00, 0x00, target_bytes[0], target_bytes[1]])
            await client.write_gatt_char(ELEM_TEMP_UUID, data, response=True)
            mqtt_client.publish(TOPIC_TEMP_STATE, str(target_c), retain=True)
            print(f"✅ Target temperature sent.")
    except Exception as e:
        print(f"❌ Temp BT Error: {e}")

# --- MQTT SETUP ---
def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe([(TOPIC_MODE_SET, 0), (TOPIC_TEMP_SET, 0)])

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if msg.topic == TOPIC_MODE_SET:
            loop.run_until_complete(write_terma_mode(payload))
        elif msg.topic == TOPIC_TEMP_SET:
            loop.run_until_complete(write_terma_temp(float(payload)))
    finally:
        loop.close()

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# --- MAIN LOOP ---
async def main():
    print(f"🔗 Connecting to MQTT...")
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
    while True:
        await get_and_publish_actual_state()
        await asyncio.sleep(60) # Poll every minute

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        mqtt_client.loop_stop()