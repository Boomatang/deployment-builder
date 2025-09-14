"""Test the configuration file stuff"""

import pytest

from deployment_builder.config import default_config, load_config, load_config_from_file, merge
from deployment_builder.keywords import (
    CLUSTERS,
    ENVIRONMENT,
    GENERAL,
    KIND_CONFIG_PATH,
    KUBECONFIG_PATH,
    MAX_WORKERS,
    NAME,
    PREFIX,
    SERVICES,
    VERSION,
)


@pytest.mark.unit
@pytest.mark.fast
def test_default_configuration():
    """Basic test to ensure the default config has the expected keys"""
    assert "general" in default_config
    assert "services" in default_config
    assert "clusters" in default_config

    general = default_config.get("general", {})

    assert "name" in general
    assert "version" in general
    assert "environment" in general
    assert "prefix" in general
    assert "kubeconfig_path" in general
    assert "kind_config_path" in general
    assert "max_workers" in general


testdata = [
    ({"k": "v"}, {"k": "bv"}, {"k": "bv"}),
    ({"k": "v"}, {"kb": "bv"}, {"k": "v", "kb": "bv"}),
    ({"k": "v", "n": {"a": 1}}, {"k": "bv", "n": {"a": 2}}, {"k": "bv", "n": {"a": 2}}),
]


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.parametrize("a,b,expected", testdata)
def test_merge(a, b, expected):
    """Basic testing on the merging of the configs"""
    r = merge(a, b)
    assert expected == r


testdata = [None, "does/not/exist.toml"]


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.parametrize("path", testdata)
def test_loading_raw_config_file_from_disc_fails(path):
    """Load a configration file from disc"""
    with pytest.raises(FileNotFoundError):
        _ = load_config(path)


@pytest.mark.unit
@pytest.mark.fast
def test_loading_raw_config_file_from_disc(temp_config_file):
    """Load a configration file from disc"""
    expected = {"general": {"name": "test", "max_workers": 1}}
    r = load_config(temp_config_file)
    assert r == expected


@pytest.mark.unit
@pytest.mark.fast
def test_loading_config_file(temp_config_file):
    """Load a configration using file from system and merging that with the defaults"""
    expected = {
        GENERAL: {
            NAME: "test",
            VERSION: "1.0.0",
            ENVIRONMENT: "development",
            PREFIX: "default",
            KUBECONFIG_PATH: "kubeconfigs",
            KIND_CONFIG_PATH: "kind-configs",
            MAX_WORKERS: 1,
        },
        SERVICES: {},
        CLUSTERS: {},
    }
    r = load_config_from_file(temp_config_file)
    assert r == expected
