import asyncio
from bleak import BleakClient

DEVICE_UUID = "26BE0662-699D-76F0-E62F-E528B929CDA1"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"

FORWARD_CMD = bytes.fromhex("AA000200000000420002")

async def test_forward():
    print("Connecting to RC Car for AI automated test...")
    try:
        async with BleakClient(DEVICE_UUID) as client:
            print("Connected! Sending 'Forward' command 20 times (2 seconds of movement)...")
            
            for i in range(20):
                print(f"Sending packet {i+1}/20...")
                await client.write_gatt_char(WRITE_CHAR, FORWARD_CMD, response=True)
                await asyncio.sleep(0.1)
                
            print("Test complete. Disconnecting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_forward())
