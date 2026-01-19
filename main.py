import keyboard
import time
import threading
import sys
import torch
import logging
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from post_processing import TextRefiner
from config_handler import load_config
from utils import copy_to_clipboard, notify_user
import ctypes
from pystray import Icon, MenuItem as item
from PIL import Image, ImageDraw

# Setup logging
logging.basicConfig(
    filename='app.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Fix for "NoneType object has no attribute write" in windowless mode
# This happens when libraries (like tqdm in Whisper) try to print to stdout/stderr
class NullWriter:
    def write(self, text):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

def is_already_running():
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexA(None, False, b"Global\\HelpMyToAnswerAppMutex")
    if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        return True
    return False

def create_image():
    # Create an icon image programmatically
    width = 64
    height = 64
    color1 = "blue"
    color2 = "white"
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.ellipse((16, 16, 48, 48), fill=color2)
    return image

def main():
    if is_already_running():
        # If already running, we can't easily notify the user via GUI since we are windowless,
        # but we can log it.
        logging.warning("Attempted to start a second instance. Exiting.")
        sys.exit(0)

    try:
        config = load_config()
        APP_NAME = config.get("app_name", "HelpMyToAnswer")
        
        logging.info(f"{APP_NAME} is starting...")
        logging.info(f"Configuration: {config}")
        
        # Determine device
        device_config = config.get("device", "auto")
        if device_config == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            device = device_config
        
        logging.info(f"Using device: {device}")

        recorder = AudioRecorder()
        transcriber = Transcriber(model_size=config.get("whisper_model", "base"), device=device)
        
        refiner = None
        if config.get("use_ollama", True):
            refiner = TextRefiner(model=config.get("ollama_model", "llama3"))
            logging.info("Ollama refiner initialized")
        
        is_recording = False
        last_hotkey_time = 0
        
        def on_hotkey():
            nonlocal is_recording, last_hotkey_time
            
            # Debounce: ignore events faster than 0.5s
            current_time = time.time()
            if current_time - last_hotkey_time < 0.5:
                 logging.debug("Hotkey ignored (debounce)")
                 return
            last_hotkey_time = current_time

            logging.info(f"Hotkey pressed. Current state: recording={is_recording}")
            if not is_recording:
                logging.info("Start recording...")
                is_recording = True
                recorder.start_recording()
                notify_user(APP_NAME, "Recording started...")
            else:
                logging.info("Stop recording...")
                is_recording = False
                audio_path = recorder.stop_recording()
                notify_user(APP_NAME, "Transcribing...")
                
                try:
                    # 1. Transcribe
                    logging.info("Transcribing...")
                    raw_text = transcriber.transcribe(audio_path)
                    if not raw_text:
                        notify_user(APP_NAME, "No speech detected.")
                        logging.info("No speech detected.")
                        return

                    logging.info(f"Raw transcription: {raw_text}")
                    
                    final_text = raw_text
                    
                    # 2. Refine with Ollama (if enabled)
                    if refiner:
                        notify_user(APP_NAME, "Refining text...")
                        logging.info("Refining text...")
                        refined = refiner.refine(raw_text)
                        if refined:
                            final_text = refined
                            logging.info(f"Refined text: {final_text}")
                        else:
                            logging.info("Refinement failed, using raw text.")

                    # 3. Copy
                    if final_text:
                        copy_to_clipboard(final_text)
                        notify_user(APP_NAME, "Copied to clipboard!")
                        logging.info("Copied to clipboard.")
                    else:
                        notify_user(APP_NAME, "Result empty.")
                        logging.info("Result empty.")

                except Exception as e:
                    logging.error(f"Error during processing: {e}")
                    notify_user(APP_NAME, f"Error: {e}")

        # Set up global hotkey
        hotkey = config.get("hotkey", "ctrl+alt+r")
        try:
            keyboard.add_hotkey(hotkey, on_hotkey)
            logging.info(f"Ready! Press {hotkey} to record.")
            print(f"Ready! Press {hotkey} to record.")
        except Exception as e:
            logging.error(f"Failed to bind hotkey '{hotkey}': {e}")
            print(f"Failed to bind hotkey '{hotkey}': {e}")
        
        # System Tray Icon Setup
        def on_exit(icon, item):
            logging.info("Exiting application via tray...")
            icon.stop()
            sys.exit(0)

        icon = Icon("HelpMyToAnswer", create_image(), "HelpMyToAnswer", menu=(
            item('Exit', on_exit),
        ))
        
        logging.info("Starting System Tray Icon loop...")
        icon.run() # This blocks until icon.stop() is called
        
    except Exception as e:
        logging.critical(f"Critical fatal error: {e}")

if __name__ == "__main__":
    main()
