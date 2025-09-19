from datetime import datetime


def log_time(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
