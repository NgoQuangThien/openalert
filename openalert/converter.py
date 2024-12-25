import copy

from sigma.collection import SigmaCollection
from sigma.backends.elasticsearch.elasticsearch_lucene import LuceneBackend

from logger import openalert_logger


# Extracted Constants
QUERY = "query"
BOOL = "bool"
FILTER = "filter"
MUST = "must"
MUST_NOT = "must_not"
SOURCE = "_source"
INCLUDES = "includes"
EXCLUDES = "excludes"
OPEN_SEARCH_QUERY = "OpenSearchQuery"

# Generic Sigma Rule (unchanged)
generic_sigma_rule = {
    "title": "Generic Sigma Rule",
    "id": "12345678-1234-1234-1234-123456789012",
    "description": "This is a generic Sigma rule",
    "logsource": {
        "category": "generic"
    },
    "detection": {}
}

pattern_query = {
    SOURCE: {INCLUDES: [], EXCLUDES: []},
    QUERY: {BOOL: {FILTER: [], MUST_NOT: []}}
}


class Converter(object):
    def __init__(self):
        pass


    @staticmethod
    def convert_query(section: dict) -> dict:
        """Convert query section of rule to filter section in OpenSearch query."""
        generic_sigma_rule["detection"] = section
        try:
            sigma_rule = SigmaCollection.from_dicts([generic_sigma_rule])
        except:
            return {}

        return LuceneBackend().convert(sigma_rule, output_format="dsl_lucene")[0]


    def add_to_query(self, source: list, section: dict) -> bool:
        """Helper to convert and add a section to an OpenSearch query."""
        result = self.convert_query(section)
        if not result:
            return False

        source.append(result[QUERY][BOOL][MUST][0])
        return True


    def add_source_require(self, query: dict, source: dict) -> dict:
        if 'includes' in source:
            query[SOURCE][INCLUDES].extend(source['includes'])
        if 'excludes' in source:
            query[SOURCE][EXCLUDES].extend(source['excludes'])


    def convert_rule(self, rule: dict) -> dict:
        """Convert one rule."""
        query = copy.deepcopy(pattern_query)
        # Convert Query Section
        if not self.add_to_query(query[QUERY][BOOL][FILTER], rule["query"]):
            return {}

        if 'fields' in rule:
            self.add_source_require(query, rule['fields'])

        # Convert Exceptions Section
        for exception in rule["exceptions"]:
            if not self.add_to_query(query[QUERY][BOOL][MUST_NOT], exception):
                return {}

        rule[OPEN_SEARCH_QUERY] = query
        return rule


    def convert_exception(self, exception: dict) -> dict:
        """Convert one exception."""
        query = copy.deepcopy(pattern_query)
        for exc in exception["exceptions"]:
            if not self.add_to_query(query[QUERY][BOOL][MUST_NOT], exc):
                return {}

        exception[OPEN_SEARCH_QUERY] = query
        return exception


    def convert_all(self, data:dict, data_type:str) -> dict:
        """Generate OpenSearch queries from rules/exceptionsList."""
        for key, value in data.copy().items():
            if data_type == 'rules':
                result = self.convert_rule(value)
            elif data_type == 'exceptionsList':
                result = self.convert_exception(value)
            else:
                result = {}

            if not result:
                openalert_logger.warning(fr'Skipping invalid {data_type} syntax: Path={key}')
                del data[key]
                continue

            data[key] = result
        return data
