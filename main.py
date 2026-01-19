import keyboard
import time
import threading
import sys
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from utils import copy_to_clipboard, notify_user

def main():
    print("WhisperClip for Windows is starting...")
    
    recorder = AudioRecorder()
    transcriber = Transcriber()
    
    # Check for CUDA availability
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    is_recording = False
    
    def on_hotkey():
        nonlocal is_recording
        if not is_recording:
            print("Start recording...")
            is_recording = True
            recorder.start_recording()
            notify_user("WhisperClip", "Recording started...")
        else:
            print("Stop recording...")
            is_recording = False
            audio_path = recorder.stop_recording()
            notify_user("WhisperClip", "Transcribing...")
            
            try:
                text = transcriber.transcribe(audio_path)
                if text:
                    copy_to_clipboard(text)
                    print(f"Transcribed: {text}")
                    notify_user("WhisperClip", "Text copied to clipboard!")
                else:
                    notify_user("WhisperClip", "No speech detected.")
            except Exception as e:
                print(f"Error: {e}")
                notify_user("WhisperClip", f"Error: {e}")

    # Set up global hotkey (Ctrl + Alt + R)
    keyboard.add_hotkey('ctrl+alt+r', on_hotkey)
    print("Ready! Press Ctrl+Alt+R to record.")
    
    # Keep the script running
    keyboard.wait()

if __name__ == "__main__":
    main()
