import json
import sys

import eql

from logger import openalert_logger


class BaseEnhancement(object):
    """ Enhancements take a match dictionary object and modify it in some way to
    enhance an alert. These are specified in each rule under the match_enhancements option.
    Generally, the key value pairs in the match module will be contained in the alert body. """

    def __init__(self):
        pass

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
        search_result = self._execute_query(eql_events, query)

        return search_result


    def process(self, alerts, enhance_params):
        query = enhance_params.get('query', 'any where true')
        events = []

        # Extract match events from alerts
        for index, alert in enumerate(alerts):
            event = alert['event']['match']
            event['@index'] = index
            events.append(event)

        result = self.search(events, query)
        if not result:
            return []

        # Merge match event into alerts
        for event in result:
            for index, alert in enumerate(alerts):
                if event['@index'] == index:
                    alert['event']['match'] = event

        # Remove event not match in origin alerts
        alerts = [
            alert for alert in alerts
            if '@index' in alert['event']['match'] and alert['event']['match'].pop('@index', None) is not None
        ]

        return alerts


class IndicatorMatchEnhancement(BaseEnhancement):
    """ Enhancements that modify the match dictionary based on the indicator that was matched """
    def process(self, alerts, params):
        pass
