# Contributing

First off, thank you for considering contributing to this repository! We welcome contributions from everyone.

## How to Contribute

### Reporting Bugs
If you find a bug, please use the provided Bug Report template in the `.github/ISSUE_TEMPLATE/` folder. Be sure to include your OS, Python version, and a clear description of the issue.

### Suggesting Enhancements
If you have an idea for a new feature or want to support a new RC car protocol, please create an issue using the Feature Request template. 

### Pull Requests
1. Fork the repository and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Format your code using standard Python formatters (e.g., `black`).
5. Issue that pull request!

## Adding New Protocols
The primary goal of this repository is to support various generic Bluetooth RC cars. If you have successfully intercepted a new protocol (via PacketLogger or HCI Snoop Log), please feel free to create a new controller profile and submit a PR!

When submitting a new protocol, please include:
- The Bluetooth `UUID` used by the car.
- The `Write` characteristic.
- Whether it requires `Write Request` (response=True) or `Write Command` (response=False).
- The Hex payloads for basic movements.
