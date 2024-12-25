import os
from jsonschema import validate

from ultils import  read_yaml
from logger import openalert_logger


YAML_EXTENSIONS = ('.yml', '.yaml')
DATE_FIELDS = ['date', 'modified']

WORK_DIR = os.path.dirname(__file__)
RULES_SCHEMA_PATH = os.path.join(WORK_DIR, 'schema/rule-schema.json')
EXCEPTIONS_SCHEMA_PATH = os.path.join(WORK_DIR, 'schema/exception-schema.json')


class Loader(object):
    def __init__(self, schema_path):
        self.schema = read_yaml(schema_path)
        self.total = 0
        self.enabled = 0
        self.disabled = 0


    @staticmethod
    def get_all_files(directory):
        """Get all files in a directory."""
        files_path = []
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    files_path.append(file_path)
        except Exception as e:
            openalert_logger.error(f'Error accessing directory {directory}: {e}')

        return files_path


    @staticmethod
    def is_duplicate_entry(content, content_dicts):
        """Check if an entry with the same ID or name already exists."""
        entry_id = content.get('id')
        entry_name = content.get('name')
        return any([
            entry_id in {c.get('id') for c in content_dicts.values()},
            entry_name in {c.get('name') for c in content_dicts.values()},
        ])


    def is_schema_valid(self, file_content) -> bool:
        """Check if the file content matches the schema."""
        def format_date_fields(fields):
            """Format specified fields in the file content to 'YYYY-MM-DD'."""
            for field in fields:
                if field in file_content:
                    file_content[field] = file_content[field].strftime('%Y-%m-%d')

        try:
            format_date_fields(DATE_FIELDS)
            validate(file_content, self.schema)
        except Exception:  # noqa: Avoid generic exception if possible
            return False

        return True


    def load(self, file_path) -> dict:
        """Load content from a file."""
        try:
            data = read_yaml(file_path)
        except Exception as e:
            openalert_logger.error(f'Error reading file {file_path}: {e}')
            return {}

        if not self.is_schema_valid(data):
            openalert_logger.debug(f'Invalid schema for file {file_path}')
            return {}

        return data


    def load_all(self):
        """Load all files from a directory and process it."""
        raise NotImplemented


class RulesLoader(Loader):
    def __init__(self, directory, schema_path):
        super().__init__(schema_path)
        self.directory = directory
        self.rules = {}
        self.disabled_rules = {}


    def load_all(self):
        """Load all rules from a directory."""
        if not os.path.isdir(self.directory):
            raise Exception(f'{self.directory} is not a directory.')

        for file_path in self.get_all_files(self.directory):
            if not file_path.endswith(YAML_EXTENSIONS):
                continue

            openalert_logger.debug(f'Loading file: {file_path}')
            rule_content = self.load(file_path)

            if not rule_content or self.is_duplicate_entry(rule_content, {**self.rules, **self.disabled_rules}):
                openalert_logger.warning(f'Skipping invalid/duplicate rule: Path={file_path}')
                continue

            self.total += 1

            if rule_content.get('enabled', True):
                self.rules[file_path] = rule_content
                self.enabled += 1
            else:
                self.disabled_rules[file_path] = rule_content
                self.disabled += 1

        openalert_logger.info(f'Rule loading is complete. Enabled: {self.enabled}, Disabled: {self.disabled},'
                              f'Total: {self.total}')

        return self.rules, self.disabled_rules


class ExceptionsLoader(Loader):
    def __init__(self, directory, schema_path):
        super().__init__(schema_path)
        self.directory = directory
        self.exceptions = {}


    def load_all(self) -> dict:
        """Load all exceptions from a directory."""
        if not os.path.isdir(self.directory):
            raise Exception(f'{self.directory} is not a directory.')

        for file_path in self.get_all_files(self.directory):
            if not file_path.endswith(YAML_EXTENSIONS):
                continue

            openalert_logger.debug(f'Loading file: {file_path}')
            exception_content = self.load(file_path)

            if not exception_content or self.is_duplicate_entry(exception_content, {**self.exceptions}):
                openalert_logger.debug(f'Skipping duplicate exception: Path={file_path}')
                continue

            self.total += 1

            self.exceptions[file_path] = exception_content
            self.enabled += 1

        openalert_logger.info(f'Exception loading is complete. Total: {self.total}')

        return self.exceptions
