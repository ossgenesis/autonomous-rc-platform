# OpenAutoRC 🚗🤖 

OpenAutoRC is an open-source framework designed to transform affordable, off-the-shelf RC cars into fully autonomous, computer-vision-powered vehicles. 

This repository currently serves as the foundational **Control Layer**. We have successfully reverse-engineered the proprietary Bluetooth Low Energy (BLE) protocols used by generic RC toys (like the `YC_CAR_DEMO`). By breaking these cars out of their restrictive mobile apps, we can now control them programmatically from any computer, paving the way for the next phase: **Autonomous AI Driving**.

## Vision & Roadmap 🗺️

Our ultimate goal is to build an accessible platform for hobbyists and researchers to experiment with self-driving algorithms and computer vision without needing to buy expensive proprietary robotics hardware.

- [x] **Phase 1: Protocol Reverse Engineering (Completed)**
  - Successfully intercepted and replicated the 10-byte proprietary Bluetooth payload.
  - Built an asynchronous Python controller for manual WASD keyboard driving.
  - Developed automated fuzzers for discovering unknown protocols on other toy cars.
- [ ] **Phase 2: Video Telemetry & Data Collection (Up Next)**
  - Integrate a camera stream (via a mounted phone or an attached ESP32-CAM) directly into the control script.
  - Build a data collection pipeline to record human-driven training data (Images paired with WASD steering inputs).
- [ ] **Phase 3: Computer Vision & AI Self-Driving**
  - Train a Convolutional Neural Network (CNN) for lane detection and obstacle avoidance (e.g., using YOLO or OpenCV).
  - Implement a closed-loop control system where the AI script directly drives the car via our BLE abstraction layer.

---

## Current State: BLE Control Layer

While we build the Computer Vision models, this repository currently functions as a robust Python BLE controller for manual driving and protocol hacking.

### Requirements
- Python 3.8+
- `bleak` library
- A BLE-capable machine (Mac, Linux, or Windows)

### Installation
```bash
# Clone the repository
git clone https://github.com/ossgenesis/OpenAutoRC.git
cd OpenAutoRC

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install bleak
```

### Driving the Car
Make sure the official app is completely closed on your phone so your computer can connect to the car's Bluetooth chip.

```bash
python ble_controller.py
```
Use `W`, `A`, `S`, `D` to steer, `Spacebar` to stop, and `X` to exit. 
*Note: The script automatically handles the "safety timeout" by continuously transmitting packets (`response=True`) at 100ms intervals.*

### Exploring Unknown Protocols
If you have a different RC car and want to help expand our supported hardware, you can use our included fuzzers to try and identify the command structure:
- `ble_fuzzer.py`: Scans 1-byte and 2-byte commands.
- `ble_smart_fuzzer.py`: Scans common 3-byte and 4-byte manufacturer sequences.
- `ble_brute_fuzzer.py`: Exhaustively brute-forces 65,536 combinations.

## Contributing
See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to help. We are actively looking for contributions to Phase 2 (Computer Vision) and payloads for other generic Bluetooth toy cars!

## License
Distributed under the Apache 2.0 License. See `LICENSE` for more information.
