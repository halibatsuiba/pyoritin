import network
import ubluetooth
from machine import Pin, UART
import time

# Define the Bluetooth Serial UUID
BT_UUID = ubluetooth.UUID(0x180F)  # Replace with appropriate UUID

# Initialize Bluetooth
bluetooth = ubluetooth.BLE()
bluetooth.active(True)
uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))  # Use appropriate pins for TX and RX

# Initialize Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

def bt_handler(event, data):
    if event == ubluetooth.IRQ_CENTRAL_CONNECT:
        print('Bluetooth Central connected')
    elif event == ubluetooth.IRQ_CENTRAL_DISCONNECT:
        print('Bluetooth Central disconnected')
    elif event == ubluetooth.IRQ_GATTC_WRITE:
        print('Data received over Bluetooth')
        process_data(data)

def process_data(data):
    try:
        ssid, password = data.decode().strip().split(',')
        print(f'Configuring Wi-Fi with SSID: {ssid} and Password: {password}')
        wlan.connect(ssid, password)
        timeout = 10  # seconds
        start_time = time.time()
        while not wlan.isconnected() and (time.time() - start_time) < timeout:
            time.sleep(1)
        if wlan.isconnected():
            print('Connected to Wi-Fi:', wlan.ifconfig())
        else:
            print('Failed to connect to Wi-Fi')
    except Exception as e:
        print('Error:', e)

# Register the Bluetooth handler
bluetooth.gatts_register_services([(BT_UUID, 0x01)])  # Replace with appropriate service and characteristic UUIDs
bluetooth.irq(handler=bt_handler)

# Main loop
print("Waiting for Bluetooth connection...")
while True:
    if uart.any():
        data = uart.read()
        if data:
            process_data(data)
    time.sleep(1)
