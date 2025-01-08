import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from inputs import get_gamepad
import math
import threading
import signal
import sys
import random

# Initialize I2C bus and PCA9685
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c)
pca.frequency = 50

# Define servo angle ranges with descriptions
SERVO_RANGES = {
    0: {"min": 110, "max": 155},   # Left Lower Lid (max=closed, min=open)
    1: {"min": 0, "max": 45},      # Left Upper Lid (min=closed, max=open)
    2: {"min": 50, "max": 130},    # Eye Horizontal (min=left, max=right)
    3: {"min": 0, "max": 90},      # Eye Vertical (min=down, max=up)
    4: {"min": 0, "max": 50},      # Right Upper Lid (max=closed, min=open)
    5: {"min": 110, "max": 155},   # Right Lower Lid (min=closed, max=open)
}

# Define mid positions for eyelids (halfway between min and max)
EYELID_MID = {
    0: SERVO_RANGES[0]["min"] + ((SERVO_RANGES[0]["min"] + SERVO_RANGES[0]["max"]) * .1),  # Left Lower
    1: SERVO_RANGES[1]["max"] -  ((SERVO_RANGES[1]["min"] + SERVO_RANGES[1]["max"]) /2),  # Left Upper
    4: SERVO_RANGES[4]["min"] + ((SERVO_RANGES[4]["min"] + SERVO_RANGES[4]["max"]) /2),  # Right Upper
    5: SERVO_RANGES[5]["max"] - ((SERVO_RANGES[5]["min"] + SERVO_RANGES[5]["max"]) * .1),  # Right Lower
}
# Create servo objects
servos = {}
for i in range(6):
    servos[i] = servo.Servo(pca.channels[i], min_pulse=500, max_pulse=2400)

# Global variables
eye_position = {"x": 90, "y": 40}  # Neutral position
is_blinking = False
running = True
use_mid_position = True
last_blink_time = time.time()
blink_interval = random.uniform(4, 9)  # Random time between blinks
VERTICAL_LID_MODIFIER = 0.8  # How much the upper lids follow vertical eye movement

def map_value(value, in_min, in_max, out_min, out_max):
    """Map a value from one range to another"""
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def move_servo(servo_num, angle):
    """Move specified servo to the given angle while respecting its limits"""
    if servo_num not in SERVO_RANGES:
        return False

    servo_range = SERVO_RANGES[servo_num]
    min_angle = min(servo_range["min"], servo_range["max"])
    max_angle = max(servo_range["min"], servo_range["max"])

    # Clamp angle to valid range
    clamped_angle = max(min_angle, min(angle, max_angle))

    servos[servo_num].angle = clamped_angle
    return True

def set_eyelids_position(position="open"):
    vertical_range = SERVO_RANGES[3]["max"] - SERVO_RANGES[3]["min"]
    current_position = eye_position["y"] - SERVO_RANGES[3]["min"]
    modifier = (current_position / vertical_range - 0.5) * VERTICAL_LID_MODIFIER
    """Set eyelid position: 'open', 'mid', or 'closed'"""
    if position == "closed":
        move_servo(0, SERVO_RANGES[0]["max"])  # Left Lower
        move_servo(1, SERVO_RANGES[1]["min"])  # Left Upper
        move_servo(4, SERVO_RANGES[4]["max"])  # Right Upper
        move_servo(5, SERVO_RANGES[5]["min"])  # Right Lower
    elif position == "mid":
        move_servo(0, EYELID_MID[0])  # Left Lower
        move_servo(5, EYELID_MID[5])  # Right Lower
        # Apply modifier to upper lids
        left_pos = EYELID_MID[1] + (SERVO_RANGES[1]["max"] - SERVO_RANGES[1]["min"]) * modifier
        right_pos = EYELID_MID[4] - (SERVO_RANGES[4]["max"] - SERVO_RANGES[4]["min"]) * modifier

        move_servo(1, left_pos)   # Left Upper
        move_servo(4, right_pos)  # Right Upper
    else:  # open
        move_servo(0, SERVO_RANGES[0]["min"])  # Left Lower
        move_servo(5, SERVO_RANGES[5]["max"])  # Right Lower
        # Apply modifier to upper lids
        left_pos = SERVO_RANGES[1]["max"] + (SERVO_RANGES[1]["max"] - SERVO_RANGES[1]["min"]) * modifier
        right_pos = SERVO_RANGES[4]["min"] - (SERVO_RANGES[4]["max"] - SERVO_RANGES[4]["min"]) * modifier

        move_servo(1, left_pos)   # Left Upper
        move_servo(4, right_pos)  # Right Upper
