import network
import socket
import uasyncio as asyncio
from machine import Pin, I2C, ADC, Timer
import ssd1306
import time
import json

# Wi-Fi credentials
SSID = 'Ohkola'
PASSWORD = 'P0rkkana'

# GPIO Pins
DIR_PIN = 14
STEP_PIN = 15
ENABLE_PIN = 13
POT_PIN = 26
LED_PIN = 25  # Optional LED indicator
OLED_SCL_PIN = 5
OLED_SDA_PIN = 4

# Stepper Motor Control Class
class StepperMotor:
    def __init__(self, dir_pin, step_pin, enable_pin=None, potentiometer_pin=POT_PIN):
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.enable_pin = Pin(enable_pin, Pin.OUT) if enable_pin else None
        self.potentiometer = ADC(Pin(potentiometer_pin))
        self.steps_remaining = 0
        self.direction = 1
        self.position = 0
        self.target_position = 0
        self.timer = Timer()

        if self.enable_pin:
            self.enable_pin.value(1)  # Disable the driver

    def _step_callback(self, timer):
        if self.steps_remaining > 0:
            self.step_pin.value(1)
            time.sleep_us(10)
            self.step_pin.value(0)
            self.steps_remaining -= 1
            self.position += self.direction
        else:
            self.timer.deinit()
            self.enable_pin.value(1)  # Disable the driver

    def move_to_position(self, target_position, speed_hz):
        steps_to_move = target_position - self.position
        self.direction = 1 if steps_to_move > 0 else 0
        self.steps_remaining = abs(steps_to_move)
        self.target_position = target_position
        self.dir_pin.value(self.direction)
        self.enable_pin.value(0)  # Enaable the driver
        self.timer.init(freq=speed_hz, mode=Timer.PERIODIC, callback=self._step_callback)

    def move_steps(self, steps, direction, speed_hz):
        self.direction = direction
        self.steps_remaining = steps
        self.dir_pin.value(self.direction)
        self.timer.init(freq=speed_hz, mode=Timer.PERIODIC, callback=self._step_callback)

    def home(self):
        pot_value = self.potentiometer.read_u16() >> 4  # 12-bit value (0-4095)
        if pot_value == 0:
            self.position = 0
            return True
        else:
            self.move_to_position(-self.position, 500)  # Move back to home
            return False

# OLED Display Class
class OLEDDisplay:
    def __init__(self, scl_pin, sda_pin, width=128, height=64):
        self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.oled = ssd1306.SSD1306_I2C(width, height, self.i2c)

    def show_message(self, message):
        self.oled.fill(0)
        for i, line in enumerate(message.split('\n')):
            self.oled.text(line, 0, i * 10)
        self.oled.show()

    def update_status(self, status, position):
        self.show_message(f"Status: {status}\nPos: {position}")

