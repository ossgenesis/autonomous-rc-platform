import asyncio
import sys
from bleak import BleakClient

# We will pass the UUID as an argument
async def inspect_device(address):
    print(f"Connecting to {address}...")
    try:
        async with BleakClient(address) as client:
            print(f"Connected: {client.is_connected}")
            
            print("\n--- Services and Characteristics ---")
            for service in client.services:
                print(f"[Service] {service.uuid} (Handle: {service.handle}) - {service.description}")
                for char in service.characteristics:
                    print(f"  └─ [Characteristic] {char.uuid} (Handle: {char.handle})")
                    print(f"      Properties: {', '.join(char.properties)}")
                    
            print("\nInspection complete!")
    except Exception as e:
        print(f"Failed to connect or inspect: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ble_inspector.py <DEVICE_UUID>")
        sys.exit(1)
        
    address = sys.argv[1]
    asyncio.run(inspect_device(address))
