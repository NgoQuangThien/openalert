import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Any

from ultils import interval_to_seconds


class RuleManager(object):
    def __init__(self, rules, disabled_rules, exceptions):
        self.rules = rules
        self.disabled_rules = disabled_rules
        self.exceptions = exceptions

        # grouped_rules: { interval: { filename: rule_dict } }
        self.grouped_rules: Dict[int, Dict[str, Dict[str, Any]]] = {}

        # Load initial
        self.load_initial_rules()


    def load_initial_rules(self):
        """Load initial rules group."""
        for filename in self.rules.keys():
            self.add_rule_to_group(filename, self.rules[filename])


    def add_rule_to_group(self, filename: str, rule: Dict[str, Any]):
        """Add a rule to the interval group."""
        interval = interval_to_seconds(rule['schedule']['interval'])
        if interval not in self.grouped_rules:
            self.grouped_rules[interval] = {}

        self.grouped_rules[interval][filename] = rule


    def remove_rule_from_group(self, filename: str, interval: int):
        """Remove a rule from the interval group."""
        if interval in self.grouped_rules and filename in self.grouped_rules[interval]:
            del self.grouped_rules[interval][filename]


    def add_rule(self, filename):
        pass


    def get_rules(self):
        pass


    def update_rules(self):
        pass


    def remove_rule(self, filename):
        pass


class Watcher(FileSystemEventHandler):
    def __init__(self, directory, manager: RuleManager):
        self.watched_dir = directory
        self.manager = manager


    def on_created(self, event):
        raise NotImplementedError


    def on_deleted(self, event):
        raise NotImplementedError


    def on_modified(self, event):
        raise NotImplementedError


class RuleFileHandler(Watcher):
    pass


class ExceptionFileHandler(Watcher):
    pass

# folder_to_watch = '/Users/admin/DEV/openalert/examples/rules'
# event_handler = Watcher(folder_to_watch)
# observer = Observer()
# observer.schedule(event_handler, folder_to_watch, recursive=True)
#
# try:
#     print(f"Start monitoring folder: {folder_to_watch}")
#     observer.start()
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     print("Stopped monitoring.")
#     observer.stop()
# observer.join()