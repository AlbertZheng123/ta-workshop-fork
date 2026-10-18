"""Validate small agent/tool contracts before advancing the workflow."""


def require_implementation(value: dict) -> dict:
    """Reject model error objects and missing edits or summaries."""
    if (not isinstance(value, dict)
            or not isinstance(value.get("edits"), list)
            or not value["edits"]
            or not isinstance(value.get("summary"), str)
            or not value["summary"].strip()):
        raise ValueError("Developer must return edits and a non-empty summary")
    return value


def require_tests(value: dict) -> dict:
    """Require explicit booleans instead of trusting truthy error strings."""
    if (not isinstance(value, dict)
            or type(value.get("passed")) is not bool
            or not isinstance(value.get("output"), str)
            or type(value.get("feature_tests_present")) is not bool):
        raise ValueError("QA returned an invalid result")
    return value
