# Raspberry Pi Animatronic Eyes Controller

This is an alternative implementation of [Will Cogley's Snap-fit Eye Mechanism](https://willcogley.notion.site/Will-Cogley-Project-Archive-75a4864d73ab4361ab26cabaadaec33a?p=b88ae87ceae24d1ca942adf34750bf87&pm=c) that uses a Raspberry Pi Zero and USB gamepad instead of the original Arduino setup. All credit for the mechanical design and original concept goes to Will Cogley.

Control animatronic eyes using a Raspberry Pi Zero and gamepad controller. Features include smooth eye movement, automatic blinking, and adjustable eyelid positions.

## Features

- Gamepad-based control of eye movements (horizontal and vertical)
- Automatic random blinking
- Manual blink control
- Adjustable eyelid positions (open, mid, squint, closed)
- Eyelids follow vertical eye movement for natural expressions
- Clean shutdown with neutral position

## Hardware Requirements

- Raspberry Pi Zero (Tested on Pi Zero and Pi 3)
- PCA9685 16-channel PWM/Servo controller
- 6 micro servos: 
  - 2 for horizontal and vertical eye movement
  - 4 for upper and lower eyelids (2 per eye)
- USB gamepad controller (Tested with Xbox-compatible)
- Power supply (5V for Pi, separate 5v power for PCA9685)
- I2C connection cables
- Will Cogley's Snap-fit Eye Mechanism (see original project page for STL files and assembly instructions)

## Servo Configuration

The code uses the following servo assignments:

- Channel 0: Left Lower Eyelid
- Channel 1: Left Upper Eyelid
- Channel 2: Horizontal Eye Movement
- Channel 3: Vertical Eye Movement
- Channel 4: Right Upper Eyelid
- Channel 5: Right Lower Eyelid

## Installation

Here's a complete setup guide from start to finish:

1. Initial Raspberry Pi Setup:
```bash
sudo raspi-config
```
Navigate to:
- Interface Options
  - I2C → Enable
  - SSH → Enable 
- System Options
  - Boot / Auto Login → Console Autologin
  
Reboot after changes:
```bash
sudo reboot
```

2. Install Base Requirements:
```bash
sudo apt-get update
sudo apt-get install python3-pip i2c-tools git
```

3. Verify I2C connection:
```bash
sudo i2cdetect -y 1
# Should show PCA9685 device (usually at address 0x40)
```

4. Create Project Directory:
```bash
mkdir eye_controller
cd eye_controller
```

5. Virtual Environment Setup (Optional but recommended. Needed for pi zero to resolve externally-managed-environment errors):
```bash
# Create virtual environment
python3 -m venv eye_venv

# Activate virtual environment
source eye_venv/bin/activate

# Install required packages
pip install adafruit-circuitpython-pca9685 adafruit-circuitpython-motor inputs
```

Note: If you choose not to use a virtual environment, you can install packages globally with:
```bash
sudo pip3 install adafruit-circuitpython-pca9685 adafruit-circuitpython-motor inputs
```

6. Create the Python Script:
```bash
# Save the code as eye_control.py
nano eye_control.py
# Paste the code and save (Ctrl+O, Enter, Ctrl+X)

# Make executable
chmod +x eye_control.py
```
## Setup Autorun 

1. Create Service File:
```bash
sudo nano /etc/systemd/system/eye-control.service
```

Add this content:
```ini
[Unit]
Description=Animatronic Eye Control
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eye_controller
ExecStart=/home/pi/eye_controller/eye_venv/bin/python /home/pi/eye_controller/eye_control.py
Restart=always

[Install]
WantedBy=multi-user.target
```
*replace your USER_NAME with pi

If not using virtual environment, modify ExecStart to:
```ini
ExecStart=/usr/bin/python3 /home/pi/eye_controller/eye_control.py
```

2. Enable and Start Service:
```bash
sudo systemctl enable eye-control
sudo systemctl start eye-control
```

3. Check Service Status:
```bash
sudo systemctl status eye-control
```
For troubleshooting, check service logs:
```bash
journalctl -u eye-control -f
```

## Usage

1. If service was enabled the controller will start at bootup
   
1(alternative). Start the controller:
```bash
python3 eye_control.py
```

2. Controls:
  - Use left analog stick to control eye movement")
  - Press left analog stick to manually blink")
  - Use LT/RT to control left/right eyelid closure")
  - Press RB to toggle between full open and mid position")
  - Press LB to toggle squint position")

## Customization

The servo ranges can be adjusted in the `SERVO_RANGES` dictionary at the top of the script:

```python
SERVO_RANGES = {
    0: {"min": 110, "max": 155},   # Left Lower Lid
    1: {"min": 0, "max": 45},      # Left Upper Lid
    2: {"min": 50, "max": 130},    # Eye Horizontal
    3: {"min": 0, "max": 90},      # Eye Vertical
    4: {"min": 0, "max": 50},      # Right Upper Lid
    5: {"min": 110, "max": 155},   # Right Lower Lid
}
```

Other adjustable parameters:
- `VERTICAL_LID_MODIFIER`: Controls how much the eyelids follow vertical eye movement
- `blink_interval`: Random time between automatic blinks (default 4-9 seconds)

## Troubleshooting

1. If servos don't move:
   - Check I2C connections
   - Verify servo power supply
   - Run `i2cdetect -y 1` to confirm PCA9685 is detected

2. If gamepad isn't recognized:
   - Check USB connection
   - Test gamepad with `jstest /dev/input/js0`
   - Verify gamepad compatibility

3. Servo jitter:
   - Check power supply stability
   - Adjust min/max pulse width in servo initialization
   - Verify servo range values are appropriate

## Safety Notes

- Always power servos with a separate power supply to avoid overloading the Pi
- Ensure servos are properly secured to prevent damage
- Test servo ranges carefully to avoid mechanical binding

## License

MIT License

Copyright (c) 2024 Elijah Atkins

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
