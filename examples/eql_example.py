import json
import sys
from pprint import pprint
import eql


DEFAULT_DATE_PATTERNS = ['%Y-%m-%dT%H:%M:%S.%fZ']
DEFAULT_EVENT_TYPE = "event.category"
DEFAULT_TIMESTAMP = "@timestamp"


class EQLSearch:
    def _create_events(self, data, event_type_key, timestamp_key, date_patterns) -> list:
        """
        Create EQL Events from the provided data.
        :param data: list of dictionaries to be transformed to EQL Events
        :param timestamp_key: name of the key-value pair to be used as timestamp
        :return: EQL Events
        """
        eql_events = list()

        # create EQL Events from 'data'
        for event_data in data:
            event_type = eql.utils.get_event_type(event_data, event_type_key)
            event_time = eql.utils.get_event_time(event_data, timestamp_key, date_patterns)

            eql_events.append(eql.Event(event_type, event_time, event_data))

        return eql_events


    def _execute_query(self, events, query) -> list:
        """
        Execute an EQL query on the provided events.
        :param events: events
        :param query: EQL query
        :return: the result of the query as a list of dictionaries or
        None when the query did not match the schema
        """
        schema = eql.Schema.learn(events)

        query_result = list()
 
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
                print(e, file=sys.stderr)
                pprint(schema.schema)
                return None

            engine.add_output_hook(store_result)
 
        # execute the query
        engine.stream_events(events)

        return query_result


    def search(self, data, query, event_type_key=DEFAULT_EVENT_TYPE, timestamp_key=DEFAULT_TIMESTAMP, date_patterns=DEFAULT_DATE_PATTERNS) -> list:
        """
        Perform a EQL search on the provided JSON or YAML data.
        :param data: list of dictionaries
        :param query: EQL search query
        :param timestamp_key: name of the key-value pair to be used as timestamp
        :return: the result of the search query as a list of dictionaries
        """

        # transform data into a list of EQL Event objects
        eql_events = self._create_events(data, event_type_key, timestamp_key, date_patterns)
 
        # execute the EQL query on the provided data
        search_result = self._execute_query(eql_events, query)
 
        return search_result


if __name__ == "__main__":
    eql_search = EQLSearch()
 
    with open('eql_data_sample.json', 'r') as json_data:
        data = json.load(json_data)
 
    query = r"""
        network where pid == 3
        """

    result = eql_search.search(data, query)
    if result:
        print(json.dumps(result))
