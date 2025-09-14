"""Shared pytest fixtures for deployment-builder tests."""

import json

import pytest
import yaml


@pytest.fixture(params=["config.toml", "config.yaml", "config.yml", "config.json"])
def temp_config_file(request, tmp_path):
    data = {"general": {"name": "test", "max_workers": 1}}
    filename = request.param
    filename_split = filename.split(".")
    if filename_split[1] == "toml":
        content = '[general]\nname = "test"\nmax_workers = 1'
    elif filename_split[1] in ["yaml", "yml"]:
        content = yaml.dump(data)
    elif filename_split[1] in ["json"]:
        content = json.dumps(data)
    temp_file = tmp_path / filename
    temp_file.write_text(content)
    return temp_file