def update_upper_lids_vertical():
    """Update upper lid positions based on vertical eye position"""
    if is_blinking:
        return

    vertical_range = SERVO_RANGES[3]["max"] - SERVO_RANGES[3]["min"]
    current_position = eye_position["y"] - SERVO_RANGES[3]["min"]
    modifier = (current_position / vertical_range - 0.5) * VERTICAL_LID_MODIFIER

    # Calculate base positions based on current open/mid setting
    left_base = EYELID_MID[1] if use_mid_position else SERVO_RANGES[1]["max"]
    right_base = EYELID_MID[4] if use_mid_position else SERVO_RANGES[4]["min"]

    # Apply modifier to upper lids
    left_pos = left_base + (SERVO_RANGES[1]["max"] - SERVO_RANGES[1]["min"]) * modifier
    right_pos = right_base - (SERVO_RANGES[4]["max"] - SERVO_RANGES[4]["min"]) * modifier

    move_servo(1, left_pos)   # Left Upper
    move_servo(4, right_pos)  # Right Upper

def blink():
    """Perform a blink animation"""
    global is_blinking, last_blink_time
    if is_blinking:
        return

    is_blinking = True

    # Close eyes
    set_eyelids_position("closed")
    time.sleep(0.2)  # Hold blink

    # Return to previous state
    if use_mid_position:
        set_eyelids_position("mid")
    else:
        set_eyelids_position("open")

    update_upper_lids_vertical()  # Restore vertical position modifier

    is_blinking = False
    last_blink_time = time.time()
def auto_blink():
    """Handle automatic blinking"""
    global blink_interval
    while running:
        current_time = time.time()
        if current_time - last_blink_time > blink_interval:
            threading.Thread(target=blink).start()
            blink_interval = random.uniform(3, 8)  # Set next blink interval
        time.sleep(0.2)
def process_gamepad():
    """Process gamepad inputs"""
    global running, eye_position, use_mid_position

    while running:
        try:
            events = get_gamepad()
            for event in events:
                if event.code == "ABS_X":  # Left stick X-axis
                    x_angle = map_value(event.state, -32768, 32767,
                                      SERVO_RANGES[2]["min"], SERVO_RANGES[2]["max"])
                    eye_position["x"] = x_angle
                    move_servo(2, x_angle)

                elif event.code == "ABS_Y":  # Left stick Y-axis
                    y_angle = map_value(event.state, -32768, 32767,
                                      SERVO_RANGES[3]["max"], SERVO_RANGES[3]["min"])
                    eye_position["y"] = y_angle
                    move_servo(3, y_angle)
                    update_upper_lids_vertical()

                elif event.code == "BTN_THUMBL" and event.state == 1:  # Left stick press
                    threading.Thread(target=blink).start()
                elif event.code == "BTN_TR" and event.state == 1:  # Right trigger
                    use_mid_position = not use_mid_position
                    if use_mid_position:
                        set_eyelids_position("mid")
                    else:
                        set_eyelids_position("open")
                    update_upper_lids_vertical()

        except Exception as e:
            print(f"Gamepad error: {e}")
            time.sleep(0.1)

def cleanup():
    """Clean up and exit"""
    global running
    running = False
    print("\nExiting... Moving to neutral position")

    # Move eyes to center
    move_servo(2, (SERVO_RANGES[2]["min"] + SERVO_RANGES[2]["max"]) / 2)
    move_servo(3, (SERVO_RANGES[3]["min"] + SERVO_RANGES[3]["max"]) / 2)

    # Close eyes
    set_eyelids_position("closed")

    pca.deinit()
    sys.exit(0)

# Set up signal handler for clean exit
signal.signal(signal.SIGINT, lambda sig, frame: cleanup())

# Main program
if __name__ == "__main__":
    try:
        print("Starting gamepad control. Press Ctrl+C to exit.")
        print("Use left analog stick to control eye movement")
        print("Press left analog stick to manually blink")
        print("Press RT to toggle between full open and mid position")

        # Open eyes at start
        set_eyelids_position("mid")

        # Start auto-blink thread
        blink_thread = threading.Thread(target=auto_blink, daemon=True)
        blink_thread.start()

        # Start gamepad processing
        process_gamepad()

    except Exception as e:
        print(f"Error: {e}")
        cleanup()



