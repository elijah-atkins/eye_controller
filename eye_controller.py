#!/usr/bin/env python3
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from inputs import get_gamepad
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
    0: {"min": 145, "max": 155},   # Left Lower Lid (max=closed, min=open)
    1: {"min": 0, "max": 80},      # Left Upper Lid (min=closed, max=open)
    2: {"min": 50, "max": 130},    # Eye Horizontal (min=left, max=right)
    3: {"min": 0, "max": 90},      # Eye Vertical (min=down, max=up)
    4: {"min": 0, "max": 80},      # Right Upper Lid (max=closed, min=open)
    5: {"min": 145, "max": 155},   # Right Lower Lid (min=closed, max=open)
}

# Define mid positions for eyelids
EYELID_MID = {
    0: SERVO_RANGES[0]["min"] + ((SERVO_RANGES[0]["max"] - SERVO_RANGES[0]["min"]) * 0.1),
    1: SERVO_RANGES[1]["max"] - ((SERVO_RANGES[1]["max"] - SERVO_RANGES[1]["min"]) * 0.5),
    4: SERVO_RANGES[4]["min"] + ((SERVO_RANGES[4]["max"] - SERVO_RANGES[4]["min"]) * 0.5),
    5: SERVO_RANGES[5]["max"] - ((SERVO_RANGES[5]["max"] - SERVO_RANGES[5]["min"]) * 0.1),
}

# Create servo objects
servos = {i: servo.Servo(pca.channels[i], min_pulse=500, max_pulse=2400) for i in range(6)}

# Global state
class State:
    def __init__(self):
        self.eye_position = {"x": 90, "y": 40}  # Neutral position
        self.is_blinking = False
        self.running = True
        self.use_mid_position = True
        self.last_blink_time = time.time()
        self.blink_interval = random.uniform(4, 9)
        self.left_trigger_value = 0  # Store trigger values (0 to 255)
        self.right_trigger_value = 0
        self.left_upper_lid_position = EYELID_MID[1] # Store lid positions
        self.right_upper_lid_position = EYELID_MID[4]

state = State()

VERTICAL_LID_MODIFIER = 0.8

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
    clamped_angle = max(min_angle, min(angle, max_angle))
    
    servos[servo_num].angle = clamped_angle
    return True

def update_eyelid_position(side="left", trigger_value=0):
    """Update eyelid position based on trigger value (0-255)"""
    if side == "left":
        if trigger_value < 10:  # Return to stored position when released
            move_servo(1, state.left_upper_lid_position)
            move_servo(0, SERVO_RANGES[0]["min"])
        else:
            upper_angle = map_value(trigger_value, 0, 255, 
                                  SERVO_RANGES[1]["max"], SERVO_RANGES[1]["min"])
            lower_angle = map_value(trigger_value, 0, 255, 
                                  SERVO_RANGES[0]["min"], SERVO_RANGES[0]["max"])
            move_servo(1, upper_angle)
            move_servo(0, lower_angle)
    else:
        if trigger_value < 10:  # Return to stored position when released
            move_servo(4, state.right_upper_lid_position)
            move_servo(5, SERVO_RANGES[5]["max"])
        else:
            upper_angle = map_value(trigger_value, 0, 255, 
                                  SERVO_RANGES[4]["min"], SERVO_RANGES[4]["max"])
            lower_angle = map_value(trigger_value, 0, 255, 
                                  SERVO_RANGES[5]["max"], SERVO_RANGES[5]["min"])
            move_servo(4, upper_angle)
            move_servo(5, lower_angle)

def set_eyelids_position(position="open"):
    """Set both eyelids position: 'open', 'mid', or 'closed'"""
    if position == "closed":
        move_servo(0, SERVO_RANGES[0]["max"])  # Left Lower
        move_servo(1, SERVO_RANGES[1]["min"])  # Left Upper
        move_servo(4, SERVO_RANGES[4]["max"])  # Right Upper
        move_servo(5, SERVO_RANGES[5]["min"])  # Right Lower
    elif position == "mid":
        move_servo(0, EYELID_MID[0])  # Left Lower
        move_servo(1, EYELID_MID[1])  # Left Upper
        move_servo(4, EYELID_MID[4])  # Right Upper
        move_servo(5, EYELID_MID[5])  # Right Lower
    else:  # open
        move_servo(0, SERVO_RANGES[0]["min"])  # Left Lower
        move_servo(1, SERVO_RANGES[1]["max"])  # Left Upper
        move_servo(4, SERVO_RANGES[4]["min"])  # Right Upper
        move_servo(5, SERVO_RANGES[5]["max"])  # Right Lower

