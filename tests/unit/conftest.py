"""Shared pytest fixtures for deployment-builder tests."""

import json

import pytest
import yaml

from deployment_builder.keywords import CLUSTERS, COUNT, ENABLE, GENERAL, MAX_WORKERS, PREFIX, SERVICES


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


@pytest.fixture()
def simple_config():
    return {
        CLUSTERS: {
            "one": {
                ENABLE: True,
                SERVICES: {
                    "l1": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n kube-system"},
                },
            },
            "two": {
                COUNT: 2,
                SERVICES: {
                    "l2a": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n kube-system"},
                    "l2b": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n kube-system"},
                },
            },
            "three": {
                COUNT: 3,
                SERVICES: {
                    "l3a": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n kube-system"},
                    "l3b": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n kube-system"},
                    "l3c": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n kube-system"},
                },
            },
        },
        GENERAL: {MAX_WORKERS: 2, PREFIX: "test"},
        SERVICES: {
            "base": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n kube-system"},
        },
    }
