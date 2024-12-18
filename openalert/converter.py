import copy
import json

from sigma.collection import SigmaCollection
from sigma.backends.elasticsearch.elasticsearch_lucene import LuceneBackend

from logger import openalert_logger


# Extracted Constants
QUERY = "query"
BOOL = "bool"
FILTER = "filter"
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


    def add_to_query(self, source: list, section: dict, key: str) -> bool:
        """Helper to convert and add a section to an OpenSearch query."""
        result = self.convert_query(section)
        if not result:
            return False

        source.append(result[QUERY])
        return True


    def convert_rule(self, rule: dict) -> dict:
        """Convert one rule."""
        query = copy.deepcopy(pattern_query)
        # Convert Query Section
        if not self.add_to_query(query[QUERY][BOOL][FILTER], rule["query"], FILTER):
            return {}

        if 'fields' in rule:
            if 'includes' in rule['fields']:
                query[SOURCE][INCLUDES].extend(rule['fields']['includes'])
            if 'excludes' in rule['fields']:
                query[SOURCE][EXCLUDES].extend(rule['fields']['excludes'])

        # Convert Exceptions Section
        for exception in rule["exceptions"]:
            if not self.add_to_query(query[QUERY][BOOL][MUST_NOT], exception, MUST_NOT):
                return {}

        rule[OPEN_SEARCH_QUERY] = query
        return rule


    def convert_all_rules(self, rules: dict) -> dict:
        """Generate OpenSearch queries from rules."""
        for filename, current_rule in rules.copy().items():
            converted_rule = self.convert_rule(current_rule)
            if not converted_rule:
                openalert_logger.warning(fr'Skipping invalid rule syntax: Path={filename}')
                del rules[filename]
                continue

            rules[filename] = converted_rule
        return rules


    def convert_exception(self, exception: dict) -> dict:
        """Convert one exception."""
        query = copy.deepcopy(pattern_query)
        for exc in exception["exceptions"]:
            if not self.add_to_query(query[QUERY][BOOL][MUST_NOT], exc, MUST_NOT):
                return {}

        exception[OPEN_SEARCH_QUERY] = query
        return exception


    def convert_all_exceptions(self, exceptions: dict) -> dict:
        """Generate OpenSearch queries from exceptions."""
        for filename, current_exception in exceptions.copy().items():
            converted_exception = self.convert_exception(current_exception)
            if not converted_exception:
                openalert_logger.warning(fr'Skipping invalid exceptionList syntax: Path={filename}')
                del exceptions[filename]
                continue

            exceptions[filename] = converted_exception
        return exceptions
