import json
import re
from pathlib import Path


def test_README_JSON_EXAMPLES_PARSE_AND_INCLUDE_REQUIRED_BEHAVIORS():
    readme = (Path(__file__).parents[2] / "README.md").read_text()
    examples = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", readme, re.S)]

    responses = [example for example in examples if "edge" in example and "data_quality" in example]
    assert len(responses) >= 3
    assert any(
        response["data_quality"]["coverage"] == "none"
        and "options_flow" in response["data_quality"]["missing_families"]
        and any(
            "yfinance is private diagnostic only" in warning
            for warning in response["data_quality"]["warnings"]
        )
        for response in responses
    )
    assert any(
        response["edge"]["score"] == 50
        and response["edge"]["confidence"] == 0
        and response["data_quality"]["coverage"] == "none"
        and len(response["data_quality"]["missing_families"]) == 5
        for response in responses
    )
