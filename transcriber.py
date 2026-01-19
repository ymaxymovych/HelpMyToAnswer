import whisper
import torch
import os
import logging
import shutil
import sys
import wavio
import numpy as np

# Fix for PyInstaller --noconsole removing stdout/stderr
class NullWriter:
    def write(self, text):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

class Transcriber:
    def __init__(self, model_size="base", device="auto"):
        self.model = None
        
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

    def transcribe(self, audio_path, language=None):
        if not self.model:
             logging.error("Transcriber model is not initialized.")
             return None

        if not audio_path or not os.path.exists(audio_path):
            logging.warning(f"Audio path invalid: {audio_path}")
            return None
        
        try:
            # Native WAV loading (No FFmpeg required)
            # Read WAV
            wav = wavio.read(audio_path)
            # Get data as numpy array
            data = wav.data
            
            # Convert to float32 and normalize
            # wavio returns data based on sampwidth. Usually int16.
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0
            elif data.dtype == np.uint8:
                data = (data.astype(np.float32) - 128) / 128.0
            
            # Flatten to 1D array (mono)
            data = data.flatten()
            
            # Whisper expects 16kHz audio. 
            # We assume AudioRecorder recorded at 16kHz (see audio_recorder.py default).
            
            options = {}
            if language:
                options["language"] = language
            
            result = self.model.transcribe(data, **options)
            return result["text"].strip()
        except Exception as e:
            logging.error(f"Error during transcription: {e}")
            return None
