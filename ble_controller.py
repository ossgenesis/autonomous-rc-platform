import asyncio
import sys
import tty
import termios
from bleak import BleakClient

DEVICE_UUID = "26BE0662-699D-76F0-E62F-E528B929CDA1"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"

# The official intercepted commands!
COMMANDS = {
    'w': bytes.fromhex("AA000200000000420002"), # Forward
    's': bytes.fromhex("AA000200000000410002"), # Backward
    'a': bytes.fromhex("AA000200000000440002"), # Left
    'd': bytes.fromhex("AA000200000000480002"), # Right
    'stop': bytes.fromhex("AA000200000000400002") # Neutral / Stop
}

# Global variable to store the currently active command
current_command = COMMANDS['stop']
running = True

def get_char():
    """Reads a single character from the standard input."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

async def keyboard_listener():
    global current_command, running
    loop = asyncio.get_running_loop()
    
    while running:
        # Run blocking keyboard read in a separate thread
        char = await loop.run_in_executor(None, get_char)
        char = char.lower()
        
        if char == 'x':
            running = False
            break
        elif char in ['w', 'a', 's', 'd']:
            current_command = COMMANDS[char]
            print(f"\r\n[State Changed] Direction: {char.upper()}")
        elif char == ' ':
            current_command = COMMANDS['stop']
            print(f"\r\n[State Changed] STOPPED")

async def bluetooth_sender(client):
    global current_command, running
    
    while running:
        if current_command:
            try:
                # Send the current command constantly every 100ms
                # IMPORTANT: PacketLogger showed "Write Request" (which means response=True) 
                # instead of "Write Command" (response=False). The car was probably ignoring our packets!
                await client.write_gatt_char(WRITE_CHAR, current_command, response=True)
            except Exception:
                pass
        
        # 0.1s matches the 140ms transmission rate you intercepted on the iPhone!
        await asyncio.sleep(0.1)

async def control_loop(client):
    print("\n--- CONTINUOUS BLUETOOTH CONTROLLER ---")
    print("Use W, A, S, D to drive. Press 'x' to quit.")
    print("Press SPACE to stop the car.")
    
    # Run both the keyboard listener and continuous bluetooth sender at the same time
    listener_task = asyncio.create_task(keyboard_listener())
    sender_task = asyncio.create_task(bluetooth_sender(client))
    
    await asyncio.gather(listener_task, sender_task)

async def main():
    print("Connecting to Hacked RC Car...")
    try:
        async with BleakClient(DEVICE_UUID) as client:
            print("Connected successfully!")
            await control_loop(client)
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
