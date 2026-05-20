import asyncio
from bleak import BleakClient

DEVICE_UUID = "26BE0662-699D-76F0-E62F-E528B929CDA1"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"

# These are the most common "magic numbers" used to start commands in cheap RC toys
COMMON_HEADERS = [0xFF, 0x66, 0x01, 0x00, 0x55, 0xAA, 0x5A, 0xFC, 0x43]

async def brute_force():
    print("Connecting to RC Car...")
    try:
        async with BleakClient(DEVICE_UUID) as client:
            print("Connected! Starting BRUTE FORCE...")
            print("🚨 WATCH THE CAR! If it moves, press Ctrl+C IMMEDIATELY! 🚨\n")
            
            # Create an ordered list of 'first bytes' prioritizing the most common ones
            all_first_bytes = COMMON_HEADERS + [b for b in range(256) if b not in COMMON_HEADERS]
            
            count = 0
            for i in all_first_bytes:
                for j in range(256):
                    cmd = bytes([i, j])
                    
                    # Print every 20th combo to reduce screen lag, but show exactly what is being tested
                    if count % 20 == 0:
                        print(f"Testing [ {hex(i)}, {hex(j)} ] ... (Sent {count} combos)", end='\r')
                    
                    try:
                        # response=False is critical so it sends instantly without waiting for a reply
                        await client.write_gatt_char(WRITE_CHAR, cmd, response=False)
                    except Exception:
                        # Ignore occasional BLE buffering errors and keep blasting
                        pass
                    
                    count += 1
                    # A tiny 30ms sleep so we don't crash the Mac's Bluetooth chip, but fast enough to test thousands quickly
                    await asyncio.sleep(0.03)
                    
            print("\n\nFinished all 65,536 combinations. If it didn't move, it needs a 3-byte or larger sequence!")
            
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(brute_force())
