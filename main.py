import keyboard
import time
import threading
import sys
import torch
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from post_processing import TextRefiner
from config_handler import load_config
from utils import copy_to_clipboard, notify_user

def main():
    config = load_config()
    APP_NAME = config.get("app_name", "HelpMyToAnswer")
    
    print(f"{APP_NAME} is starting...")
    print(f"Configuration: {config}")
    
    # Determine device
    device_config = config.get("device", "auto")
    if device_config == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = device_config
    
    print(f"Using device: {device}")

    recorder = AudioRecorder()
    transcriber = Transcriber(model_size=config.get("whisper_model", "base"), device=device)
    
    refiner = None
    if config.get("use_ollama", True):
        refiner = TextRefiner(model=config.get("ollama_model", "llama3"))
    
    is_recording = False
    
    def on_hotkey():
        nonlocal is_recording
        if not is_recording:
            print("Start recording...")
            is_recording = True
            recorder.start_recording()
            notify_user(APP_NAME, "Recording started...")
        else:
            print("Stop recording...")
            is_recording = False
            audio_path = recorder.stop_recording()
            notify_user(APP_NAME, "Transcribing...")
            
            try:
                # 1. Transcribe
                raw_text = transcriber.transcribe(audio_path)
                if not raw_text:
                    notify_user(APP_NAME, "No speech detected.")
                    return

                print(f"Raw transcription: {raw_text}")
                
                final_text = raw_text
                
                # 2. Refine with Ollama (if enabled)
                if refiner:
                    notify_user(APP_NAME, "Refining text...")
                    refined = refiner.refine(raw_text)
                    if refined:
                        final_text = refined
                        print(f"Refined text: {final_text}")
                    else:
                        print("Refinement failed, using raw text.")

                # 3. Copy
                if final_text:
                    copy_to_clipboard(final_text)
                    notify_user(APP_NAME, "Copied to clipboard!")
                else:
                     notify_user(APP_NAME, "Result empty.")

            except Exception as e:
                print(f"Error: {e}")
                notify_user(APP_NAME, f"Error: {e}")

    # Set up global hotkey
    hotkey = config.get("hotkey", "ctrl+alt+r")
    try:
        keyboard.add_hotkey(hotkey, on_hotkey)
        print(f"Ready! Press {hotkey} to record.")
    except Exception as e:
        print(f"Failed to bind hotkey '{hotkey}': {e}")
    
    # Keep the script running
    keyboard.wait()

if __name__ == "__main__":
    main()
