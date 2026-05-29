from datetime import date, datetime, timezone

from yieldfabric.core.output_store import OutputStore
from yieldfabric.utils.serialization import json_safe


def test_json_safe_converts_yaml_timestamp_datetime_to_iso_string():
    payload = {
        "input": {
            "expiry": datetime(2027, 1, 30, 0, 0, tzinfo=timezone.utc),
            "nested": [date(2027, 1, 31)],
        }
    }

    assert json_safe(payload) == {
        "input": {
            "expiry": "2027-01-30T00:00:00Z",
            "nested": ["2027-01-31"],
        }
    }


def test_output_store_expands_embedded_shell_substitution():
    store = OutputStore(debug=False)

    value = store.substitute("deposit-$(printf 123)")

    assert value == "deposit-123"