def update_upper_lids_vertical():
    """Update upper lid positions based on vertical eye position"""
    if state.is_blinking:
        return

    vertical_range = SERVO_RANGES[3]["max"] - SERVO_RANGES[3]["min"]
    current_position = state.eye_position["y"] - SERVO_RANGES[3]["min"]
    modifier = (current_position / vertical_range - 0.5) * VERTICAL_LID_MODIFIER

    if state.left_trigger_value < 10:
        base = EYELID_MID[1] if state.use_mid_position else SERVO_RANGES[1]["max"]
        state.left_upper_lid_position = base + (SERVO_RANGES[1]["max"] - SERVO_RANGES[1]["min"]) * modifier
        move_servo(1, state.left_upper_lid_position)

    if state.right_trigger_value < 10:
        base = EYELID_MID[4] if state.use_mid_position else SERVO_RANGES[4]["min"]
        state.right_upper_lid_position = base - (SERVO_RANGES[4]["max"] - SERVO_RANGES[4]["min"]) * modifier
        move_servo(4, state.right_upper_lid_position)

def blink():
    """Perform a blink animation"""
    if state.is_blinking or state.left_trigger_value > 10 or state.right_trigger_value > 10:
        return

    state.is_blinking = True
    
    set_eyelids_position("closed")
    time.sleep(0.2)

    if state.use_mid_position:
        set_eyelids_position("mid")
    else:
        set_eyelids_position("open")

    update_upper_lids_vertical()
    
    state.is_blinking = False
    state.last_blink_time = time.time()

def auto_blink():
    """Handle automatic blinking"""
    while state.running:
        current_time = time.time()
        if current_time - state.last_blink_time > state.blink_interval:
            threading.Thread(target=blink).start()
            state.blink_interval = random.uniform(3, 8)
        time.sleep(0.2)

def process_gamepad():
    """Process gamepad inputs"""
    while state.running:
        try:
            events = get_gamepad()
            for event in events:
                if event.code == "BTN_SELECT" and event.state == 1:  # Back button
                    cleanup()
                    
                elif event.code == "ABS_Z":  # Left trigger (Button 11)
                    state.left_trigger_value = event.state
                    update_eyelid_position("left", event.state)
                    
                elif event.code == "ABS_RZ":  # Right trigger (Button 12)
                    state.right_trigger_value = event.state
                    update_eyelid_position("right", event.state)
                    
                elif event.code == "BTN_TR" and event.state == 1:  # RB button
                    state.use_mid_position = not state.use_mid_position
                    if not state.is_blinking:
                        if state.use_mid_position:
                            set_eyelids_position("mid")
                        else:
                            set_eyelids_position("open")
                        update_upper_lids_vertical()
                    
                elif event.code == "ABS_X":  # Left stick X-axis
                    x_angle = map_value(event.state, -32768, 32767,
                                      SERVO_RANGES[2]["min"], SERVO_RANGES[2]["max"])
                    state.eye_position["x"] = x_angle
                    move_servo(2, x_angle)
                    
                elif event.code == "ABS_Y":  # Left stick Y-axis
                    y_angle = map_value(event.state, -32768, 32767,
                                      SERVO_RANGES[3]["max"], SERVO_RANGES[3]["min"])
                    state.eye_position["y"] = y_angle
                    move_servo(3, y_angle)
                    update_upper_lids_vertical()
                    
                elif event.code == "BTN_THUMBL" and event.state == 1:  # Left stick press
                    threading.Thread(target=blink).start()

        except Exception as e:
            print(f"Gamepad error: {e}")
            time.sleep(0.1)

def cleanup():
    """Clean up and exit"""
    state.running = False
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

if __name__ == "__main__":
    try:
        print("Starting gamepad control. Press Ctrl+C or Back button to exit.")
        print("Use left analog stick to control eye movement")
        print("Press left analog stick to manually blink")
        print("Use LT/RT to control left/right eyelid closure")
        print("Press RB to toggle between full open and mid position")

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
