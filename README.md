# RC Car Bluetooth Controller 🚗📶

A Python-based Bluetooth Low Energy (BLE) controller for generically-branded RC cars (like `YC_CAR_DEMO`). This project reverse-engineers the proprietary Bluetooth protocol used by cheap RC car apps (e.g., `LCW_RCcar`) to allow keyboard control (WASD) from a Mac/Linux machine.

## Motivation
Many affordable RC cars rely on proprietary iOS/Android applications to connect via Bluetooth. Because these apps are heavily sandboxed and often do not support MacOS, it is impossible to control the cars from a computer out of the box. 

This repository successfully reverse-engineers the 10-byte binary protocol required to drive the car and provides a fully asynchronous Python script to intercept and replicate the commands.

## Features
- **WASD Keyboard Control**: Drive your RC car seamlessly from your terminal.
- **Continuous Transmission**: Automatically handles the "safety timeout" by continuously transmitting packets (`response=True`) at 100ms intervals, mimicking the official app.
- **Automated Fuzzers**: Includes brute-force and smart-fuzzing scripts for identifying protocols on other undocumented toy cars.

## Requirements
- Python 3.8+
- `bleak` library
- A BLE-capable machine (Mac, Linux, or Windows)

## Installation
```bash
# Clone the repository
git clone https://github.com/ossgenesis/rc-car-bluetooth.git
cd rc-car-bluetooth

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install bleak
```

## Usage

### Driving the Car
Make sure the official app is completely closed on your phone so your computer can connect to the car's Bluetooth chip.

```bash
python ble_controller.py
```
Use `W`, `A`, `S`, `D` to steer, `Spacebar` to stop, and `X` to exit.

### Exploring Unknown Protocols
If you have a different RC car, you can use our included fuzzers to try and identify the command structure:
- `ble_fuzzer.py`: Scans 1-byte and 2-byte commands.
- `ble_smart_fuzzer.py`: Scans common 3-byte and 4-byte manufacturer sequences (`0x66`, `0xFF`, `0x55`).
- `ble_brute_fuzzer.py`: Exhaustively brute-forces 65,536 2-byte combinations.

*Note: If the fuzzers fail, the car likely uses a structured multi-byte protocol with Checksums. You will need to use Apple's PacketLogger or Android's HCI Snoop Log to manually sniff the protocol.*

## Protocol Details
The protocol for the generic `YC_CAR_DEMO` is a 10-byte hex array written to characteristic `0000fff2-0000-1000-8000-00805f9b34fb` using **Write Request**.
- Forward: `AA000200000000420002`
- Backward: `AA000200000000410002`
- Left: `AA000200000000440002`
- Right: `AA000200000000480002`
- Stop: `AA000200000000400002`

## Contributing
See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to help. We are actively looking for payloads for other generic Bluetooth toy cars!

## License
Distributed under the Apache 2.0 License. See `LICENSE` for more information.
