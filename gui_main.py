import sys
import os
import time
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QLabel, QPushButton, QComboBox, QCheckBox, 
                             QTabWidget, QSplitter, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QAction

# Import our existing backend modules
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from history_manager import HistoryManager
import keyboard
import os 
import sys

log_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'debug_crash.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

def exception_hook(exctype, value, traceback):
    logging.critical("Uncaught exception", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)

sys.excepthook = exception_hook
log_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'debug_crash.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

def exception_hook(exctype, value, traceback):
    logging.critical("Uncaught exception", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)

sys.excepthook = exception_hook

class TranscriptionWorker(QThread):
    # Signals
    partial_result = pyqtSignal(str, str) # text, stability (h1, h3, h5)
    status_update = pyqtSignal(str)       # For status labels/logs, NOT transcript
    finished = pyqtSignal()

    def __init__(self, model_size="base", device="cpu", input_device_index=None, language=None):
        super().__init__()
        self.is_running = False
        self.input_device_index = input_device_index
        self.recorder = AudioRecorder(device_index=self.input_device_index)
        self.model_size = model_size
        self.device = device
        self.language = language
        self.transcriber = None # Lazy load

    def run(self):
        try:
            self.is_running = True
            
            # Initialize resources if needed
            if not self.transcriber:
                self.status_update.emit("Loading Model...")
                try:
                    self.transcriber = Transcriber(model_size=self.model_size, device=self.device)
                    self.status_update.emit("Model Loaded. Ready.")
                except Exception as e:
                    logging.error(f"Model load error: {e}")
                    self.status_update.emit(f"Error loading model: {e}")
                    return

            # Start recording
            try:
                self.recorder.start_recording()
                self.status_update.emit("Listening...")
            except Exception as e:
                 logging.error(f"Recording start error: {e}")
                 self.status_update.emit(f"Mic Error: {e}")
                 return
            
            while self.is_running:
                time.sleep(0.1)
                
            # Stop and Transcribe Final
            try:
                audio_path = self.recorder.stop_recording()
                if audio_path:
                    self.status_update.emit("Transcribing...")
                    # Update UI to show we are processing (optional visual cue in transcript if needed, but keeping clean for now)
                    text = self.transcriber.transcribe(audio_path, language=self.language)
                    if text:
                        self.partial_result.emit(text, "h5")
                        self.status_update.emit("Done.")
                    else:
                        self.status_update.emit("No speech detected.")
                else:
                    logging.warning("No audio path returned from stop_recording")
            except Exception as e:
                 logging.error(f"Transcribe/Stop error: {e}", exc_info=True)
                 self.status_update.emit(f"Error: {e}")
        
        except Exception as e:
            logging.critical(f"Worker thread crash: {e}", exc_info=True)
        finally:
            self.finished.emit()
            
    # ... rest of worker ...

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HelpMyToAnswer V2")
        self.resize(800, 700)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # Backend Worker
        self.worker = None
        self.is_recording = False
        self.history_manager = HistoryManager()
        
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 1. Top Panel (Toolbar)
        top_panel = QHBoxLayout()
        
        self.status_label = QLabel("■ STOP")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        # Audio Input Selection
        self.mic_combo = QComboBox()
        self.mic_combo.setToolTip("Select Microphone")
        self.mic_combo.addItem("Default Mic", None)
        # Populate devices
        try:
            devices = AudioRecorder.get_input_devices()
            for dev in devices:
                self.mic_combo.addItem(f"{dev['name']}", dev['index'])
        except:
            pass
            
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Tiny", "Base", "Small", "Medium"])
        self.model_combo.setCurrentText("Base")
        self.model_combo.setToolTip("Model Size (Small/Medium = Better Quality, Slower)")

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Auto", "UK", "EN", "RU"])
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Dictation (Online)", "Dictation (Offline)", "Screenshot (OCR)"])

        self.context_check = QCheckBox("Active Chat")

        top_panel.addWidget(self.status_label)
        top_panel.addWidget(QLabel("|")) 
        top_panel.addWidget(self.mic_combo)
        top_panel.addWidget(self.model_combo)
        top_panel.addWidget(self.lang_combo)
        top_panel.addWidget(self.mode_combo)
        top_panel.addStretch()
        top_panel.addWidget(self.context_check)
        
        main_layout.addLayout(top_panel)

        # 2. Middle Content (Splitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Live Transcript
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("LIVE TRANSCRIPT"))
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(True)
        self.transcript_area.setPlaceholderText("Press Start or Ctrl+Space to speak...")
        self.transcript_area.setStyleSheet("font-family: Consolas; font-size: 11pt;")
        left_layout.addWidget(self.transcript_area)
        
        # Right: Instructions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("INSTRUCTIONS"))
        self.instruction_area = QTextEdit()
        self.instruction_area.setPlaceholderText("e.g. 'Shorten this'...")
        right_layout.addWidget(self.instruction_area)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 200])
        
        main_layout.addWidget(splitter, stretch=1)

        # 3. Bottom Panel
        self.tabs = QTabWidget()
        self.tab_a = QTextEdit()
        self.tab_b = QTextEdit()
        self.tab_c = QTextEdit()
        
        # History Tab
        self.history_tab = QListWidget()
        self.history_tab.itemDoubleClicked.connect(self.on_history_item_double_clicked)
        
        self.tabs.addTab(self.tab_a, "Variant A (Formal)")
        self.tabs.addTab(self.tab_b, "Variant B (Casual)")
        self.tabs.addTab(self.tab_c, "Variant C (Short)")
        self.tabs.addTab(self.history_tab, "History")
        
        # Load History
        self.refresh_history_ui()
        
        main_layout.addWidget(self.tabs, stretch=1)

        # 4. Action Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_record = QPushButton("Start Recording (Ctrl+Space)")
        self.btn_record.clicked.connect(self.toggle_recording)
        
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.clicked.connect(self.copy_to_clipboard) # Simple copy
        
        btn_layout.addWidget(self.btn_record)
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addStretch()
        btn_layout.addWidget(QPushButton("Clear"))
        
        main_layout.addLayout(btn_layout)

        self.apply_styles()
        
        # Global Hotkey (using keyboard library in a non-blocking way if possible, or QShortcur)
        # Using QShortcut for local app focus, but user wants global.
        # We will use the existing keyboard lib hook but careful about threading.
        try:
            keyboard.add_hotkey('ctrl+space', self.remote_toggle_recording)
        except:
            pass # Handle gracefully if it fails

    def remote_toggle_recording(self):
        # Called from background thread by keyboard lib, need to bridge to UI thread
        # PyQT updates must happen on UI thread.
        # We can use a Signal here realistically, but for simplicity triggering click() might produce warning
        # signal logic is better.
        pass 

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.is_recording = True
        self.status_label.setText("● REC")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.btn_record.setText("Stop Recording (Ctrl+Space)")
        
        self.transcript_area.clear()
        
        # Get selected mic index
        selected_mic = self.mic_combo.currentData()
        
        # Get selected language
        lang_text = self.lang_combo.currentText()
        lang_map = {
            "Auto": None,
            "UK": "uk",
            "EN": "en",
            "RU": "ru"
        }
        selected_lang = lang_map.get(lang_text, None)
        
        # Get Model Size
        self.model_size = self.model_combo.currentText().lower()

        # Start Worker
        self.worker = TranscriptionWorker(model_size=self.model_size, device="cpu", input_device_index=selected_mic, language=selected_lang)
        self.worker.partial_result.connect(self.update_transcript)
        self.worker.status_update.connect(self.update_status) # New signal
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def update_status(self, msg):
        self.status_label.setText(msg)
        # Optional: Flash color if error
        if "Error" in msg:
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
             self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")

    def stop_recording(self):
        self.is_recording = False
        self.status_label.setText("■ STOP")
        self.status_label.setStyleSheet("color: white; font-weight: bold;")
        self.btn_record.setText("Start Recording (Ctrl+Space)")
        
        if self.worker:
            self.worker.stop()
            # We don't wait() here to avoid freezing UI, let functionality finish gracefully

    def on_worker_finished(self):
        self.worker = None
        # Save to history if we have text
        current_text = self.transcript_area.toPlainText().strip()
        if current_text:
             self.history_manager.add_entry(current_text)
             self.refresh_history_ui()
    
    def refresh_history_ui(self):
        self.history_tab.clear()
        entries = self.history_manager.get_history()
        for entry in entries:
            # Format: [Time] Snippet...
            snippet = (entry['text'][:50] + '...') if len(entry['text']) > 50 else entry['text']
            label = f"[{entry['timestamp']}] {snippet}"
            item = QListWidgetItem(label)
            item.setToolTip(entry['text']) # Full text on hover
            item.setData(Qt.ItemDataRole.UserRole, entry['text']) # Store full text
            self.history_tab.addItem(item)

    def on_history_item_double_clicked(self, item):
        full_text = item.data(Qt.ItemDataRole.UserRole)
        self.transcript_area.setText(full_text)
        self.update_status("Loaded from History")
        # Also switch to Variant A tab if needed, or just let user see it in transcript area
        # self.status_label.setText("Done")

    def copy_to_clipboard(self):
        text = self.transcript_area.toPlainText()
        QApplication.clipboard().setText(text)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QLabel { color: #e0e0e0; }
            QTextEdit { background-color: #3c3f41; color: #a9b7c6; border: 1px solid #5e6060; border-radius: 4px; }
            QPushButton { background-color: #4c5052; color: #ffffff; border: 1px solid #5e6060; padding: 5px; border-radius: 4px; }
            QPushButton:hover { background-color: #5f666b; }
            QTabWidget::pane { border: 1px solid #5e6060; }
            QTabBar::tab { background: #3c3f41; color: #a9b7c6; padding: 8px; }
            QTabBar::tab:selected { background: #4c5052; font-weight: bold; }
        """)

    def update_transcript(self, text, stability="final"):
        if stability == "h1":
            color = "#808080" # Grey
        elif stability == "h3":
            color = "#a0a0a0" # Darker Grey
        else:
            color = "#ffffff" # White
            
        cursor = self.transcript_area.textCursor()
        # For this simple log version, we append. In streaming reset, we would replace info.
        # Just appending with color for now
        html = f'<span style="color: {color};">{text} </span>'
        cursor.insertHtml(html)
        cursor.insertBlock() # New line for clarity in this version
        self.transcript_area.setTextCursor(cursor)
        self.transcript_area.ensureCursorVisible()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
