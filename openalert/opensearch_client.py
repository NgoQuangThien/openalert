import json

from opensearchpy import OpenSearch


class OpenSearchClient(OpenSearch):
    def __init__(self, config):
        super(OpenSearchClient, self).__init__(
            hosts=config['opensearch']['hosts'],
            http_compress=True,
            http_auth=(config['opensearch']['username'], config['opensearch']['password']),
            use_ssl=config['opensearch']['ssl']['enabled'],
            verify_certs=config['opensearch']['ssl'].get('verifyCerts', True),
            ca_certs=config['opensearch']['ssl'].get('certificateAuthorities', None),
            client_cert=config['opensearch']['ssl'].get('certificate', None),
            client_key=config['opensearch']['ssl'].get('key', None),
            ssl_show_warn=False,
            timeout=config['opensearch'].get('timeout', 30000),
        )
