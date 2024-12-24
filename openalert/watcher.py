import json
import os

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

    def on_created(self, event):
        file_path = event.src_path
        rule = self.rules_loader.load(file_path)
        rule = self.executor.converter.convert_rule(rule)

        if rule:    # Load rule success
            if rule['enabled']:
                new_interval = interval_to_seconds(rule['schedule']['interval'])
                # Add to enabled rule
                self.executor.rules[file_path] = rule
                # Add to rules_group
                self.executor.add_rule_to_group(file_path, rule)
                # Create job for rules_groups if it's not exits
                self.executor.ensure_job_exists(new_interval)
                openalert_logger.info(fr'Rule created successfully: {file_path}')
            else:
                self.executor.disabled_rules[file_path] = rule
                openalert_logger.info(fr'Disabled rule created successfully: {file_path}')
        else:
            openalert_logger.info(fr'Failed to load rule {file_path}.')
        print(json.dumps(self.executor.rules))


    def on_modified(self, event):
        file_path = event.src_path
        if not os.path.exists(file_path):
            return

        rule = self.rules_loader.load(file_path)
        rule = self.executor.converter.convert_rule(rule)

        if not rule:
            openalert_logger.info(fr'Failed to load rule file: {file_path}')
            # Update file in enabled_rule
            if self.executor.rules.get(file_path, None):
                self.executor.remove_exits_rule_and_clean_job(file_path)
                return
            # Update file in disabled_rule
            elif self.executor.disabled_rules.get(file_path, None):
                self.executor.remove_disabled_rule(file_path)
                return
            # Update file not using
            else:
                return

        # Process event when rule load successfully
        if self.executor.rules.get(file_path, None):    # Modified enabled_rule
            old_rule = self.executor.rules.get(file_path)
            old_interval = interval_to_seconds(old_rule['schedule']['interval'])
            if rule['enabled']: # New rule is enabled_rule
                new_interval = interval_to_seconds(rule['schedule']['interval'])
                if old_interval != new_interval:    # Need change rule to other rules_group
                    # Delete old rule from rules_group
                    self.executor.remove_rule_from_group(file_path, old_interval)
                    # Check old rules_groups is empty
                    self.executor.clean_empty_interval_job(old_interval)
                    # Add new rule to rules_group
                    self.executor.add_rule_to_group(file_path, rule)
                    # Create new job for rules_group if not exist
                    self.executor.ensure_job_exists(new_interval)
                else:   # Just update rule detail
                    self.executor.grouped_rules[new_interval][file_path] = rule

            else:   # New rule change to disabled_rule
                self.executor.remove_exits_rule_and_clean_job(file_path)
                # Add rule to disabled_rule
                self.executor.disabled_rules[file_path] = rule

            openalert_logger.info(fr'Rule enable modified successfully: {file_path}')

        elif self.executor.disabled_rules.get(file_path, None):  # Modified disabled_rule
            if not rule['enabled']: # Just update rule detail
                self.executor.disabled_rules[file_path] = rule
            else:   # Rule change to enable
                new_interval = interval_to_seconds(rule['schedule']['interval'])
                # Add rule to list rule
                self.executor.rules[file_path] = rule
                # Add rule to rules_group
                self.executor.add_rule_to_group(file_path, rule)
                # Create new job for rules_group if not exist
                self.executor.ensure_job_exists(new_interval)
            openalert_logger.info(fr'Rule disable modified successfully: {file_path}')

        else:   # File is ignored
            if rule['enabled']:
                new_interval = interval_to_seconds(rule['schedule']['interval'])
                self.executor.rules[file_path] = rule
                self.executor.add_rule_to_group(file_path, rule)
                self.executor.ensure_job_exists(new_interval)
                openalert_logger.info(fr'Added new rule: {file_path}')
            else:
                self.executor.disabled_rules[file_path] = rule
                openalert_logger.info(fr'Added new disabled rule: {file_path}')

        print(json.dumps(self.executor.rules))


    def on_deleted(self, event):
        file_path = event.src_path
        if self.executor.rules.get(file_path, None):    # Remove enabled rule
            self.executor.remove_exits_rule_and_clean_job(file_path)
            openalert_logger.info(fr'Enable rule {file_path} removed successfully.')
        elif self.executor.disabled_rules.get(file_path, None): # Remove disabled rule
            self.executor.remove_disabled_rule(file_path)
            openalert_logger.info(fr'Disable rule {file_path} removed successfully.')
        print(json.dumps(self.executor.rules))


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