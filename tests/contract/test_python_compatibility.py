from pathlib import Path


def test_production_imports_are_python_310_compatible():
    package = Path(__file__).parents[2] / "catalyst_edge_mcp"
    offenders = [
        path.relative_to(package)
        for path in package.rglob("*.py")
        if "from datetime import UTC" in path.read_text()
    ]

    assert offenders == []
