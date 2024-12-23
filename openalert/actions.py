import json
from logger import openalert_logger, debug_action_logger
from opensearchpy import helpers


class Action(object):
    def __init__(self):
        pass
    def send(self, alerts=None, config=None):
        raise NotImplementedError


class DebugAction(Action):
    def __init__(self):
        super().__init__()

    def send(self, alerts=None, config=None):
        for alert in alerts:
            debug_action_logger.debug(json.dumps(alert))


class IndexerAction(Action):
    def __init__(self):
        super().__init__()

    @staticmethod
    def _build_document(alert, index):
        """Build a single document."""
        return {
            '_op_type': 'create',
            '_index': index,
            '_source': alert
        }

    def _build_documents(self, alerts, index):
        """Build a list of documents for indexing."""
        return [self._build_document(alert, index) for alert in alerts]


    def send(self, alerts=None, config=None):
        """Send bulk-indexed documents to OpenSearch."""
        try:
            index = config['index']
            documents = self._build_documents(alerts, index)
            response = helpers.bulk(config['client'], documents)
            # openalert_logger.info(f'Indexed {response[0]} alerts')
            return response
        except Exception as e:
            openalert_logger.error(f'Error indexing alerts: {e}')
            return None


class EmailAction(Action):
    def __init__(self):
        super().__init__()


    def send(self, alerts=None, config=None):
        pass