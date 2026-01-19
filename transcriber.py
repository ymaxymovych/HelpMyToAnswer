import whisper
import torch
import os

import logging
import shutil

class Transcriber:
    def __init__(self, model_size="base", device="auto"):
        self.model = None  # Ensure attribute exists
        
        # Ensure FFmpeg is in path. Check current directory first.
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        ffmpeg_local = os.path.join(current_dir, "ffmpeg.exe")
        if os.path.exists(ffmpeg_local):
            logging.info(f"Found local ffmpeg at {ffmpeg_local}, adding to PATH")
            os.environ["PATH"] += os.pathsep + current_dir

        # Check for FFmpeg again
        if not shutil.which("ffmpeg"):
            logging.error("FFmpeg not found in system PATH. Whisper requires FFmpeg.")
            # We don't raise here, letting it try, but it will likely fail.
        
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        logging.info(f"Loading Whisper model '{model_size}' on {self.device}...")
        try:
            self.model = whisper.load_model(model_size, device=self.device)
            logging.info("Model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load model on {self.device}: {e}")
            if self.device == "cuda":
                logging.info("Falling back to cpu...")
                self.device = "cpu"
                try:
                    self.model = whisper.load_model(model_size, device=self.device)
                    logging.info("Model loaded on CPU fallback.")
                except Exception as ex_cpu:
                    logging.critical(f"Failed to load model on CPU: {ex_cpu}")
                    self.model = None
            else:
                self.model = None

    def transcribe(self, audio_path):
        if not self.model:
             logging.error("Transcriber model is not initialized.")
             return None

        if not audio_path or not os.path.exists(audio_path):
            logging.warning(f"Audio path invalid: {audio_path}")
            return None
        
        try:
            result = self.model.transcribe(audio_path)
            return result["text"].strip()
        except Exception as e:
            logging.error(f"Error during transcription: {e}")
            return None
