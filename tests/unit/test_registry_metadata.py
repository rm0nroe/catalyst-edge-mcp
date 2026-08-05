import json
from importlib.metadata import version
from pathlib import Path

from catalyst_edge_mcp import __version__

ROOT = Path(__file__).parents[2]
MCP_NAME = "io.github.rm0nroe/catalyst-edge-mcp"


def test_registry_metadata_matches_package():
    payload = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    package = payload["packages"][0]
    package_version = version("catalyst-edge-mcp")

    assert __version__ == package_version

    assert payload["name"] == MCP_NAME
    assert payload["title"] == "Catalyst Edge Research"
    assert payload["description"].startswith("Source-linked market intelligence")
    assert payload["websiteUrl"] == "https://catalyst-edge-mcp.vercel.app"
    assert payload["icons"] == [
        {
            "src": "https://catalyst-edge-mcp.vercel.app/favicon.svg",
            "mimeType": "image/svg+xml",
            "sizes": ["any"],
        }
    ]
    assert payload["version"] == package_version
    assert package["registryType"] == "pypi"
    assert package["identifier"] == "catalyst-edge-mcp"
    assert package["version"] == package_version
    assert package["transport"] == {"type": "stdio"}
    sec_identity = next(
        item
        for item in package["environmentVariables"]
        if item["name"] == "CATALYST_EDGE_SEC_USER_AGENT"
    )
    assert sec_identity["isRequired"] is True
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"<!-- mcp-name: {MCP_NAME} -->" in readme
    assert readme.startswith("# CATALYST/EDGE\n")
