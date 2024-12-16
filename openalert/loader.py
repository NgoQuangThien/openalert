import os
from jsonschema import validate

from ultils import  read_yaml
from logger import openalert_logger


def get_all_files(folder):
    files = list()
    try:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                files.append(file_path)
    except Exception as e:
        openalert_logger.error(f'Error accessing folder {folder}: {e}')

    return files


class Loader(object):
    def __init__(self, folder, schema_path):
        self.folder = folder
        self.schema = read_yaml(schema_path)


    def validate_schema(self, file_content) -> bool:
        """Validate schema of the file."""
        try:
            if 'date' in file_content:
                file_content['date'] = file_content['date'].strftime('%Y-%m-%d')
            if 'modified' in file_content:
                file_content['modified'] = file_content['modified'].strftime('%Y-%m-%d')

            validate(file_content, self.schema)
        except Exception as e:
            openalert_logger.error(f'Error validating schema: {e}')
            return False

        return True


    def load(self, file_path) -> dict:
        """Load content from a file."""
        try:
            data = read_yaml(file_path)
        except Exception as e:
            openalert_logger.error(f'Error reading file {file_path}: {e}')
            return dict()

        if not self.validate_schema(data):
            openalert_logger.warning('Cannot load the file, ignoring it: ' + file_path)
            return dict()

        return data


    def load_all(self):
        """Load all files from a folder."""
        raise NotImplemented


class RulesLoader(Loader):
    def __init__(self, folder, schema_path):
        super().__init__(folder, schema_path)
        self.rules = dict()


    def load_all(self) -> dict:
        if not os.path.isdir(self.folder):
            raise Exception(f'{self.folder} is not a directory.')

        for file in get_all_files(self.folder):
            if file.endswith(('.yml', '.yaml')):
                openalert_logger.info(f'Loading file: {file}')
                rule_content = self.load(file)
                if rule_content:
                    self.rules[file] = rule_content

        return self.rules


class ExceptionsLoader(Loader):
    def __init__(self, folder, schema_path):
        super().__init__(folder, schema_path)
        self.exceptions = dict()

    def load_all(self) -> dict:
        if not os.path.isdir(self.folder):
            raise Exception(f'{self.folder} is not a directory.')

        for file in get_all_files(self.folder):
            if file.endswith('.yml'):
                openalert_logger.info(f'Loading file: {file}')
                rule_content = self.load(file)
                if rule_content:
                    self.exceptions[file] = rule_content

        return self.exceptions


# rule_folder = 'D:/DEV/Python/openalert/examples/rules/'
# rule_loader = RulesLoader(rule_folder, os.path.join(os.path.dirname(__file__),'schema/rule-schema.json'))
# rules = rule_loader.load_all()
# print(rules)
#
# exception_folder = 'D:/DEV/Python/openalert/examples/exceptions/'
# exception_loader = RulesLoader(rule_folder, os.path.join(os.path.dirname(__file__),'schema/rule-schema.json'))
# exceptions = exception_loader.load_all()
# print(exceptions)