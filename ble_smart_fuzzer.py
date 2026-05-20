import asyncio
from bleak import BleakClient
import time

DEVICE_UUID = "26BE0662-699D-76F0-E62F-E528B929CDA1"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"

# The most common Chinese RC Car BLE payloads (forward/move commands)
PAYLOADS = [
    # 1. 0x66 Header (Very common for YC_CAR and similar)
    ("Type 1: 0x66 Header", bytes([0x66, 0x80, 0x80, 0x00, 0x00, 0x99])),
    ("Type 1b: 0x66 alt", bytes([0x66, 0x01, 0x01, 0x00, 0x00, 0x99])),
    
    # 2. QY-BLE Style
    ("Type 2: QY-BLE", bytes([0xAA, 0x55, 0x01, 0x00, 0x00, 0x55, 0xAA])),
    
    # 3. 0xFF Header
    ("Type 3: 0xFF Header", bytes([0xFF, 0x01, 0x50, 0xFF])),
    ("Type 3b: 0xFF Padding", bytes([0xFF, 0x00, 0x01, 0x00, 0xFF])),
    
    # 4. LEDBLE (PWM style)
    ("Type 4: LEDBLE Style", bytes([0x56, 0x01, 0x01, 0x00, 0xFF, 0x00, 0xF0, 0xAA])),
    
    # 5. CMD ASCII Prefix
    ("Type 5: CMD ASCII", bytes([0x43, 0x4D, 0x44, 0x01, 0x00])),
    
    # 6. 0x5A Header with typical checksum
    ("Type 6: 0x5A Header", bytes([0x5A, 0x01, 0x01, 0x5C])),
    
    # 7. 0xFC Header
    ("Type 7: 0xFC Header", bytes([0xFC, 0x01, 0x00, 0x00, 0x00, 0x00, 0xFD])),
    
    # 8. 0xA5 Header
    ("Type 8: 0xA5 Header", bytes([0xA5, 0x01, 0x00, 0x00, 0xA6])),
    
    # 9. ASCII Strings
    ("Type 9: ASCII FORWARD", b"FORWARD\r\n"),
    ("Type 9b: ASCII F", b"F\r\n"),
    
    # 10. AT Commands
    ("Type 10: AT+F", b"AT+F\r\n"),
]

async def smart_fuzz():
    print("Connecting to RC Car...")
    try:
        async with BleakClient(DEVICE_UUID) as client:
            print("Connected! Starting Smart Fuzzer...")
            print("\n🚨 WATCH THE PHYSICAL CAR VERY CLOSELY! 🚨")
            print("If it twitches, spins, or moves, press Ctrl+C immediately and note the Type!\n")
            
            for name, payload in PAYLOADS:
                print(f"Testing {name}: {payload.hex(' ')}")
                
                # Send the payload a few times to ensure the car registers it
                for _ in range(3):
                    try:
                        await client.write_gatt_char(WRITE_CHAR, payload, response=False)
                    except Exception as e:
                        pass
                    await asyncio.sleep(0.2)
                
                # Wait before trying the next completely different protocol
                await asyncio.sleep(1.5)
                
            print("\nFinished all common payloads. Did it move?")
            
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(smart_fuzz())
