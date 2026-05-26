import cv2
import numpy as np

def draw_hud(frame: np.ndarray, state: dict) -> np.ndarray:
    """
    Overlays telemetry and active commands onto the video frame.
    
    Expected state dict:
    {
        "command": "w",         # 'w', 'a', 's', 'd', or 'stop'
        "recording": True,      # bool
        "frame_count": 1234,    # int
        "fps": 30,              # int or float
        "ble_status": "OK",     # string
        "latency_ms": 1500      # int
    }
    """
    # Create a copy so we don't mutate the original frame unless desired
    output = frame.copy()
    h, w, _ = output.shape

    # Fonts and colors
    font = cv2.FONT_HERSHEY_SIMPLEX
    color_white = (255, 255, 255)
    color_green = (0, 255, 0)
    color_red = (0, 0, 255)
    color_bg = (0, 0, 0)
    
    # --- 1. Top Right: Recording Status ---
    if state.get("recording", False):
        # Blinking logic (blink every 15 frames)
        if state.get("frame_count", 0) % 30 < 15:
            cv2.circle(output, (w - 150, 40), 10, color_red, -1)
        cv2.putText(output, "REC", (w - 130, 45), font, 0.8, color_red, 2)
    
    cv2.putText(output, f"Frame: {state.get('frame_count', 0)}", (w - 150, 80), font, 0.6, color_white, 1)

    # --- 2. Bottom Right: Telemetry ---
    # Draw a dark transparent background for telemetry
    overlay = output.copy()
    cv2.rectangle(overlay, (w - 200, h - 120), (w, h), color_bg, -1)
    alpha = 0.5
    cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)

    cv2.putText(output, f"FPS: {state.get('fps', 0):.1f}", (w - 190, h - 90), font, 0.6, color_white, 1)
    cv2.putText(output, f"BLE: {state.get('ble_status', 'Unknown')}", (w - 190, h - 60), font, 0.6, color_green if state.get('ble_status') == 'OK' else color_red, 1)
    cv2.putText(output, f"RTMP Lag: ~{state.get('latency_ms', 0)}ms", (w - 190, h - 30), font, 0.5, color_white, 1)

    # --- 3. Bottom Left: Visual D-Pad ---
    dpad_x, dpad_y = 50, h - 150
    btn_size = 40
    gap = 5
    
    active_cmd = state.get("command", "stop").lower()

    # W A S D coordinates
    btns = {
        'w': (dpad_x + btn_size + gap, dpad_y),
        'a': (dpad_x, dpad_y + btn_size + gap),
        's': (dpad_x + btn_size + gap, dpad_y + btn_size + gap),
        'd': (dpad_x + (btn_size + gap) * 2, dpad_y + btn_size + gap)
    }

    for key, (bx, by) in btns.items():
        # Highlight if active
        if key == active_cmd:
            cv2.rectangle(output, (bx, by), (bx + btn_size, by + btn_size), color_green, -1)
            cv2.putText(output, key.upper(), (bx + 10, by + 28), font, 0.8, color_bg, 2)
        else:
            cv2.rectangle(output, (bx, by), (bx + btn_size, by + btn_size), color_white, 2)
            cv2.putText(output, key.upper(), (bx + 10, by + 28), font, 0.8, color_white, 2)

    return output
