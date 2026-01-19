import whisper
import torch
import os

class Transcriber:
    def __init__(self, model_size="base", device="auto"):
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Loading Whisper model '{model_size}' on {self.device}...")
        try:
            self.model = whisper.load_model(model_size, device=self.device)
            print("Model loaded.")
        except Exception as e:
            print(f"Failed to load model on {self.device}: {e}")
            if self.device == "cuda":
                print("Falling back to cpu...")
                self.device = "cpu"
                self.model = whisper.load_model(model_size, device=self.device)

    def transcribe(self, audio_path):
        if not audio_path or not os.path.exists(audio_path):
            return None
        
        result = self.model.transcribe(audio_path)
        return result["text"].strip()
