import asyncio
from bleak import BleakClient

DEVICE_UUID = "26BE0662-699D-76F0-E62F-E528B929CDA1"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"

async def fuzz_car():
    print("Connecting to RC Car...")
    try:
        async with BleakClient(DEVICE_UUID) as client:
            print("Connected! Starting automated tests...")
            print("\n🚨 WATCH THE PHYSICAL CAR! If it twitches, spins, or moves, look at the screen and remember the command! 🚨")
            print("Press Ctrl+C to stop when you see it move.\n")
            
            # Phase 1: Test single byte commands (0x00 to 0xFF)
            print("--- Phase 1: Single Bytes ---")
            for i in range(1, 256):
                cmd = bytes([i])
                print(f"Sending Single Byte: {hex(i)}", end='\r')
                try:
                    await client.write_gatt_char(WRITE_CHAR, cmd, response=False)
                except Exception:
                    pass
                await asyncio.sleep(0.3)
                
            # Phase 2: Test 2-byte commands
            print("\n\n--- Phase 2: 2-Byte Commands ---")
            for i in range(1, 256):
                cmd = bytes([i, 0x00])
                print(f"Sending 2-Byte: {hex(i)} 0x00", end='\r')
                try:
                    await client.write_gatt_char(WRITE_CHAR, cmd, response=False)
                except Exception:
                    pass
                await asyncio.sleep(0.3)
                
            print("\n\nFinished testing. Did it move at all?")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(fuzz_car())
