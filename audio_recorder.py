import sounddevice as sd
import numpy as np
import wavio
import tempfile
import os
import queue

class AudioRecorder:
    def __init__(self, samplerate=16000, channels=1, device_index=None):
        self.samplerate = samplerate
        self.channels = channels
        self.device_index = device_index
        self.recording = False
        self.audio_queue = queue.Queue()
        self.filename = os.path.join(tempfile.gettempdir(), "whisper_clip_recording.wav")

    @staticmethod
    def get_input_devices():
        """Returns a list of dicts with 'index' and 'name' for input devices."""
        devices = []
        try:
            # Query devices
            all_devices = sd.query_devices()
            # Filter for input devices (max_input_channels > 0)
            for i, dev in enumerate(all_devices):
                if dev['max_input_channels'] > 0:
                    devices.append({'index': i, 'name': dev['name']})
        except Exception as e:
            print(f"Error listing devices: {e}")
        return devices

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, flush=True)
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.recording = True
        self.audio_queue = queue.Queue() # Clear queue
        try:
            self.stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                device=self.device_index,
                callback=self.callback
            )
            self.stream.start()
        except Exception as e:
            print(f"Failed to start recording stream: {e}")
            self.recording = False

    def stop_recording(self):
        try:
            if hasattr(self, 'stream'):
                self.stream.stop()
                self.stream.close()
        except Exception as e:
             print(f"Error closing stream: {e}")
        
        self.recording = False
        
        # Collect all data from queue
        data = []
        try:
            while not self.audio_queue.empty():
                data.append(self.audio_queue.get())
        except Exception as e:
             print(f"Error reading queue: {e}")
        
        if not data:
            print("No audio data collected.")
            return None
            
        # Concatenate and save to wav
        try:
            recording = np.concatenate(data, axis=0)
            wavio.write(self.filename, recording, self.samplerate, sampwidth=2)
            return self.filename
        except Exception as e:
            print(f"Error saving wav: {e}")
            return None
