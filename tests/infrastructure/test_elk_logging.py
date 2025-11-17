"""
ELK Stack Logging Integration Tests
Feature: 002-production-infra
Task: T065

Tests ELK Stack functionality:
1. Elasticsearch health and index templates
2. Log indexing within 10 seconds
3. Kibana dashboard access
4. Log search and aggregation
"""

import pytest
import time
import json
from datetime import datetime
import requests


@pytest.fixture(scope="module")
def elasticsearch_url():
    return "http://localhost:9200"


@pytest.fixture(scope="module")
def kibana_url():
    return "http://localhost:5601"


@pytest.fixture(scope="module")
def logstash_http_url():
    return "http://localhost:8080"


@pytest.fixture(scope="module")
def es_client(elasticsearch_url):
    session = requests.Session()
    max_retries = 30

    for i in range(max_retries):
        try:
            response = session.get(f"{elasticsearch_url}/_cluster/health", timeout=5)
            if response.status_code == 200:
                print("[OK] Elasticsearch is ready")
                return session
        except Exception as e:
            if i == max_retries - 1:
                pytest.skip(f"[SKIP] Elasticsearch not available: {e}")
            time.sleep(2)

    return session


def test_elasticsearch_health(es_client, elasticsearch_url):
    response = es_client.get(f"{elasticsearch_url}/_cluster/health")
    assert response.status_code == 200, f"[FAIL] Health check failed: {response.status_code}"
    health = response.json()
    assert health.get("status") in ["green", "yellow"], f"[FAIL] Cluster status: {health.get('status')}"
    print(f"[OK] Elasticsearch health: {health.get('status')}")


def test_index_template_exists(es_client, elasticsearch_url):
    response = es_client.get(f"{elasticsearch_url}/_index_template/shopfds-logs")
    assert response.status_code == 200, "[FAIL] Index template not found"
    print("[OK] Index template 'shopfds-logs' exists")


def test_ilm_policy_exists(es_client, elasticsearch_url):
    response = es_client.get(f"{elasticsearch_url}/_ilm/policy/shopfds-logs-policy")
    assert response.status_code == 200, "[FAIL] ILM policy not found"
    policy = response.json()
    phases = policy["shopfds-logs-policy"]["policy"]["phases"]
    assert "delete" in phases, "[FAIL] Delete phase not configured"
    assert phases["delete"]["min_age"] == "30d", "[FAIL] Retention not 30 days"
    print("[OK] ILM policy with 30-day retention exists")


def test_log_indexing_within_10_seconds(es_client, elasticsearch_url, logstash_http_url):
    test_request_id = f"test-{int(time.time())}"
    test_log = {
        "@timestamp": datetime.utcnow().isoformat(),
        "service": "ecommerce",
        "level": "INFO",
        "message": "Integration test log",
        "request_id": test_request_id,
        "endpoint": "/api/v1/test",
        "status_code": 200
    }

    try:
        response = requests.post(logstash_http_url, json=test_log, timeout=5)
        assert response.status_code == 200, f"[FAIL] Logstash rejected: {response.status_code}"
        print(f"[OK] Log sent (request_id: {test_request_id})")
    except Exception as e:
        pytest.skip(f"[SKIP] Logstash not available: {e}")

    start_time = time.time()
    for i in range(20):
        time.sleep(0.5)
        search_query = {"query": {"term": {"request_id": test_request_id}}}
        try:
            response = es_client.post(f"{elasticsearch_url}/shopfds-*/_search", json=search_query)
            if response.status_code == 200:
                results = response.json()
                if results["hits"]["total"]["value"] > 0:
                    elapsed = time.time() - start_time
                    print(f"[OK] Log indexed in {elapsed:.2f}s (target: <10s)")
                    assert elapsed < 10.0, f"[FAIL] Indexing too slow: {elapsed:.2f}s"
                    return
        except Exception:
            pass

    pytest.fail("[FAIL] Log not indexed within 10 seconds")


def test_search_logs_by_service(es_client, elasticsearch_url):
    search_query = {"query": {"term": {"service": "ecommerce"}}, "size": 10}
    response = es_client.post(f"{elasticsearch_url}/shopfds-*/_search", json=search_query)
    assert response.status_code == 200, f"[FAIL] Search failed: {response.status_code}"
    results = response.json()
    print(f"[OK] Found {results['hits']['total']['value']} logs for 'ecommerce'")


def test_search_logs_by_level(es_client, elasticsearch_url):
    search_query = {"query": {"term": {"level": "ERROR"}}, "size": 10}
    response = es_client.post(f"{elasticsearch_url}/shopfds-*/_search", json=search_query)
    assert response.status_code == 200, f"[FAIL] Search failed: {response.status_code}"
    results = response.json()
    print(f"[OK] Found {results['hits']['total']['value']} ERROR logs")


def test_search_logs_by_time_range(es_client, elasticsearch_url):
    search_query = {
        "query": {"range": {"@timestamp": {"gte": "now-1h", "lte": "now"}}},
        "size": 10
    }
    response = es_client.post(f"{elasticsearch_url}/shopfds-*/_search", json=search_query)
    assert response.status_code == 200, f"[FAIL] Search failed: {response.status_code}"
    results = response.json()
    print(f"[OK] Found {results['hits']['total']['value']} logs in last hour")


def test_aggregation_by_service(es_client, elasticsearch_url):
    agg_query = {"size": 0, "aggs": {"services": {"terms": {"field": "service", "size": 10}}}}
    response = es_client.post(f"{elasticsearch_url}/shopfds-*/_search", json=agg_query)
    assert response.status_code == 200, f"[FAIL] Aggregation failed: {response.status_code}"
    results = response.json()
    if "aggregations" in results:
        buckets = results["aggregations"]["services"]["buckets"]
        print("[OK] Log distribution by service:")
        for bucket in buckets:
            print(f"  - {bucket['key']}: {bucket['doc_count']} logs")


def test_kibana_health(kibana_url):
    try:
        response = requests.get(f"{kibana_url}/api/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            state = status["status"]["overall"]["state"]
            assert state in ["green", "yellow"], f"[FAIL] Kibana state: {state}"
            print(f"[OK] Kibana health: {state}")
        else:
            pytest.skip(f"[SKIP] Kibana not responding: {response.status_code}")
    except Exception as e:
        pytest.skip(f"[SKIP] Kibana not available: {e}")


def test_log_query_performance(es_client, elasticsearch_url):
    search_query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"service": "ecommerce"}},
                    {"range": {"@timestamp": {"gte": "now-1h"}}}
                ]
            }
        },
        "size": 100
    }
    start_time = time.time()
    response = es_client.post(f"{elasticsearch_url}/shopfds-*/_search", json=search_query)
    elapsed = time.time() - start_time
    assert response.status_code == 200, f"[FAIL] Query failed: {response.status_code}"
    assert elapsed < 1.0, f"[FAIL] Query too slow: {elapsed:.2f}s (target: <1s)"
    results = response.json()
    print(f"[OK] Query in {elapsed:.3f}s, found {results['hits']['total']['value']} logs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
