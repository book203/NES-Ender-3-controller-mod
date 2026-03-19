import network
import socket
import time
import os
from machine import Pin, reset
from neopixel import NeoPixel
import custom
from custom import OCTOPRINT_URL, API_KEY

# LED setup
LED_PIN = Pin(16, Pin.OUT)
NUM_PIXELS = 1
led = NeoPixel(LED_PIN, NUM_PIXELS)

def fade_red_step():
    cycle_time = time.ticks_ms() % 2000
    brightness = int(abs((cycle_time - 1000) / 1000.0 * 255))
    led[0] = (brightness, 0, 0)
    led.write()

# ---------------------------------------------------------
# CONFIG VALIDATION
# ---------------------------------------------------------

def config_is_valid():
    """Check if both Wi-Fi and OctoPrint config files exist and contain valid data."""
    try:
        # Wi-Fi config
        if "wifi_config.txt" not in os.listdir():
            print("wifi_config.txt missing.")
            return False

        with open("wifi_config.txt") as f:
            lines = f.readlines()
            if len(lines) < 2:
                print("wifi_config.txt malformed.")
                return False
            ssid = lines[0].split("=")[1].strip()
            password = lines[1].split("=")[1].strip()
            if ssid == "" or password == "":
                print("Wi-Fi config empty.")
                return False

        # OctoPrint config
        if "octoprint_config.txt" not in os.listdir():
            print("octoprint_config.txt missing.")
            return False

        with open("octoprint_config.txt") as f:
            lines = f.readlines()
            if len(lines) < 2:
                print("octoprint_config.txt malformed.")
                return False
            ip = lines[0].split("=")[1].strip()
            api = lines[1].split("=")[1].strip()
            if ip == "" or api == "":
                print("OctoPrint config empty.")
                return False

        return True

    except Exception as e:
        print("Config validation error:", e)
        return False


def wipe_config():
    """Delete both config files to force setup mode."""
    for file in ["wifi_config.txt", "octoprint_config.txt"]:
        try:
            os.remove(file)
            print(f"Deleted {file}")
        except:
            pass

# ---------------------------------------------------------
# WIFI FUNCTIONS
# ---------------------------------------------------------

def read_wifi_credentials():
    try:
        with open("wifi_config.txt", "r") as f:
            lines = f.readlines()
            ssid = lines[0].split("=")[1].strip()
            password = lines[1].split("=")[1].strip()
            print(f"Wi-Fi credentials loaded: SSID={ssid}, Password=******")
            return ssid, password
    except Exception:
        print("No Wi-Fi credentials found.")
        return None, None


def connect_to_wifi():
    ssid, password = read_wifi_credentials()
    if not ssid or not password:
        print("Invalid Wi-Fi config. Wiping and starting AP mode...")
        wipe_config()
        start_access_point()
        return False

    wlan = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)

    wlan.active(False)
    time.sleep(1)
    wlan.active(True)
    ap.active(False)

    print(f"Attempting to connect to Wi-Fi: SSID={ssid}")
    wlan.connect(ssid, password)

    timeout_ms = 7000
    start_time = time.ticks_ms()

    while not wlan.isconnected():
        fade_red_step()
        if time.ticks_diff(time.ticks_ms(), start_time) > timeout_ms:
            print("Wi-Fi timeout. Wiping config and starting AP mode...")
            wipe_config()
            wlan.active(False)
            start_access_point()
            return False
        time.sleep(1)

    print("Wi-Fi connected successfully!")
    print("IP Address:", wlan.ifconfig()[0])

    led[0] = (0, 255, 0)
    led.write()
    return True

# ---------------------------------------------------------
# ACCESS POINT MODE
# ---------------------------------------------------------

