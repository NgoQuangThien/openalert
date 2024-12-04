import json

from elasticsearch_lucene import LuceneBackend
from sigma.elasticsearch_esql import ESQLBackend
from sigma.collection import SigmaCollection

# Instantiate backend, using our resolved pipeline
# and some backend parameter
lucene_backend = LuceneBackend()

rule = SigmaCollection.from_yaml(r"""
title: Run Whoami Showing Privileges
id: 14701da0-4b0f-4ee6-9c95-2ffb4e73bb9a
logsource:
    category: generic
detection:
    detection_1:
        - data_stream.type: "logs"
    detection_2:
        - data_stream.type: "metrics"
    condition: detection_1 and detection_2
""")                               

filter = SigmaCollection.from_yaml(r"""
title: Filter Out Administrator accounts
description: Filters out administrator accounts that start with adm_
id: d84c0ded-edd7-4123-80ed-348bb3ccc444
logsource:
    category: generic
filter:
    rules:
        - 14701da0-4b0f-4ee6-9c95-2ffb4e73bb9a
    filter_1:
        data_stream.dataset: "nginx.access"
    condition: filter_1
""")

filter2 = SigmaCollection.from_yaml(r"""
title: Filter Out Administrator accounts
description: Filters out administrator accounts that start with adm_
id: d84c0ded-edd7-4123-80ed-348bb3ccc444
logsource:
    category: generic
filter:
    rules:
        - 14701da0-4b0f-4ee6-9c95-2ffb4e73bb9a
    filter_1:
        data_stream.namespace: "default"
    condition: filter_1
""")

result = SigmaCollection.merge([rule, filter, filter2])

# Print converted rule ready for dsl syntax
dsl_lucene = lucene_backend.convert(result, output_format="dsl_lucene")[0]
print(json.dumps(dsl_lucene["query"], indent=2))

rule2 = SigmaCollection.from_yaml(r"""
title: Windows Failed Logon Event
name: failed_logon # Rule Reference
description: Detects failed logon events on Windows systems.
logsource:
    product: windows
    service: security
detection:
    selection:
        EventID: 4625
    condition: selection
---
title: Multiple failed logons for a single user (possible brute force attack)
correlation:
    type: event_count
    rules:
        - failed_logon # Referenced here
    group-by:
        - TargetUserName
        - TargetDomainName
    timespan: 5m
    condition:
        gte: 10
""")
esql_backend = ESQLBackend()
result = SigmaCollection.merge([rule2])
dsl_lucene = esql_backend.convert(result, output_format="default")[0]
print(json.dumps(dsl_lucene["query"], indent=2))