import requests
import json
import time

# Define the IP address of the Raspberry Pi Pico W
PICO_IP = "192.168.100.41"  # Replace with the actual IP address of your Pico W
BASE_URL = f"http://{PICO_IP}"

def get_motor_status():
    """
    Retrieve the current status of the stepper motor.
    """
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            status = response.json()
            print(f'**** Status ****')
            print(f"Steps Remaining: {status['steps_remaining']}")
            print(f"Direction: {'CW' if status['direction'] == 1 else 'CCW'}")
        else:
            print(f"Failed to get status: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return int(status['steps_remaining'])

def home():
    """
    Drive motor to home position.
    """
    payload = {
    }
    headers = {'Content-Type': 'application/json'}    
    try:
        response = requests.get(f"{BASE_URL}/home", json=payload, headers=headers)
        if response.status_code == 200:
            status = response.json()
            print('**** homing ****')
            print(f"{status['status']}")
    except Exception as e:
        print(f"Error: {e}")
  

def move_motor(steps, direction, speed):
    """
    Move the stepper motor.
    :param steps: Number of steps to move
    :param direction: 1 for clockwise, 0 for counterclockwise
    :param speed: Speed in Hz
    """
    payload = {
        "steps": steps,
        "direction": direction,
        "speed": speed
    }
    headers = {'Content-Type': 'application/json'}
    try:
        print('**** move ****')
        response = requests.post(f"{BASE_URL}/move", json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result["status"] == "ok":
                # print(f"Motor is moving: {steps} steps {'CW' if direction == 1 else 'CCW'} at {speed} Hz")
                print(result)
            else:
                print(f"Failed to move motor: {result}")
        else:
            print(f"Failed to send move command: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Example usage of the API
    get_motor_status()  # Get current motor status
    
    # Homing
    home()

    # Move the motor 200 steps clockwise at 500 Hz
    # move_motor(steps=200, direction=0, speed=200)

    # Wait and then check status again
    # get_motor_status()

