from machine import Pin
import time
import network
import urequests
from neopixel import NeoPixel

# ---------------------------------------------------------------------------
# Load OctoPrint configuration from file (no defaults)
# ---------------------------------------------------------------------------

def load_octoprint_config():
    try:
        with open("octoprint_config.txt", "r") as f:
            lines = f.readlines()
            url = lines[0].split("=")[1].strip()
            key = lines[1].split("=")[1].strip()
            print(f"Loaded OctoPrint config: URL={url}, API Key=******")
            return url, key
    except Exception:
        print("No octoprint_config.txt found. OctoPrint settings are empty.")
        return "", ""

OCTOPRINT_URL, API_KEY = load_octoprint_config()

# ---------------------------------------------------------------------------
# LED Setup
# ---------------------------------------------------------------------------

LED_PIN = Pin(16, Pin.OUT)
NUM_PIXELS = 1
led = NeoPixel(LED_PIN, NUM_PIXELS)

BRIGHTNESS_SCALE = 0.05

def scale_color(r, g, b):
    return (int(r * BRIGHTNESS_SCALE), int(g * BRIGHTNESS_SCALE), int(b * BRIGHTNESS_SCALE))

def fade_green_blue_step():
    cycle_time = time.ticks_ms() % 4000
    if cycle_time < 2000:
        brightness = int((cycle_time / 2000.0) * 255)
        led[0] = scale_color(0, 255 - brightness, brightness)
    else:
        brightness = int(((cycle_time - 2000) / 2000.0) * 255)
        led[0] = scale_color(0, brightness, 255 - brightness)
    led.write()

# ---------------------------------------------------------------------------
# Button Setup (FAST + CORRECT Z DIRECTION)
# ---------------------------------------------------------------------------

buttons = {
    5: {"name": "Z-axis up",   "gcode": "G1 Z5 F6000"},   # FIXED: Z up = negative
    2: {"name": "Z-axis down", "gcode": "G1 Z-5 F6000"},    # FIXED: Z down = positive

    4: {"name": "Extruder left",  "gcode": "G1 X-20 F6000"},
    3: {"name": "Extruder right", "gcode": "G1 X20 F6000"},

    7: {"name": "Toggle bed heat", "toggle": True, "state": False},
    6: {"name": "Toggle extruder heat", "toggle": True, "state": False},
    0: {"name": "Extrude 50mm", "gcode": "G1 E50 F100"},
    1: {"name": "Shutdown OctoPrint", "gcode": None},
}

for pin_num in buttons:
    buttons[pin_num]["pin"] = Pin(pin_num, Pin.IN, Pin.PULL_UP)

# ---------------------------------------------------------------------------
# OctoPrint Communication
# ---------------------------------------------------------------------------

def check_printer_state():
    if not OCTOPRINT_URL:
        return ""
    try:
        response = urequests.get(f"{OCTOPRINT_URL}/api/printer")
        data = response.json()
        response.close()
        return data.get("state", {}).get("text", "")
    except:
        return ""

def send_gcode(gcode):
    if not OCTOPRINT_URL or not API_KEY:
        print("⚠ OctoPrint URL or API Key not set.")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"commands": [gcode]}

    try:
        response = urequests.post(
            f"{OCTOPRINT_URL}/api/printer/command",
            json=payload,
            headers=headers,
            timeout=5
        )
        response.close()
    except Exception as e:
        print(f"⚠ Error sending G-code: {e}")

# ---------------------------------------------------------------------------
# Button Handling (FAST: ALL MOVES USE RELATIVE MODE)
# ---------------------------------------------------------------------------

def handle_button(pin):
    for pin_num, action in buttons.items():
        if action["pin"] == pin:

            # Heater toggles
            if pin_num in [7, 6]:
                toggle_heater(pin_num)
                return

            # Shutdown
            if pin_num == 1:
                shutdown_octoprint()
                return

            # FAST movement: relative mode only
            send_gcode("G91")          # enter relative mode
            send_gcode(action["gcode"])
            send_gcode("G90")          # return to absolute mode

            return

def button_pressed(pin):
    time.sleep(0.01)
    handle_button(pin)

def toggle_heater(pin_num):
    if not OCTOPRINT_URL or not API_KEY:
        print("⚠ OctoPrint settings not set.")
        return

    action = buttons[pin_num]
    action["state"] = not action["state"]

    if pin_num == 7:
        gcode = f"M140 S{60 if action['state'] else 0}"
    else:
        gcode = f"M104 S{220 if action['state'] else 0}"

    send_gcode(gcode)

def shutdown_octoprint():
    if not OCTOPRINT_URL or not API_KEY:
        print("⚠ OctoPrint URL or API Key not set.")
        return

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    try:
        response = urequests.post(
            f"{OCTOPRINT_URL}/api/system/commands/core/shutdown",
            headers=headers,
            timeout=5
        )
        response.close()
    except:
        pass

# Attach interrupts
for pin_num, action in buttons.items():
    action["pin"].irq(trigger=Pin.IRQ_FALLING, handler=button_pressed)

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

def main():
    print("Custom.py script started...")
    counter = 0

    while True:
        fade_green_blue_step()
        if counter % 5 == 0:
            print("Custom.py is running...")
        counter += 1
        time.sleep(0.5)