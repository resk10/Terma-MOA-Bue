# Terma BlueLine Bluetooth to MQTT Bridge

A Python-based bridge designed to integrate Terma BlueLine Bluetooth radiators (like the Terma Moa Blue) into Home Assistant via MQTT. This allows the radiator to appear as a standard `climate` (thermostat) entity.

## Features
- **Power Control**: Toggle between 'Off' and 'Heat' modes.
- **Dual Temperature Tracking**: Separates 'Wanted' (target) and 'Actual' (real-time sensor) temperatures.
- **Auto-Unlock**: Handles PIN authentication (default `123456`) automatically.
- **Endianness Correction**: Uses Little-Endian parsing to ensure accurate temperature reporting and command execution.

## Prerequisites
- **Hardware**: Linux host with Bluetooth (e.g., Raspberry Pi, Orange Pi Zero 3).
- **Python 3.9+**
- **Dependencies**: 
  - `pip install bleak paho-mqtt`

## 1. Bluetooth Preparation
Before running the script, your Linux host must trust the radiator:
1. Open terminal: `bluetoothctl`
2. Power on and scan: `power on`, `scan on`
3. Pair: `pair [YOUR_MAC_ADDRESS]` (Enter PIN `123456` if prompted)
4. **Important**: `trust [YOUR_MAC_ADDRESS]`
5. `exit`

## 2. Configuration

### Home Assistant (`configuration.yaml`)
```yaml
mqtt:
  climate:
    - name: "Towel Rail"
      unique_id: "terma_towel_rail"
      temperature_command_topic: "terma/element/set"
      temperature_state_topic: "terma/element/status"
      current_temperature_topic: "terma/element/actual_status"
      mode_command_topic: "terma/living_room/mode_set"
      mode_state_topic: "terma/living_room/mode_state"
      modes:
        - "off"
        - "heat"
      payload_on: "heat"
      payload_off: "off"
      min_temp: 30
      max_temp: 60
      temp_step: 1
      temperature_unit: "C"
      precision: 0.1
```
Python Bridge (terma_bridge.py)
Update the MQTT_BROKER, DEVICE_MAC, and ADAPTER (usually hci0 or hci1) variables at the top of the script.

## 3. Background Service Setup (Ubuntu/Debian)
To ensure the bridge starts on boot and restarts on failure, set it up as a systemd service:

Create the file: /etc/systemd/system/terma-bridge.service

Paste the following:

Ini, TOML
[Unit]
Description=Terma Bluetooth to MQTT Bridge
After=network.target bluetooth.target

[Service]
Type=simple
User=orangepi
WorkingDirectory=/home/orangepi
ExecStart=/usr/bin/python3 /home/orangepi/terma_bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
Enable and start:

Bash
sudo systemctl daemon-reload
sudo systemctl enable terma-bridge.service
sudo systemctl start terma-bridge.service
Troubleshooting
Device Busy: Ensure no other apps (like the mobile app) are connected to the radiator. BLE only supports one connection at a time.

Log check: Use journalctl -u terma-bridge.service -f to see real-time communication logs.

Bluetooth Reset: If the connection hangs, try sudo hciconfig [adapter] reset.
