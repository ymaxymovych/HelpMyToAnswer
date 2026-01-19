import sounddevice as sd
import numpy as np
import wavio
import tempfile
import os
import queue

class AudioRecorder:
    def __init__(self, samplerate=44100, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self.recording = False
        self.audio_queue = queue.Queue()
        self.filename = os.path.join(tempfile.gettempdir(), "whisper_clip_recording.wav")

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, flush=True)
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.recording = True
        self.audio_queue = queue.Queue() # Clear queue
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            callback=self.callback
        )
        self.stream.start()

    def stop_recording(self):
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        self.recording = False
        
        # Collect all data from queue
        data = []
        while not self.audio_queue.empty():
            data.append(self.audio_queue.get())
        
        if not data:
            return None
            
        # Concatenate and save to wav
        recording = np.concatenate(data, axis=0)
        wavio.write(self.filename, recording, self.samplerate, sampwidth=2)
        
        return self.filename