# Wi-Fi and Web Server Class
class WebServer:
    def __init__(self, ssid, password, stepper_motor, display, potentiometer):
        self.ssid = ssid
        self.password = password
        self.stepper_motor = stepper_motor
        self.display = display
        self.potentiometer = potentiometer
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

    async def connect(self):
        print("Connecting to Wi-Fi...")
        self.wlan.connect(self.ssid, self.password)
        while not self.wlan.isconnected():
            await asyncio.sleep(1)
        print(f"Connected, IP address: {self.wlan.ifconfig()[0]}")

    def start(self):
        ip = self.wlan.ifconfig()[0]
        addr = socket.getaddrinfo(ip, 80)[0][-1]

        s = socket.socket()
        s.bind(addr)
        s.listen(5)
        print(f"Listening on {ip}:80")

        while True:
            cl, addr = s.accept()
            print('Client connected from', addr)
            request = cl.recv(1024)
            request = request.decode('utf-8')
            print(request)

            if "/pot" in request:
                pot_value = self.potentiometer.read_u16() >> 4
                response = json.dumps({"potentiometer": pot_value})
                cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
                cl.send(response)
            elif "/move" in request:
                steps = int(self._get_param(request, "steps", 0))
                direction = int(self._get_param(request, "direction", 1))
                speed = int(self._get_param(request, "speed", 500))
                self.stepper_motor.move_steps(steps, direction, speed)
                self.display.update_status(f"Moving {'Fwd' if direction == 1 else 'Bwd'}", self.stepper_motor.position)
                response = json.dumps({"status": "moving", "steps": steps, "direction": direction})
                cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
                cl.send(response)
            else:
                response = self.webpage()
                cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                cl.send(response)
            cl.close()

    def _get_param(self, request, param, default):
        try:
            value = request.split(f"{param}=")[1].split(" ")[0].split("&")[0]
            return value
        except:
            return default

    def webpage(self):
        html = f"""<html>
                    <head>
                        <title>Konkanpyöritin</title>
                        <script>
                            function updatePot() {{
                                fetch('/pot')
                                .then(response => response.json())
                                .then(data => {{
                                    document.getElementById("potValue").innerText = data.potentiometer;
                                }});
                            }}
                            setInterval(updatePot, 1000);

                            function moveMotor(direction) {{
                                const steps = document.getElementById("steps").value;
                                const speed = document.getElementById("speed").value;
                                fetch(`/move?steps=${{steps}}&direction=${{direction}}&speed=${{speed}}`)
                                .then(response => response.json())
                                .then(data => {{
                                    console.log("Motor moved", data);
                                }});
                            }}
                        </script>
                    </head>
                    <body>
                        <h1>Pico W Stepper Motor Control</h1>
                        <p>Potentiometer Value: <span id="potValue">-</span></p>
                        <label for="steps">Steps:</label>
                        <input type="number" id="steps" name="steps">
                        <label for="speed">Speed (Hz):</label>
                        <input type="number" id="speed" name="speed">
                        <button onclick="moveMotor(1)">Move Forward</button>
                        <button onclick="moveMotor(0)">Move Backward</button>
                    </body>
                  </html>"""
        return html

# REST API Class
class RESTServer:
    def __init__(self, stepper_motor, display):
        self.stepper_motor = stepper_motor
        self.display = display

    async def handle_request(self, reader, writer):
        request = await reader.read(1024)
        request = request.decode('utf-8')
        print(request)

        response = ""

        if "POST /move" in request:
            try:
                content_length = int(request.split("Content-Length: ")[1].split("\r\n")[0])
                body = request.split("\r\n\r\n")[1]
                params = json.loads(body)
                steps = int(params['steps'])
                direction = int(params['direction'])
                speed = int(params['speed'])
                self.stepper_motor.move_steps(steps, direction, speed)
                self.display.update_status(f"Moving {'Fwd' if direction == 1 else 'Bwd'}", self.stepper_motor.position)
                response = json.dumps({"status": "ok", "steps": steps})
            except Exception as e:
                response = json.dumps({"status": "error", "message": str(e)})

        writer.write('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
        writer.write(response)
        await writer.drain()
        await writer.aclose()

    async def start_server(self):
        server = await asyncio.start_server(self.handle_request, "0.0.0.0", 8080)
        print("REST API server started on port 8080")
        await server.serve_forever()

# Main function
async def main():
    oled_display = OLEDDisplay(OLED_SCL_PIN, OLED_SDA_PIN)
    oled_display.show_message("Starting...")
    stepper_motor = StepperMotor(DIR_PIN, STEP_PIN, ENABLE_PIN)
    potentiometer = ADC(Pin(POT_PIN))
    web_server = WebServer(SSID, PASSWORD, stepper_motor, oled_display, potentiometer)
    rest_server = RESTServer(stepper_motor, oled_display)

    await web_server.connect()
    asyncio.create_task(rest_server.start_server())
    web_server.start()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Server stopped")
