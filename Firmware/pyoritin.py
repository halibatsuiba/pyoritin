import network
import uasyncio as asyncio
from machine import Pin, I2C, Timer, ADC
import ssd1306
import time
import json

# Wi-Fi credentials
SSID = 'Ohkola'
PASSWORD = 'P0rkkana'

class WiFiManager:
    def __init__(self, ssid, password, display=None):
        self.ssid = ssid
        self.password = password
        self.display = display
        self.wlan = network.WLAN(network.STA_IF)
    
    async def connect(self):
        self.wlan.active(True)
        self.wlan.connect(self.ssid, self.password)
        
        while not self.wlan.isconnected():
            print("Connecting to Wi-Fi...")
            if self.display:
                self.display.show_message("Connecting to Wi-Fi...")
            await asyncio.sleep(1)

        print(f"Connected to {self.ssid}")
        if self.display:
            self.display.show_message(f"{self.ssid}")

    def get_ip(self):
        return self.wlan.ifconfig()[0]

class Potentiometer:
    def __init__(self, pot_pin=26):
        self.potentiometer = ADC(Pin(pot_pin))
        self.value = 0
        self.timer = Timer()
        
    def _pot_callback(self, timer):
        self.value = self.potentiometer.read_u16() >> 4  # 12-bit value (0-4095)
        
    def start(self):
        self.timer.init(freq=10, mode=Timer.PERIODIC, callback=self._pot_callback)
        
    def stop(self):
        self.timer.deinit()

class StepperMotor:
    def __init__(self, potentiometer, dir_pin, step_pin, enable_pin ):
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.enable_pin = Pin(enable_pin, Pin.OUT)
        self.potentiometer = potentiometer
        self.steps_remaining = 0
        self.direction = 1
        self.timer = Timer()

        if self.enable_pin:
            self.enable_pin.value(1)  # Disable the driver

    def _step_callback(self, timer):
        if self.steps_remaining > 0:
            self.step_pin.value(1)
            # time.sleep_us(10)
            self.step_pin.value(0)
            self.steps_remaining -= 1
        else:
            self.enable_pin.value(1)  # Disable the driver
            self.timer.deinit()

    def move(self, steps, direction, speed_hz):
        self.enable_pin.value(0)  # Enable the driver
        self.direction = direction
        self.steps_remaining = steps
        self.dir_pin.value(self.direction)
        self.timer.init(freq=speed_hz, mode=Timer.PERIODIC, callback=self._step_callback)
        
    def home(self):
        if self.potentiometer.value == 0:
            self.position = 0
            return True
        else:
            self.move_to_position(-self.position, 200)  # Move back to home
            return False        

class OLEDDisplay:
    def __init__(self, scl_pin, sda_pin, width=128, height=64):
        self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.oled = ssd1306.SSD1306_I2C(width, height, self.i2c)

    def show_message(self, message):
        self.oled.fill(0)
        for i, line in enumerate(message.split('\n')):
            self.oled.text(line, 0, i * 10)
        self.oled.show()

class RESTServer:
    def __init__(self, stepper, potentiometer, display=None):
        self.display = display
        self.stepper = stepper
        self.potentiometer = potentiometer

    async def handle_request(self, reader, writer):
        request = await reader.read(1024)
        request = request.decode('utf-8')
        print(request)

        response = ""

        if "GET /status" in request:
            # Return status of the stepper motor
            response = json.dumps({"steps_remaining": self.stepper.steps_remaining, "direction": self.stepper.direction})
            if self.display:
                self.display.show_message(f"Steps: {self.stepper.steps_remaining}\nDir: {'CW' if self.stepper.direction else 'CCW'}")

        elif "POST /move" in request:
            # Extract parameters from the request
            try:
                content_length = int(request.split("Content-Length: ")[1].split("\r\n")[0])
                body = request.split("\r\n\r\n")[1]
                params = json.loads(body)
                steps = int(params['steps'])
                direction = int(params['direction'])
                speed = int(params['speed'])
                self.stepper.move(steps, direction, speed)
                response = json.dumps({"status": "ok", "steps": steps, "direction": direction, "speed": speed})
                if self.display:
                    self.display.show_message(f"Moving: {steps}\nDir: {'CW' if direction else 'CCW'}")
            except Exception as e:
                response = json.dumps({"status": "error", "message": str(e)})

        elif "POST /home" in request:
            homed = self.stepper.home()
            if homed:
                response = json.dumps({"status": "ok", "position": 0})
            else:
                response = json.dumps({"status": "moving", "position": self.stepper.position})
                
        # Send HTTP response
        writer.write('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
        writer.write(response)
        await writer.drain()
        await writer.aclose()

    async def start_server(self):    
        # Start the server and run the event loop
        print('Setting up server')
        server = asyncio.start_server(self.handle_request, "0.0.0.0", 80)
        asyncio.create_task(server)
        # asyncio.create_task(blink_led())
        
        while True:
            # Add other tasks that you might need to do in the loop
            await asyncio.sleep(5)
            # print(f"Pot: {self.potentiometer.value}  Stepper:")
        
# Main function
async def main():
    # Initialize components
    oled_display = OLEDDisplay(scl_pin=5, sda_pin=4)
    wifi_manager = WiFiManager(SSID, PASSWORD, display=oled_display)
    stepper_motor = StepperMotor(potentiometer, dir_pin=14, step_pin=15, enable_pin=13)
    potentiometer = Potentiometer(pot_pin=26)
    potentiometer.start()
    rest_server = RESTServer(stepper_motor, potentiometer, display=oled_display)

    # Connect to Wi-Fi
    await wifi_manager.connect()

    # Start the REST API server
    await rest_server.start_server()

# Run the main function using asyncio
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Server stopped")
