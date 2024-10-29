import network
import uasyncio as asyncio
from machine import Pin
import time
import json
from potentiometer import potentiometer
from oleddisplay import oleddisplay
from steppermotor import steppermotor
import logging

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
                # self.display.show_message("Connecting to Wi-Fi...")
                self.display.update_row(f"Connecting...", 1)
            await asyncio.sleep(1)

        # print(f"Connected to {self.ssid}")
        if self.display:
            # self.display.show_message(f"{self.ssid}")
            self.display.update_row(f"{self.ssid}", 1)
            # self.display.draw_wifi_symbol(5,10)
            ipaddress = self.get_ip()
            self.display.update_row(f"{ipaddress}", 3)
            print(f'RSSI:{self.wlan.status('rssi')}')

    def get_ip(self):
        return self.wlan.ifconfig()[0]


class RESTServer:
    def __init__(self, stepper, potentiometer, wifi_manager, display=None):
        self.display = display
        self.stepper = stepper
        self.potentiometer = potentiometer
        self.wlan = wifi_manager.wlan

    async def handle_request(self, reader, writer):
        request = await reader.read(1024)
        request = request.decode('utf-8')
        response_body = ""
        
        if "GET /status" in request:
            # Return status of the stepper motor
            response_body = json.dumps({"steps_remaining": self.stepper.steps_remaining, "direction": self.stepper.direction})
            if self.display:
                self.display.show_message(f"Steps: {self.stepper.steps_remaining}\nDir: {'CW' if self.stepper.direction else 'CCW'}")

        if "GET /home" in request:
            try:
                self.stepper.home()
            except Exception as e:
                response_body = json.dumps({"status": "error", "message": str(e)})
                
        elif "POST /move" in request:
            # Extract parameters from the request
            try:
                body = request.split("\r\n\r\n")[1]
                params = json.loads(body)

                steps = int(params['steps'])
                direction = int(params['direction'])
                speed = int(params['speed'])
                
                if self.display:
                    self.display.show_message(f"Moving: {steps}\nDir: {'CW' if direction else 'CCW'}")
                    
                response_body = json.dumps({"status": "ok", "steps": steps, "direction": direction, "speed": speed})
                self.stepper.move(steps, direction, speed)
            
            except Exception as e:
                response_body = json.dumps({"status": "error", "message": str(e)})

        # Format the HTTP response
        response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response_body
        
        # Send response and close the connection
        writer.write(response.encode('utf-8'))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def start_server(self):    
        # Start the server and run the event loop
        print('Setting up server')
        server = asyncio.start_server(self.handle_request, "0.0.0.0", 80)
        asyncio.create_task(server)
        # asyncio.create_task(blink_led())
        
        while True:
            # Add other tasks that you might need to do in the loop
            await asyncio.sleep(1)
            # print(f"Pot: {self.potentiometer.value}  Stepper:")
            RSSI = self.wlan.status('rssi')
            self.display.update_row(f"RSSI: {RSSI}", 2)
            self.display.update_row(f"Pot: {self.potentiometer.value}", 4)
            
        
# Main function
async def main():
    # Initialize components
    logging.warning('Logger online')
    oled_display = oleddisplay(scl_pin=5, sda_pin=4)
    wifi_manager = WiFiManager(SSID, PASSWORD, display=oled_display)
    pot = potentiometer(pot_pin=26)
    pot.start()
    stepper_motor = steppermotor(pot, oled_display, logging, dir_pin=14, step_pin=15, enable_pin=13)
    # stepper_motor.home()
    rest_server = RESTServer(stepper_motor, pot, wifi_manager, display=oled_display)

    # Connect to Wi-Fi
    await wifi_manager.connect()

    # Start the REST API server
    await rest_server.start_server()

# Run the main function using asyncio
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Server stopped")
