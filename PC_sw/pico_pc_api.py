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
            print(f"Steps Remaining: {status['steps_remaining']}")
            print(f"Direction: {'CW' if status['direction'] == 1 else 'CCW'}")
        else:
            print(f"Failed to get status: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return int(status['steps_remaining'])

def homing():
    """
    Drive motor to home position.
    """
    try:
        response = requests.get(f"{BASE_URL}/home")
        if response.status_code == 200:
            status = response.json()
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
        response = requests.post(f"{BASE_URL}/move", data=json.dumps(payload), headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result["status"] == "ok":
                print(f"Motor is moving: {steps} steps {'CW' if direction == 1 else 'CCW'} at {speed} Hz")
            else:
                print(f"Failed to move motor: {result['message']}")
        else:
            print(f"Failed to send move command: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Example usage of the API
    get_motor_status()  # Get current motor status
    
    # Move the motor 200 steps clockwise at 500 Hz
    # ove_motor(steps=200, direction=0, speed=200)

    homing()

    # Wait and then check status again
    get_motor_status()

