import json
import sys
from pprint import pprint
import eql

class EQLSearch:
    def _create_events(self, data, timestamp_key) -> list:
        """
        Create EQL Events from the provided data.
        :param data: list of dictionaries to be transformed to EQL Events
        :param timestamp_key: name of the key-value pair to be used as timestamp
        :return: EQL Events
        """
        eql_events = list()

        # create EQL Events from 'data'
        for item in data:
            if "event" in item and "category" in item["event"]:
                event_type = item["event"]["category"]
            else:
                event_type = "generic"

            if timestamp_key in item:
                timestamp_value = item[timestamp_key]
            else:
                timestamp_value = 0

            eql_events.append(eql.Event(event_type, timestamp_value, item))
        
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


    def search(self, data, query, timestamp_key) -> list:
        """
        Perform a EQL search on the provided JSON or YAML data.
        :param data: list of dictionaries
        :param query: EQL search query
        :param timestamp_key: name of the key-value pair to be used as timestamp
        :return: the result of the search query as a list of dictionaries
        """

        # transform data into a list of EQL Event objects
        eql_events = self._create_events(data, timestamp_key)
 
        # execute the EQL query on the provided data
        search_result = self._execute_query(eql_events, query)
 
        return search_result


if __name__ == "__main__":
    eql_search = EQLSearch()
 
    with open('eql_data_sample.json', 'r') as json_data:
        data = json.load(json_data)
 
    query = r"""
        any where @timestamp >= "2021-08-31"
        """
    timestamp_key = "@timestamp"
    result = eql_search.search(data, query, timestamp_key)
    if result:
        print(json.dumps(result))
