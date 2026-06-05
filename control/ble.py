import asyncio
import threading
from typing import Set

from bleak import BleakClient

DEVICE_UUID = "26BE0662-699D-76F0-E62F-E528B929CDA1"
WRITE_CHAR  = "0000fff2-0000-1000-8000-00805f9b34fb"
INTERVAL_S  = 0.1

# Command byte is a bitmask: 0x40 base | direction bits
_CMD_BASE = 0x40
_KEY_BITS = {
    'w': 0x02,  # forward
    's': 0x01,  # backward
    'a': 0x04,  # left
    'd': 0x08,  # right
}


def _build_payload(active_keys: Set[str]) -> bytes:
    bits = _CMD_BASE
    for k in active_keys:
        bits |= _KEY_BITS.get(k, 0)
    return b'\xaa\x00\x02\x00\x00\x00\x00' + bytes([bits]) + b'\x00\x02'


# Single-key payloads kept for reference
COMMANDS = {k: _build_payload({k}) for k in _KEY_BITS}
COMMANDS['stop'] = _build_payload(set())


class BLEController:
    """
    Continuous Bluetooth sender with simultaneous key support.

    Press/release model (for human keyboard input):
        ble.press('w')   # key held down
        ble.release('w') # key released
        ble.release_all()  # emergency stop

    Single-command model (for AI inference):
        ble.set_command('a')  # replaces all active keys with one
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active: Set[str] = set()
        self._running = False
        self.link_state = "DISCONNECTED"

    # ── Key state API (human input) ─────────────────────────────────────────

    def press(self, key: str):
        if key in _KEY_BITS:
            with self._lock:
                self._active.add(key)

    def release(self, key: str):
        with self._lock:
            self._active.discard(key)

    def release_all(self):
        with self._lock:
            self._active.clear()

    # ── Single-command API (AI inference) ───────────────────────────────────

    def set_command(self, key: str):
        """Replace active key set with a single command (used by inference engine)."""
        with self._lock:
            self._active.clear()
            if key in _KEY_BITS:
                self._active.add(key)

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def current_key(self) -> str:
        with self._lock:
            keys = frozenset(self._active)
        if not keys:
            return 'stop'
        if len(keys) == 1:
            return next(iter(keys))
        return '+'.join(sorted(keys))

    # ── BLE loop ────────────────────────────────────────────────────────────

    async def run(self, client: BleakClient):
        self._running = True
        self.link_state = "OK"
        try:
            while self._running:
                with self._lock:
                    payload = _build_payload(self._active)
                await client.write_gatt_char(WRITE_CHAR, payload, response=True)
                await asyncio.sleep(INTERVAL_S)
        except asyncio.CancelledError:
            pass
        except Exception:
            self.link_state = "ERROR"
        finally:
            self.link_state = "DISCONNECTED"

    def stop(self):
        self._running = False
