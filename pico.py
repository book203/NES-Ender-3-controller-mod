import paho.mqtt.client as mqtt
import requests

# MQTT Configuration
BROKER = "Replace with Raspberry Pi IP address"  # Replace with Raspberry Pi 3B+'s IP address. Keep the ""
TOPIC = "3dprinter/commands"

# OctoPrint API Configuration
OCTOPRINT_API_KEY = "this can be found on the web interface of the OctoPrint" # Keep the ""
OCTOPRINT_URL = "http://Your Octoprint IP address/api"

# MQTT Callback
def on_message(client, userdata, message):
    command = message.payload.decode()
    print(f"Received: {command}")

    if command == "z_axis_up_20mm":
        requests.post(f"{OCTOPRINT_URL}/printer/command", json={"commands": ["G1 Z20"]}, headers={"X-Api-Key": OCTOPRINT_API_KEY})
    elif command == "z_axis_down_20mm":
        requests.post(f"{OCTOPRINT_URL}/printer/command", json={"commands": ["G1 Z-20"]}, headers={"X-Api-Key": OCTOPRINT_API_KEY})
    elif command == "extruder_left_20mm":
        # Add limit switch logic here
        requests.post(f"{OCTOPRINT_URL}/printer/command", json={"commands": ["G1 X-20"]}, headers={"X-Api-Key": OCTOPRINT_API_KEY})
    elif command == "extruder_right_20mm":
        requests.post(f"{OCTOPRINT_URL}/printer/command", json={"commands": ["G1 X20"]}, headers={"X-Api-Key": OCTOPRINT_API_KEY})
    elif command == "heat_bed_toggle":
        # Toggle bed heating logic
        pass
    elif command == "heat_extruder_toggle":
        # Toggle extruder heating logic
        pass
    elif command == "extrude_50mm":
        # Ensure extruder temperature logic
        pass
    elif command == "shutdown_octoprint":
        requests.post(f"{OCTOPRINT_URL}/system/command", json={"action": "shutdown"}, headers={"X-Api-Key": OCTOPRINT_API_KEY})

# MQTT Setup
client = mqtt.Client()
client.connect(BROKER)
client.subscribe(TOPIC)
client.on_message = on_message

client.loop_forever()
