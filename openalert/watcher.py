import json

import watchdog.events
import watchdog.observers
from watchdog.events import FileSystemEvent, DirCreatedEvent, FileCreatedEvent

from loader import Loader, RULES_SCHEMA_PATH, EXCEPTIONS_SCHEMA_PATH
from ultils import interval_to_seconds
from logger import openalert_logger

yaml_patterns = ['*.yaml', '*.yml']


class Watcher(watchdog.events.PatternMatchingEventHandler):
    def __init__(self, directory, executor):
        watchdog.events.PatternMatchingEventHandler.__init__(self, patterns=yaml_patterns,
                                                             ignore_directories=True, case_sensitive=True)
        self.directory = directory
        self.executor = executor
        self.observer = watchdog.observers.Observer()
        self.observer.schedule(self, self.directory, recursive=False)


    def start(self):
        self.observer.start()


    def stop(self):
        self.observer.stop()
        self.observer.join()


class RulesWatcher(Watcher):
    def __init__(self, directory, executor):
        super().__init__(directory, executor)
        self.rules_loader = Loader(RULES_SCHEMA_PATH)
        self.exceptions_loader = Loader(EXCEPTIONS_SCHEMA_PATH)


    def add_or_update_rule(self, file_path, rule):
        old_rule = self.executor.rules.get(file_path, None)
        self.executor.rules[file_path] = rule
        new_interval = interval_to_seconds(rule['schedule']['interval'])

        # Rule file is update
        if old_rule is not None:
            old_interval = interval_to_seconds(old_rule['schedule']['interval'])
            # Interval changed
            if new_interval != old_interval:
                # Delete old rule from rules_groups of old_interval
                self.executor.remove_rule_from_group(file_path, old_interval)
                # Add rule to execut
                if rule['enabled']:
                    # Add new rule to rules_groups of new interval
                    self.executor.add_rule_to_group(file_path, rule)
                    # Check old rules_groups is empty
                    self.executor.clean_empty_interval_job(old_interval)
                    # Create job for rules_groups of new rule if it not exits
                    self.executor.ensure_job_exists(new_interval)
                else:
                    self.executor.disabled_rules[file_path] = rule
            else:
                self.executor.grouped_rules[new_interval][file_path] = rule

        # New rule file
        else:
            self.executor.add_rule_to_group(file_path, rule)


    def add_or_update_disabled_rule(self, file_path, rule):
        old_rule = self.executor.disabled_rules.get(file_path, None)
        self.executor.disabled_rules[file_path] = rule


    def handle_change(self, file_path):
        rule = self.rules_loader.load(file_path)
        rule = self.executor.converter.convert_rule(rule)

        # Load rule success
        if rule:
            if file_path in self.executor.rules:
                self.add_or_update_rule(file_path, rule)
            elif file_path in self.executor.disabled_rules:
                self.add_or_update_disabled_rule(file_path, rule)
        # Load rule fail
        else:
            openalert_logger.info(fr'Failed to load rule {file_path}.')
            if file_path in self.executor.rules:
                self.executor.remove_rule_and_clean_empty_interval_job(file_path)
            elif file_path in self.executor.disabled_rules:
                self.executor.remove_disabled_rule(file_path)


    def on_created(self, event):
        file_path = event.src_path
        rule = self.rules_loader.load(file_path)
        rule = self.executor.converter.convert_rule(rule)

        if rule:    # Load rule success
            if rule['enabled']:
                # Add to enabled rule
                self.executor.rules[file_path] = rule
                # Add to rules_group
                self.executor.add_rule_to_group(file_path, rule)
                # Create job for rules_groups if it's not exits
                self.executor.ensure_job_exists(interval_to_seconds(rule['schedule']['interval']))
            else:
                self.executor.disabled_rules[file_path] = rule
        else:
            openalert_logger.info(fr'Failed to load rule {file_path}.')


    def on_modified(self, event):
        file_path = event.src_path
        rule = self.rules_loader.load(file_path)
        rule = self.executor.converter.convert_rule(rule)

        if self.executor.rules.get(file_path, None):    # Modified enabled_rule
            old_rule = self.executor.rules.get(file_path)
            old_interval = interval_to_seconds(old_rule['schedule']['interval'])
            new_interval = interval_to_seconds(rule['schedule']['interval'])
            if rule['enabled']: # New rule is enabled_rule
                if old_interval != new_interval:
                    # Delete old rule from rules_group
                    self.executor.remove_rule_from_group(file_path, old_interval)
                    # Check old rules_groups is empty
                    self.executor.clean_empty_interval_job(old_interval)
                    # Add new rule to rules_group
                    self.executor.add_rule_to_group(file_path, rule)
                    # Create new rules_group if not exist
                    self.executor.ensure_job_exists(new_interval)
                else:
                    self.executor.grouped_rules[new_interval][file_path] = rule

            else:   # New rule change to disabled_rule
                # Remove rule from enabled_rule
                self.executor.remove_rule(file_path)
                # Remove rule from rules_group
                self.executor.remove_rule_from_group(file_path, old_interval)
                # Check old rules_groups is empty
                self.executor.clean_empty_interval_job(old_interval)
                # Add rule to disabled_rule
                self.executor.disabled_rules[file_path] = rule

        elif self.executor.disabled_rules.get(file_path, None):  # Modified disabled_rule
            if not rule['enabled']:
                self.executor.disabled_rules[file_path] = rule
            else:
                pass

        else:   # File is ignored
            pass



    def on_deleted(self, event):
        pass


    def on_any_event(self, event: FileSystemEvent):
        if event.event_type in ['created', 'modified']:
            self.handle_change(event.src_path)

        elif event.event_type == 'deleted':
            # Delete disabled rule
            if event.src_path in self.executor.disabled_rules:
                if self.executor.remove_disabled_rule(event.src_path):
                    openalert_logger.info(fr'Rule {event.src_path} is deleted from disabled rule.')
            # Delete rule
            elif event.src_path in self.executor.rules:
                if self.executor.remove_rule_and_clean_empty_interval_job(event.src_path):
                    openalert_logger.info(fr'Rule {event.src_path} is deleted from rule.')


class ExceptionsWatcher(Watcher):
    def __init__(self, directory, executor):
        super().__init__(directory, executor)
        self.exceptions_loader = Loader(EXCEPTIONS_SCHEMA_PATH)


    def add_or_update_exception(self, file_path, exception):
        old_exception = self.executor.exceptions.get(file_path, None)
        self.executor.exceptions[file_path] = exception


    def handle_change(self, file_path):
        exception = self.exceptions_loader.load(file_path)
        exception = self.executor.converter.convert_exception(exception)
        if exception:
            self.add_or_update_exception(file_path, exception)
        else:
            self.executor.remove_rule(file_path)


    def on_any_event(self, event: FileSystemEvent):
        if event.event_type in ['created', 'modified']:
            self.handle_change(event.src_path)
        elif event.event_type == 'deleted':
            self.executor.remove_rule(event.src_path)