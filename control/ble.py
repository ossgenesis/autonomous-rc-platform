import asyncio
from bleak import BleakClient

DEVICE_UUID = "26BE0662-699D-76F0-E62F-E528B929CDA1"
WRITE_CHAR  = "0000fff2-0000-1000-8000-00805f9b34fb"
INTERVAL_S  = 0.1  # matches the 100ms packet rate from the original iPhone capture

COMMANDS = {
    'w':    bytes.fromhex("AA000200000000420002"),  # Forward
    's':    bytes.fromhex("AA000200000000410002"),  # Backward
    'a':    bytes.fromhex("AA000200000000440002"),  # Left
    'd':    bytes.fromhex("AA000200000000480002"),  # Right
    'stop': bytes.fromhex("AA000200000000400002"),  # Neutral
}


class BLEController:
    """Continuous Bluetooth sender. Call set_command() from any thread; run() drives the BLE loop."""

    def __init__(self):
        self._cmd = COMMANDS['stop']
        self._running = False
        self.link_state = "DISCONNECTED"
        self.current_key = "stop"

    def set_command(self, key: str):
        self._cmd = COMMANDS.get(key, COMMANDS['stop'])
        self.current_key = key if key in COMMANDS else "stop"

    async def run(self, client: BleakClient):
        self._running = True
        self.link_state = "OK"
        try:
            while self._running:
                await client.write_gatt_char(WRITE_CHAR, self._cmd, response=True)
                await asyncio.sleep(INTERVAL_S)
        except asyncio.CancelledError:
            pass
        except Exception:
            self.link_state = "ERROR"
        finally:
            self.link_state = "DISCONNECTED"

    def stop(self):
        self._running = False
