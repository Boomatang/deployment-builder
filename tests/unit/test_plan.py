"""test the creation of a plan"""

import time

import pytest

from deployment_builder.plan import Plan


class MockEngine:
    def __init__(self):
        self.name = "mock"


@pytest.mark.slow
@pytest.mark.unit
def test_get_cluster_queue(simple_config):
    """Get the mp queue for the creation of the cluster"""
    expected = ["test-one", "test-two-1", "test-two-2", "test-three-1", "test-three-2", "test-three-3"]

    plan = Plan(simple_config, MockEngine())

    queue = plan.cluster_queue()
    assert queue.qsize() == len(expected)
    clusters = []
    # NOTE: test becomes flaky with out the sleep
    time.sleep(0.5)
    while not queue.empty():
        r = queue.get()
        clusters.append(r.name)

    assert clusters == expected


@pytest.mark.unit
def test_get_cluster_names(simple_config):
    """Get the list names of the clusters in the plan"""
    expected = ["test-one", "test-two-1", "test-two-2", "test-three-1", "test-three-2", "test-three-3"]
    plan = Plan(simple_config, MockEngine())
    names = plan.cluster_names()
    assert names == expected


@pytest.mark.unit
def test_get_cluster_count(simple_config):
    """Get the count of the clusters in the plan"""
    expected = 6
    plan = Plan(simple_config, MockEngine())
    names = plan.cluster_count()
    assert names == expected


@pytest.mark.slow
@pytest.mark.unit
def test_get_services_queue(simple_config):
    """Get the mp queue for the creation of the cluster"""
    c1 = "kind-test-one"
    c2a = "kind-test-two-1"
    c2b = "kind-test-two-2"
    c3a = "kind-test-three-1"
    c3b = "kind-test-three-2"
    c3c = "kind-test-three-3"
    s1 = "base"
    s2 = "l1"
    s3 = "l2a"
    s4 = "l3a"
    s5 = "l2b"
    s6 = "l3b"
    s7 = "l3c"
    expected = [
        (s1, c1),
        (s1, c2a),
        (s1, c2b),
        (s1, c3a),
        (s1, c3b),
        (s1, c3c),
        (s2, c1),
        (s3, c2a),
        (s3, c2b),
        (s4, c3a),
        (s4, c3b),
        (s4, c3c),
        (s5, c2a),
        (s5, c2b),
        (s6, c3a),
        (s6, c3b),
        (s6, c3c),
        (s7, c3a),
        (s7, c3b),
        (s7, c3c),
    ]

    plan = Plan(simple_config, MockEngine())

    queue = plan.services_queue()
    assert queue.qsize() == len(expected)
    clusters = []
    # NOTE: test becomes flaky with out the sleep
    time.sleep(0.5)
    while not queue.empty():
        r = queue.get()
        clusters.append((r.name, r.context))

    assert clusters == expected
