import argparse
import csv
import os
import time
import sys

# Ensure we can import the HUD from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import cv2
except ImportError:
    print("Error: OpenCV is not installed. Please run `pip install opencv-python`")
    sys.exit(1)

try:
    from video.hud import draw_hud
except ImportError:
    print("Error: Could not import video.hud. Make sure you run this from the project root.")
    sys.exit(1)

def replay_session(dataset_dir):
    """
    Reads a dataset session folder and replays the frames with the recorded commands overlaid.
    """
    labels_path = os.path.join(dataset_dir, "labels.csv")
    frames_dir = os.path.join(dataset_dir, "frames")

    if not os.path.exists(labels_path):
        print(f"Error: labels.csv not found in {dataset_dir}")
        return
    if not os.path.exists(frames_dir):
        print(f"Error: frames directory not found in {dataset_dir}")
        return

    print(f"Loading session from: {dataset_dir}")
    
    # Read labels
    records = []
    with open(labels_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    
    print(f"Found {len(records)} frames to replay.")
    print("Press 'q' to quit replay. Press 'Space' to pause/play. Use left/right arrows to step frames when paused.")

    if not records:
        print("No records found.")
        return

    fps = 30
    delay = int(1000 / fps)
    
    idx = 0
    paused = False

    while idx < len(records):
        row = records[idx]
        frame_filename = row.get("frame_file")
        command = row.get("command", "stop")
        
        frame_path = os.path.join(frames_dir, frame_filename)
        
        if not os.path.exists(frame_path):
            print(f"Warning: Frame missing {frame_path}")
            idx += 1
            continue
            
        frame = cv2.imread(frame_path)
        if frame is None:
            print(f"Warning: Could not read {frame_path}")
            idx += 1
            continue

        # Reconstruct state dictionary for the HUD
        state = {
            "command": command,
            "recording": False, # We are replaying, not recording
            "frame_count": idx,
            "fps": fps,
            "ble_status": "REPLAY",
            "latency_ms": 0
        }

        # Draw HUD
        hud_frame = draw_hud(frame, state)
        
        cv2.imshow("Dataset Replay", hud_frame)

        # Handle playback controls
        if paused:
            key = cv2.waitKey(0) & 0xFF
            if key == ord(' '):
                paused = False
            elif key == 2: # Left arrow key on mac (OpenCV waitKey is tricky with arrows, but using generic mapping)
                idx = max(0, idx - 1)
                continue
            elif key == 3: # Right arrow
                idx = min(len(records) - 1, idx + 1)
                continue
            elif key == ord('q'):
                break
        else:
            key = cv2.waitKey(delay) & 0xFF
            if key == ord(' '):
                paused = True
            elif key == ord('q'):
                break
            
            idx += 1

    cv2.destroyAllWindows()
    print("Replay finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replay a recorded RC car session with HUD overlay.")
    parser.add_argument("dataset", help="Path to the dataset session directory (e.g., dataset/20260526T143012)")
    args = parser.parse_args()
    
    replay_session(args.dataset)
