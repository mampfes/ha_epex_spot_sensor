import json
import re
from pathlib import Path


def test_manifest_required_fields():
    """Test that manifest.json contains all required fields for HA and HACS."""
    manifest_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "epex_spot_sensor"
        / "manifest.json"
    )

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    # Required keys for Home Assistant custom integrations
    required_keys = ["domain", "name", "version", "documentation", "issue_tracker"]

    for key in required_keys:
        assert key in manifest, f"Missing required key: {key}"

    # Required for HACS
    assert (
        "integration_type" in manifest
    ), "Missing required key for HACS: integration_type"

    # Validate types
    assert isinstance(manifest["domain"], str), "Domain must be a string"
    assert isinstance(manifest["name"], str), "Name must be a string"
    assert isinstance(manifest["version"], str), "Version must be a string"
    assert isinstance(manifest["documentation"], str), "Documentation must be a string"
    assert isinstance(manifest["issue_tracker"], str), "Issue tracker must be a string"
    assert isinstance(
        manifest["integration_type"], str
    ), "Integration type must be a string"

    # Validate URL formats (basic check for http/https)
    url_pattern = re.compile(r"^https?://")
    assert url_pattern.match(
        manifest["documentation"]
    ), f"Documentation URL invalid: {manifest['documentation']}"
    assert url_pattern.match(
        manifest["issue_tracker"]
    ), f"Issue tracker URL invalid: {manifest['issue_tracker']}"

    # Validate integration_type is valid for HACS
    valid_integration_types = [
        "integration",
        "device",
        "service",
        "helper",
        "netdaemon",
        "appdaemon",
    ]
    assert manifest["integration_type"] in valid_integration_types, (
        f"Invalid integration_type: {manifest['integration_type']}. "
        f"Must be one of {valid_integration_types}"
    )
