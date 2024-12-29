import os
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from logger import openalert_logger
from ultils import interval_to_seconds
from loader import Loader, RULES_SCHEMA_PATH, EXCEPTIONS_SCHEMA_PATH


YAML_PATTERNS = ['*.yaml', '*.yml']


class Watcher(PatternMatchingEventHandler):
    def __init__(self, directory, executor):
        super().__init__(patterns=YAML_PATTERNS, ignore_directories=True, case_sensitive=True)
        self.directory = directory
        self.executor = executor
        self.observer = Observer()
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

    def on_created(self, event):
        file_path = event.src_path
        loaded_rule = self.rules_loader.load(file_path)
        if not loaded_rule or self.rules_loader.is_duplicate_entry(loaded_rule, self.executor.rules):
            openalert_logger.info(fr'Failed to load rule: {file_path}')
            return

        self.process_rule(file_path, loaded_rule, is_new=True)

    def on_modified(self, event):
        file_path = event.src_path
        if not os.path.exists(file_path):
            return

        loaded_rule = self.rules_loader.load(file_path)
        if not loaded_rule:
            openalert_logger.info(fr'Failed to load rule: {file_path}')
            self.remove_rule(file_path)
            return

        self.process_rule(file_path, loaded_rule, is_new=False)

    def on_deleted(self, event):
        file_path = event.src_path
        self.remove_rule(file_path)

    def process_rule(self, file_path, rule, is_new):
        if not rule:
            self.remove_rule(file_path)
            return

        if rule['enabled']:
            rule = self.executor.converter.convert_rule(rule)
            if not rule:
                return
            self.enable_rule(file_path, rule, is_new)
        else:
            self.disable_rule(file_path, rule, is_new)

    def enable_rule(self, file_path, rule, is_new):
        new_interval = interval_to_seconds(rule['schedule']['interval'])
        old_rule = self.executor.rules.get(file_path, None)
        old_interval = interval_to_seconds(old_rule['schedule']['interval']) if old_rule else None

        if old_rule and old_interval != new_interval:  # Move to a new rule group
            self.executor.remove_rule_from_group(file_path, old_interval)
            self.executor.clean_empty_interval_job(old_interval)

        self.executor.rules[file_path] = rule
        self.executor.add_rule_to_group(file_path, rule)
        self.executor.ensure_job_exists(new_interval)
        action = "Modified" if not is_new else "Added"
        openalert_logger.info(fr'{action} enabled rule: {file_path}')

    def disable_rule(self, file_path, rule, is_new):
        if file_path in self.executor.rules:  # Remove existing enabled rule
            self.executor.remove_exits_rule_and_clean_job(file_path)

        self.executor.disabled_rules[file_path] = rule
        action = "Modified" if not is_new else "Added"
        openalert_logger.info(fr'{action} disabled rule: {file_path}')

    def remove_rule(self, file_path):
        if file_path in self.executor.rules:
            self.executor.remove_exits_rule_and_clean_job(file_path)
            openalert_logger.info(fr'Removed enable_rule: {file_path}')
        elif file_path in self.executor.disabled_rules:
            self.executor.remove_disabled_rule(file_path)
            openalert_logger.info(fr'Removed disable_rule: {file_path}')


class ExceptionsWatcher(Watcher):
    def __init__(self, directory, executor):
        super().__init__(directory, executor)
        self.exceptions_loader = Loader(EXCEPTIONS_SCHEMA_PATH)

    def on_created(self, event):
        self.process_exception(event.src_path, is_deleted=False)

    def on_modified(self, event):
        self.process_exception(event.src_path, is_deleted=False)

    def on_deleted(self, event):
        self.process_exception(event.src_path, is_deleted=True)


    def process_exception(self, file_path, is_deleted):
        if is_deleted:
            if self.executor.remove_exception(file_path):
                openalert_logger.info(fr'Deleted exception: {file_path}')
            return

        exception = self.exceptions_loader.load(file_path)
        if not exception:
            openalert_logger.warning(f'Invalid exception: {file_path}')
            return

        converted_exception = self.executor.converter.convert_exception(exception)
        if not converted_exception:
            openalert_logger.info(fr'Failed to load exception: {file_path}')
            self.executor.remove_exception(file_path)
            return

        if file_path not in self.executor.exceptions:
            if self.exceptions_loader.is_duplicate_entry(converted_exception, self.executor.exceptions):
                openalert_logger.info(fr'Duplicate exception: {file_path}')
                return
            self.executor.add_exception(file_path, converted_exception)
            action = "Added"
        else:
            self.executor.update_exception(file_path, converted_exception)
            action = "Updated"

        openalert_logger.info(fr'{action} exception: {file_path}')