def start_access_point():
    print("Disabling STA mode...")
    ap = network.WLAN(network.AP_IF)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(1)

    print("Activating AP mode...")
    ap.active(True)
    ap.config(essid="NES_Controller_Setup", password="password123")

    print(f"AP Mode Active: {ap.active()}")
    print(f"AP IP Address: {ap.ifconfig()}")

    try:
        print("Setting up web server...")
        addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(5)
        print("Web server is running on 192.168.4.1...")

        while True:
            client, addr = s.accept()
            print(f"Client connected: {addr}")
            request = client.recv(1024).decode()

            if "POST" in request:
                try:
                    request_data = request.split("\r\n\r\n")[-1]
                    params = request_data.split("&")

                    ssid = ""
                    password = ""
                    octoprint_ip = ""
                    octoprint_api = ""

                    for param in params:
                        if param.startswith("ssid="):
                            ssid = param.split("=")[1]
                        elif param.startswith("password="):
                            password = param.split("=")[1]
                        elif param.startswith("octoprint_ip="):
                            octoprint_ip = param.split("=")[1]
                        elif param.startswith("octoprint_api="):
                            octoprint_api = param.split("=")[1]

                    def url_decode(data):
                        import re
                        return re.sub(r'%([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), data)

                    ssid = url_decode(ssid)
                    password = url_decode(password)
                    octoprint_ip = url_decode(octoprint_ip)
                    octoprint_api = url_decode(octoprint_api)

                    if not octoprint_ip.startswith("http://") and not octoprint_ip.startswith("https://"):
                        octoprint_ip = f"http://{octoprint_ip}"

                    print(f"Received Wi-Fi Credentials: SSID={ssid}, Password={password}")
                    print(f"Received OctoPrint Details: IP={octoprint_ip}, API Key={octoprint_api}")

                    with open("wifi_config.txt", "w") as f:
                        f.write(f"ssid={ssid}\n")
                        f.write(f"password={password}\n")

                    with open("octoprint_config.txt", "w") as f:
                        f.write(f"octoprint_ip={octoprint_ip}\n")
                        f.write(f"octoprint_api={octoprint_api}\n")

                    html_response = """<!DOCTYPE html>
                    <html>
                    <body>
                    <h1>Configuration Saved!</h1>
                    <p>Your Pico W will restart and apply the settings.</p>
                    </body>
                    </html>
                    """
                    client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html_response)
                    client.close()
                    reset()

                except Exception as e:
                    print(f"Error processing form submission: {e}")
                    client.send("HTTP/1.1 400 Bad Request\r\n\r\n")

            else:
                html_form = f"""<!DOCTYPE html>
                <html>
                <body>
                <h1>Pico W Configuration</h1>

                <h3>Current OctoPrint Settings</h3>
                <p><b>URL:</b> {OCTOPRINT_URL}</p>
                <p><b>API Key:</b> {API_KEY}</p>

                <hr>

                <form method="POST" action="/">
                  <label>Wi-Fi SSID:</label><input type="text" name="ssid"><br>
                  <label>Wi-Fi Password:</label><input type="password" name="password"><br>
                  <label>OctoPrint IP Address:</label><input type="text" name="octoprint_ip"><br>
                  <label>OctoPrint API Key:</label><input type="text" name="octoprint_api"><br>
                  <input type="submit" value="Submit">
                </form>
                </body>
                </html>
                """

                client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html_form)
                client.close()

    except Exception as e:
        print(f"Failed to start web server: {e}")

# ---------------------------------------------------------
# MAIN BOOT LOGIC
# ---------------------------------------------------------

def main():
    print("Boot.py script started...")

    # Validate config before anything else
    if not config_is_valid():
        print("Invalid or missing config. Wiping and entering AP mode...")
        wipe_config()
        start_access_point()
        return

    # Try Wi-Fi
    if connect_to_wifi():

        # Validate OctoPrint API
        if not custom.validate_octoprint_connection():
            print("Invalid OctoPrint settings. Wiping config and entering AP mode...")
            wipe_config()
            start_access_point()
            return

        print("Wi-Fi connected! Running main project...")
        while True:
            custom.main()
            time.sleep(1)
    else:
        print("Access Point mode active. Waiting for Wi-Fi credentials.")

main()