import copy
import json
import sys

import eql

from converter import Converter, pattern_query, QUERY
from logger import openalert_logger
from opensearch_client import OpenSearchClient


class BaseEnhancement(object):
    """ Enhancements take a match dictionary object and modify it in some way to
    enhance an alert. These are specified in each rule under the match_enhancements option.
    Generally, the key value pairs in the match module will be contained in the alert body. """

    def __init__(self, client):
        self.client = client
        self.converter = Converter()

    def process(self, alerts, enhance_params):
        """ Modify the contents of match, a dictionary, in some way """
        raise NotImplementedError()


class EQLEnhancement(BaseEnhancement):
    """ Enhancements that modify the match dictionary based on the EQL query that was matched """
    DEFAULT_DATE_PATTERNS = ['%Y-%m-%dT%H:%M:%S.%fZ']
    DEFAULT_EVENT_TYPE = "event.category"
    DEFAULT_TIMESTAMP = "@timestamp"


    def _create_events(self, data, event_type_key, timestamp_key, date_patterns) -> list:
        """Create EQL Events from the provided data."""
        eql_events = list()

        # create EQL Events from 'data'
        for event_data in data:
            event_type = eql.utils.get_event_type(event_data, event_type_key)
            event_time = eql.utils.get_event_time(event_data, timestamp_key, date_patterns)
            eql_events.append(eql.Event(event_type, event_time, event_data))

        return eql_events


    def _execute_query(self, events, query) -> list:
        """Execute an EQL query on the provided events."""
        schema = eql.Schema.learn(events)

        query_result = []
        # this function is used to store the result of the query to 'query_result'
        def store_result(result):
            for event in result.events:
                query_result.append(event.data)

        engine = eql.PythonEngine()
        with schema:
            try:
                eql_query = eql.parse_query(query, implied_any=True, implied_base=True)
                engine.add_query(eql_query)
            except eql.EqlError as e:
                openalert_logger.debug(fr'EQL enhancer error: {e}')
                openalert_logger.debug(fr'EQL schema of events: {json.dumps(schema.schema)}')
                return []

            engine.add_output_hook(store_result)

        # execute the query
        engine.stream_events(events)

        return query_result


    def search(self, data, query, event_type_key=DEFAULT_EVENT_TYPE, timestamp_key=DEFAULT_TIMESTAMP,
               date_patterns=DEFAULT_DATE_PATTERNS) -> list:
        """Perform a EQL search on the provided JSON or YAML data."""
        eql_events = self._create_events(data, event_type_key, timestamp_key, date_patterns)

        # execute the EQL query on the provided data
        match_event = self._execute_query(eql_events, query)

        return match_event


    def process(self, events, enhance_params):
        # Execute ELQ query
        query = enhance_params.get('query', 'any where true')
        result = self.search(events, query)
        if not result:
            return []

        return result


class IndicatorMatchEnhancement(BaseEnhancement):
    """ Enhancements that modify the match dictionary based on the indicator that was matched """
    def get_nested_value(self, data, field_path):
        parts = field_path.split('.')
        val = data
        for p in parts:
            if p in val:
                val = val[p]
            else:
                return None
        return val


    def does_event_match_indicator(self, event, indicator, mapping):
        """Check if an event matches an indicator based on the mapping."""
        for group in mapping:
            is_group_matched = True
            for entry in group["entries"]:
                event_val = self.get_nested_value(event, entry["field"])
                indicator_val = self.get_nested_value(indicator,entry["value"])

                if event_val is None or indicator_val is None or event_val != indicator_val:
                    is_group_matched = False
                    break
            if is_group_matched:
                return True  # If one group matches (OR condition)
        return False


    def process(self, events, enhance_params):
        # Use match_all query if query section is empty
        query = enhance_params.get('query')
        if not query:
            query = { "query": { "match_all": {} } }
        else:
            # Generate OpenSearch query
            query = self.converter.convert_query(query)
            if not query:
                openalert_logger.error(fr'IndicatorMatchEnhancement: cannot convert query')

        # If fields exist in IndicatorMatch config
        fields = enhance_params.get('fields')
        if fields:
            tmp_query = copy.deepcopy(pattern_query)
            tmp_query[QUERY] = query['query']
            self.converter.add_source_require(tmp_query, fields)
            query = tmp_query

        # Get data from OpenSearch
        try:
            opensearch_data = self.client.search(index=','.join(enhance_params['index']), body=query)['hits']['hits']
        except Exception as e:
            openalert_logger.error(f"Cannot get data from OpenSearch. ERROR: {e}")
            return []

        # Build list indicators
        indicators = []
        for data in opensearch_data:
            if not data['_source']:
                continue
            indicators.append(data['_source'])

        if not indicators:
            return []

        # Check if event match indicator
        match_events = []
        for event in events:
            for indicator in indicators:
                if self.does_event_match_indicator(event, indicator, enhance_params['mapping']):
                    match_events.append(event)
                    break   # Stop checking other indicators for this event


        return match_events
