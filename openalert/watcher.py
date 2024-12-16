from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time


class Watcher(FileSystemEventHandler):
    def __init__(self, folder):
        self.watched_folder = folder


    def on_created(self, event):
        raise NotImplementedError


    def on_deleted(self, event):
        raise NotImplementedError


    def on_modified(self, event):
        raise NotImplementedError


folder_to_watch = '/Users/admin/DEV/openalert/examples/rules'
event_handler = Watcher(folder_to_watch)
observer = Observer()
observer.schedule(event_handler, folder_to_watch, recursive=True)

try:
    print(f"Start monitoring folder: {folder_to_watch}")
    observer.start()
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped monitoring.")
    observer.stop()
observer.join()