from labs.plugin_doctor.plugin_doctor import audit_source


def test_plugin_doctor_clean_read_tool_can_ship():
    report = audit_source(
        "generic",
        {
            "tools": [
                {
                    "name": "read_customer",
                    "description": "Read one customer record by its stable customer identifier.",
                    "input_schema": {
                        "type": "object",
                        "properties": {"customer_id": {"type": "string"}},
                        "required": ["customer_id"],
                    },
                    "annotations": {"readOnlyHint": True},
                }
            ]
        },
        namespace="test",
    )
    assert report["state"] == "SHIP"
    assert report["score"] == 100


def test_plugin_doctor_unknown_tool_is_blocked():
    report = audit_source(
        "generic",
        {
            "tools": [
                {
                    "name": "process",
                    "description": "Process the requested object using the configured behavior.",
                    "input_schema": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                    },
                }
            ]
        },
        namespace="test",
    )
    assert report["state"] == "BLOCKED"
    assert any(f["code"] == "PD-S001" for f in report["findings"])


def test_plugin_doctor_missing_metadata_is_blocked():
    report = audit_source(
        "generic",
        {"tools": [{"name": "mystery"}]},
        namespace="test",
    )
    codes = {f["code"] for f in report["findings"]}
    assert report["state"] == "BLOCKED"
    assert {"PD-D001", "PD-Q001", "PD-S001"} <= codes


def test_plugin_doctor_high_impact_tool_is_fix_not_auto_block():
    report = audit_source(
        "generic",
        {
            "tools": [
                {
                    "name": "delete_customer",
                    "description": "Delete exactly one customer record using its stable customer identifier.",
                    "input_schema": {
                        "type": "object",
                        "properties": {"customer_id": {"type": "string"}},
                        "required": ["customer_id"],
                    },
                    "annotations": {"destructiveHint": True},
                }
            ]
        },
        namespace="test",
    )
    assert report["state"] == "FIX"
    assert any(f["code"] == "PD-R001" for f in report["findings"])
