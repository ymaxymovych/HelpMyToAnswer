import pyperclip
import threading
from plyer import notification

def copy_to_clipboard(text):
    pyperclip.copy(text)

def notify_user(title, message):
    # Run notification in a separate thread to not block main execution
    def _notify():
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="HelpMyToAnswer",
                timeout=3
            )
        except Exception as e:
            print(f"Notification error: {e}")
            
    threading.Thread(target=_notify).start()
