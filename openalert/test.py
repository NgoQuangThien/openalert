events = [
    {
        "event_number": 1,
        "data_stream": {"type": "dns"},
        "source": {"ip": "1.1.1.1"},
        "destination": {"ip": "2.2.2.2"}
    },
    {
        "event_number": 2,
        "source": {"ip": "3.3.3.3"},
        "destination": {"ip": "4.4.4.4"}
    },
    {
        "event_number": 3,
        "data_stream": {"type": "http"},
        "destination": {"ip": "9.9.9.9"}
    }
]

indicators = [
    {
        "feed_type": "dns",
        "src_ip": "1.1.1.1",
        "dst_ip": "2.2.2.2",
        "malicious_score": 90
    },
    {
        "feed_type": "dns",
        "src_ip": "5.5.5.5",
        "dst_ip": "4.4.4.4",
        "malicious_score": 70
    },
    {
        "feed_type": "http",
        "dst_ip": "9.9.9.9",
        "malicious_score": 80
    }
]

mapping = [
    {
        "entries": [
            {"field": "data_stream.type", "value": "feed_type"},
            {"field": "source.ip", "value": "src_ip"}
        ]
    },
    {
        "entries": [
            {"field": "destination.ip", "value": "dst_ip"}
        ]
    }
]


def get_nested_value(data, field_path):
    """Lấy giá trị lồng nhau theo field_path, ví dụ "source.ip"."""
    parts = field_path.split('.')
    val = data
    for p in parts:
        if p in val:
            val = val[p]
        else:
            return None
    return val


def does_event_match_indicator(event, indicator, mapping):
    """Check if an event matches an indicator based on the mapping."""
    print(indicator)
    for group in mapping:
        is_group_matched = True
        for entry in group["entries"]:
            event_val = get_nested_value(event, entry["field"])
            indicator_val = indicator.get(entry["value"])
            if event_val is None or indicator_val is None or event_val != indicator_val:
                is_group_matched = False
                break
        if is_group_matched:
            return True  # If one group matches (OR condition)
    return False


alerts = []
for event in events:
    for indicator in indicators:
        if does_event_match_indicator(event, indicator, mapping):
            is_triggered = True
            alerts.append(event)
            break  # Stop checking other indicators for this event

print(alerts)