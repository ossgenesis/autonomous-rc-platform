import asyncio
from bleak import BleakScanner

async def scan_for_devices():
    print("Scanning for Bluetooth LE devices for 10 seconds...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    print("\n--- Discovered Devices ---")
    if not devices:
        print("No devices found. Ensure Bluetooth is enabled and the car is turned on.")
        return
        
    for d in devices:
        # Some devices might not have a name, so we handle that gracefully
        name = d.name if d.name else "Unknown Device"
        # RSSI is the signal strength. Higher (closer to 0) is better.
        print(f"Name: {name}")
        print(f"Address (UUID on macOS): {d.address}")
        print("-" * 30)

if __name__ == "__main__":
    # macOS requires asyncio to run properly
    asyncio.run(scan_for_devices())
