# Danh sách chỉ mục
indices = ["cmccs-*", "cmccs-logs-*"]

# Danh sách truy vấn
queries = [
    {"query": {"match_all": {}}, "from": 0, "size": 1},
    {"query": {"match": {"field": "value"}}, "from": 10, "size": 5},
]

# Tạo msearch body
msearch_body = []
for query in queries:
    # Dòng metadata
    msearch_body.append({"index": indices})
    # Dòng truy vấn
    msearch_body.append(query)

print(msearch_body)