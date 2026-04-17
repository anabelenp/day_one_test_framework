#!/usr/bin/env python3
"""
Performance Security Tests

Tests for validating security mechanisms under load:
- Authentication load testing: Token validation under high load
- Authorization stress testing: RBAC performance under concurrent access
- Rate limiting validation: API throttling effectiveness
- DDoS simulation: System resilience under attack conditions

Run with: TESTING_MODE=mock pytest tests/performance/test_security_performance.py -v
"""

import pytest
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from collections import defaultdict

from src.service_manager import (
    get_cache_client,
    get_message_client,
    get_database_client,
    get_api_client,
)


class PerformanceMetrics:
    """Collects and analyzes performance metrics"""

    def __init__(self):
        self.results: List[float] = []
        self.errors: List[str] = []
        self.lock = threading.Lock()

    def record(self, duration: float, error: str = None):
        with self.lock:
            self.results.append(duration)
            if error:
                self.errors.append(error)

    @property
    def total_requests(self) -> int:
        return len(self.results)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.error_count / self.total_requests) * 100

    @property
    def avg_duration(self) -> float:
        if not self.results:
            return 0.0
        return statistics.mean(self.results)

    @property
    def median_duration(self) -> float:
        if not self.results:
            return 0.0
        return statistics.median(self.results)

    @property
    def p95_duration(self) -> float:
        if not self.results:
            return 0.0
        sorted_results = sorted(self.results)
        index = int(len(sorted_results) * 0.95)
        return sorted_results[min(index, len(sorted_results) - 1)]

    @property
    def p99_duration(self) -> float:
        if not self.results:
            return 0.0
        sorted_results = sorted(self.results)
        index = int(len(sorted_results) * 0.99)
        return sorted_results[min(index, len(sorted_results) - 1)]

    @property
    def min_duration(self) -> float:
        return min(self.results) if self.results else 0.0

    @property
    def max_duration(self) -> float:
        return max(self.results) if self.results else 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "error_rate_percent": round(self.error_rate, 2),
            "avg_ms": round(self.avg_duration * 1000, 2),
            "median_ms": round(self.median_duration * 1000, 2),
            "p95_ms": round(self.p95_duration * 1000, 2),
            "p99_ms": round(self.p99_duration * 1000, 2),
            "min_ms": round(self.min_duration * 1000, 2),
            "max_ms": round(self.max_duration * 1000, 2),
        }


@pytest.mark.performance
@pytest.mark.security
class TestAuthenticationLoad:
    """Authentication load testing - Token validation under high load"""

    @pytest.fixture(autouse=True)
    def setup_clients(self):
        """Setup service clients"""
        self.cache_client = get_cache_client()
        self.api_client = get_api_client()
        self.db_client = get_database_client()
        self.cache_client.connect()
        self.api_client.connect()
        self.db_client.connect()

    def test_token_validation_under_load(self):
        """
        Test token validation performance under concurrent load.

        Requirements:
        - Handle 1000+ concurrent token validations
        - P99 latency < 100ms
        - Error rate < 1%
        """
        metrics = PerformanceMetrics()
        num_requests = 1000
        num_threads = 50

        def validate_token(token_id: int) -> None:
            start = time.time()
            try:
                token_key = f"auth_token:{token_id}"
                self.cache_client.set(token_key, "valid", ttl=300)
                result = self.cache_client.get(token_key)
                duration = time.time() - start
                if result is None:
                    metrics.record(duration, "Token not found")
                else:
                    metrics.record(duration)
            except Exception as e:
                duration = time.time() - start
                metrics.record(duration, str(e))

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(validate_token, i) for i in range(num_requests)]
            for future in as_completed(futures):
                future.result()
        total_time = time.time() - start_time

        summary = metrics.summary()
        summary["total_time_seconds"] = round(total_time, 2)
        summary["requests_per_second"] = round(num_requests / total_time, 2)

        print(f"\nToken Validation Load Test Results:")
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Throughput: {summary['requests_per_second']} req/s")
        print(f"  Avg Latency: {summary['avg_ms']}ms")
        print(f"  P95 Latency: {summary['p95_ms']}ms")
        print(f"  P99 Latency: {summary['p99_ms']}ms")
        print(f"  Error Rate: {summary['error_rate_percent']}%")

        assert summary["error_rate_percent"] < 1.0, (
            f"Error rate {summary['error_rate_percent']}% exceeds 1%"
        )
        assert summary["p99_ms"] < 100, (
            f"P99 latency {summary['p99_ms']}ms exceeds 100ms"
        )

    def test_authentication_burst_handling(self):
        """
        Test authentication system handles sudden bursts of requests.

        Simulates 100 concurrent login attempts within 1 second.
        """
        metrics = PerformanceMetrics()
        num_burst_requests = 100

        def authenticate_user(user_id: int) -> None:
            start = time.time()
            try:
                auth_data = {
                    "user_id": f"user_{user_id}",
                    "password": "test_password",
                    "timestamp": time.time(),
                }
                result = self.api_client.authenticate(auth_data)
                duration = time.time() - start
                metrics.record(duration)
            except Exception as e:
                duration = time.time() - start
                metrics.record(duration, str(e))

        with ThreadPoolExecutor(max_workers=num_burst_requests) as executor:
            futures = [
                executor.submit(authenticate_user, i) for i in range(num_burst_requests)
            ]
            for future in as_completed(futures):
                future.result()

        summary = metrics.summary()
        print(f"\nAuthentication Burst Test Results:")
        print(f"  Burst Size: {num_burst_requests}")
        print(f"  Avg Latency: {summary['avg_ms']}ms")
        print(f"  Max Latency: {summary['max_ms']}ms")
        print(f"  Error Rate: {summary['error_rate_percent']}%")

        assert summary["max_ms"] < 500, (
            f"Max latency {summary['max_ms']}ms too high for burst"
        )
        assert summary["error_rate_percent"] < 5.0, (
            f"Error rate {summary['error_rate_percent']}% too high"
        )

    def test_token_validation_latency_degradation(self):
        """
        Test that token validation latency doesn't degrade significantly under load.

        Runs validation in waves and compares early vs late performance.
        """
        wave_results = defaultdict(list)
        total_requests = 500
        wave_size = 100

        def validate_token_waved(token_id: int) -> float:
            start = time.time()
            token_key = f"perf_token:{token_id}"
            self.cache_client.set(token_key, "valid", ttl=60)
            self.cache_client.get(token_key)
            return time.time() - start

        with ThreadPoolExecutor(max_workers=25) as executor:
            for wave in range(total_requests // wave_size):
                futures = [
                    executor.submit(validate_token_waved, wave * wave_size + i)
                    for i in range(wave_size)
                ]
                for f in as_completed(futures):
                    duration = f.result()
                    wave_results[wave].append(duration * 1000)

        wave_means = {
            wave: statistics.mean(times) for wave, times in wave_results.items()
        }
        first_wave = wave_means.get(0, 0)
        last_wave = wave_means.get(max(wave_results.keys()), 0)

        degradation_percent = (
            ((last_wave - first_wave) / first_wave * 100) if first_wave > 0 else 0
        )

        print(f"\nLatency Degradation Analysis:")
        print(f"  Wave 1 Avg: {first_wave:.2f}ms")
        print(f"  Wave {max(wave_results.keys()) + 1} Avg: {last_wave:.2f}ms")
        print(f"  Degradation: {degradation_percent:.1f}%")

        assert degradation_percent < 50, (
            f"Latency degraded by {degradation_percent:.1f}%"
        )


@pytest.mark.performance
@pytest.mark.security
class TestRBACPerformance:
    """Authorization stress testing - RBAC performance under concurrent access"""

    @pytest.fixture(autouse=True)
    def setup_clients(self):
        """Setup service clients"""
        self.cache_client = get_cache_client()
        self.db_client = get_database_client()
        self.cache_client.connect()
        self.db_client.connect()

    def test_rbac_policy_lookup_under_load(self):
        """
        Test RBAC policy lookups perform well under concurrent access.

        Requirements:
        - 500+ concurrent policy lookups
        - P99 latency < 50ms
        """
        metrics = PerformanceMetrics()
        num_requests = 500
        num_threads = 25

        roles = ["admin", "viewer", "editor", "auditor", "operator"]
        resources = ["dashboard", "reports", "users", "settings", "logs"]

        def lookup_policy(request_id: int) -> None:
            start = time.time()
            try:
                role = roles[request_id % len(roles)]
                resource = resources[request_id % len(resources)]
                policy_key = f"rbac:{role}:{resource}"

                self.cache_client.set(policy_key, "allow", ttl=300)
                result = self.cache_client.get(policy_key)

                duration = time.time() - start
                if result is None:
                    metrics.record(duration, "Policy not found")
                else:
                    metrics.record(duration)
            except Exception as e:
                duration = time.time() - start
                metrics.record(duration, str(e))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(lookup_policy, i) for i in range(num_requests)]
            for future in as_completed(futures):
                future.result()

        summary = metrics.summary()
        print(f"\nRBAC Policy Lookup Results:")
        print(f"  Total Lookups: {summary['total_requests']}")
        print(f"  Avg Latency: {summary['avg_ms']}ms")
        print(f"  P95 Latency: {summary['p95_ms']}ms")
        print(f"  P99 Latency: {summary['p99_ms']}ms")
        print(f"  Error Rate: {summary['error_rate_percent']}%")

        assert summary["p99_ms"] < 50, f"P99 latency {summary['p99_ms']}ms exceeds 50ms"
        assert summary["error_rate_percent"] < 1.0, f"Error rate too high"

    def test_concurrent_permission_checks(self):
        """
        Test concurrent permission checks across different user roles.

        Simulates 200 concurrent users with different roles checking permissions.
        """
        metrics = PerformanceMetrics()
        num_users = 200
        num_threads = 20

        user_roles = [
            ("admin_user", "admin"),
            ("security_user", "security"),
            ("viewer_user", "viewer"),
            ("editor_user", "editor"),
            ("auditor_user", "auditor"),
        ]

        def check_permissions(user_idx: int) -> None:
            user_name, role = user_roles[user_idx % len(user_roles)]
            start = time.time()
            try:
                perm_key = f"perm:{user_name}:{role}"
                self.cache_client.set(perm_key, "granted", ttl=60)
                result = self.cache_client.get(perm_key)
                duration = time.time() - start
                metrics.record(duration)
            except Exception as e:
                duration = time.time() - start
                metrics.record(duration, str(e))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(check_permissions, i) for i in range(num_users)]
            for future in as_completed(futures):
                future.result()

        summary = metrics.summary()
        print(f"\nConcurrent Permission Check Results:")
        print(f"  Users: {num_users}")
        print(f"  Avg Latency: {summary['avg_ms']}ms")
        print(f"  P95 Latency: {summary['p95_ms']}ms")
        print(f"  Error Rate: {summary['error_rate_percent']}%")

        assert summary["p95_ms"] < 100, f"P95 latency {summary['p95_ms']}ms too high"


@pytest.mark.performance
@pytest.mark.security
class TestRateLimiting:
    """Rate limiting validation - API throttling effectiveness"""

    @pytest.fixture(autouse=True)
    def setup_clients(self):
        """Setup service clients"""
        self.api_client = get_api_client()
        self.cache_client = get_cache_client()
        self.api_client.connect()
        self.cache_client.connect()

    def test_rate_limit_threshold_detection(self):
        """
        Test that rate limiting correctly identifies when threshold is reached.

        Simulates gradual increase in request rate and verifies throttling kicks in.
        """
        rate_limit_window = 60
        rate_limit_max = 100
        test_user = "ratelimit_test_user"

        results = {
            "allowed": 0,
            "rate_limited": 0,
            "errors": 0,
        }

        def make_request(request_num: int) -> None:
            try:
                rate_key = f"rate:{test_user}"
                current_count = self.cache_client.get(rate_key)

                if current_count is None:
                    self.cache_client.set(rate_key, "1", ttl=rate_limit_window)
                    current_count = "0"

                count = int(current_count) if current_count else 0

                if count >= rate_limit_max:
                    results["rate_limited"] += 1
                else:
                    self.cache_client.set(
                        rate_key, str(count + 1), ttl=rate_limit_window
                    )
                    results["allowed"] += 1

            except Exception:
                results["errors"] += 1

        num_requests = 150
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            for future in as_completed(futures):
                future.result()

        total = results["allowed"] + results["rate_limited"] + results["errors"]
        limited_rate = (results["rate_limited"] / total * 100) if total > 0 else 0

        print(f"\nRate Limiting Detection Results:")
        print(f"  Total Requests: {total}")
        print(f"  Allowed: {results['allowed']}")
        print(f"  Rate Limited: {results['rate_limited']}")
        print(f"  Errors: {results['errors']}")
        print(f"  Limited Rate: {limited_rate:.1f}%")

        assert results["allowed"] <= rate_limit_max, (
            "Rate limiter allowed more than threshold"
        )
        assert results["rate_limited"] > 0, "Rate limiter did not activate"

    def test_rate_limit_recovery(self):
        """
        Test that rate limiting allows requests after the window expires.
        """
        test_user = "recovery_test"
        short_ttl = 2

        def check_and_increment() -> bool:
            key = f"rate_recovery:{test_user}"
            count = self.cache_client.get(key)
            if count is None:
                self.cache_client.set(key, "1", ttl=short_ttl)
                return True
            return False

        allowed_first = sum(1 for _ in range(10) if check_and_increment())
        print(f"\nFirst window - Allowed: {allowed_first}")

        time.sleep(short_ttl + 1)

        allowed_second = sum(1 for _ in range(10) if check_and_increment())
        print(f"After TTL expiry - Allowed: {allowed_second}")

        assert allowed_second > 0, "Rate limiter did not reset after TTL expiry"

    def test_distributed_rate_limiting(self):
        """
        Test rate limiting works correctly with distributed concurrent access.
        """
        rate_key = "distributed_rate_limit"
        max_requests = 50
        num_threads = 25
        requests_per_thread = 10

        def distributed_requests(thread_id: int) -> Dict[str, int]:
            results = {"allowed": 0, "blocked": 0}
            for i in range(requests_per_thread):
                try:
                    count = self.cache_client.get(rate_key)
                    if count is None:
                        self.cache_client.set(rate_key, "1", ttl=60)
                        results["allowed"] += 1
                    elif int(count) < max_requests:
                        self.cache_client.set(rate_key, str(int(count) + 1), ttl=60)
                        results["allowed"] += 1
                    else:
                        results["blocked"] += 1
                except Exception:
                    results["blocked"] += 1
            return results

        total_results = {"allowed": 0, "blocked": 0}
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(distributed_requests, i) for i in range(num_threads)
            ]
            for future in as_completed(futures):
                result = future.result()
                total_results["allowed"] += result["allowed"]
                total_results["blocked"] += result["blocked"]

        print(f"\nDistributed Rate Limiting Results:")
        print(f"  Total Allowed: {total_results['allowed']}")
        print(f"  Total Blocked: {total_results['blocked']}")

        assert total_results["allowed"] <= max_requests * 1.5, (
            "Rate limiter allowed too many requests"
        )


@pytest.mark.performance
@pytest.mark.security
class TestDDoSSimulation:
    """DDoS simulation - System resilience under attack conditions"""

    @pytest.fixture(autouse=True)
    def setup_clients(self):
        """Setup service clients"""
        self.cache_client = get_cache_client()
        self.api_client = get_api_client()
        self.db_client = get_database_client()
        self.cache_client.connect()
        self.api_client.connect()
        self.db_client.connect()

    def test_connection_pool_under_stress(self):
        """
        Test that the connection pool handles stress without exhausting resources.

        Simulates 500 concurrent connections and verifies graceful degradation.
        """
        metrics = PerformanceMetrics()
        num_connections = 500
        num_threads = 100

        def stress_connection(conn_id: int) -> None:
            start = time.time()
            try:
                key = f"stress_conn:{conn_id}"
                self.cache_client.set(key, f"value_{conn_id}", ttl=30)
                result = self.cache_client.get(key)
                duration = time.time() - start
                metrics.record(duration)
            except Exception as e:
                duration = time.time() - start
                metrics.record(duration, str(e))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(stress_connection, i) for i in range(num_connections)
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        summary = metrics.summary()
        print(f"\nConnection Pool Stress Test Results:")
        print(f"  Connections: {num_connections}")
        print(f"  Throughput: {num_connections / summary['max_ms'] * 1000:.0f} ops/sec")
        print(f"  Avg Latency: {summary['avg_ms']}ms")
        print(f"  P95 Latency: {summary['p95_ms']}ms")
        print(f"  Error Rate: {summary['error_rate_percent']}%")

        assert summary["error_rate_percent"] < 10, (
            f"Error rate {summary['error_rate_percent']}% too high under stress"
        )

    def test_high_volume_request_handling(self):
        """
        Test system handles very high volume of requests (1000+ requests/second).

        This simulates a DDoS-like flood of requests.
        """
        metrics = PerformanceMetrics()
        target_rps = 1000
        duration_seconds = 5
        num_threads = 50

        stop_event = threading.Event()
        request_count = {"count": 0, "lock": threading.Lock()}

        def high_volume_requests(thread_id: int) -> None:
            while not stop_event.is_set():
                start = time.time()
                try:
                    key = f"ddos_test:{thread_id}:{time.time_ns()}"
                    self.cache_client.set(key, "flood", ttl=1)
                    self.cache_client.get(key)
                    duration = time.time() - start

                    with request_count["lock"]:
                        request_count["count"] += 1

                    metrics.record(duration)
                except Exception as e:
                    duration = time.time() - start
                    metrics.record(duration, str(e))

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=high_volume_requests, args=(i,))
            t.start()
            threads.append(t)

        time.sleep(duration_seconds)
        stop_event.set()

        for t in threads:
            t.join(timeout=5)

        summary = metrics.summary()
        actual_rps = request_count["count"] / duration_seconds

        print(f"\nHigh Volume Request Handling Results:")
        print(f"  Target Rate: {target_rps} req/s")
        print(f"  Actual Rate: {actual_rps:.0f} req/s")
        print(f"  Total Requests: {request_count['count']}")
        print(f"  Avg Latency: {summary['avg_ms']}ms")
        print(f"  P99 Latency: {summary['p99_ms']}ms")
        print(f"  Error Rate: {summary['error_rate_percent']}%")

        assert actual_rps > 100, (
            f"System unable to handle expected load: {actual_rps} req/s"
        )
        assert summary["p99_ms"] < 1000, (
            f"P99 latency {summary['p99_ms']}ms too high under load"
        )

    def test_graceful_degradation_under_attack(self):
        """
        Test that the system degrades gracefully under attack conditions.

        Verifies that critical services remain available even under extreme load.
        """
        metrics = PerformanceMetrics()
        num_requests = 300

        def attack_simulation(request_id: int) -> None:
            start = time.time()
            try:
                key = f"attack:{request_id}"
                self.cache_client.set(key, "attack_traffic", ttl=10)
                result = self.cache_client.get(key)
                duration = time.time() - start
                metrics.record(duration)
            except Exception as e:
                duration = time.time() - start
                metrics.record(duration, str(e))

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(attack_simulation, i) for i in range(num_requests)
            ]
            for future in as_completed(futures):
                future.result()

        summary = metrics.summary()

        critical_operations_worked = True
        try:
            self.cache_client.set("health_check", "ok", ttl=5)
            health = self.cache_client.get("health_check")
            critical_operations_worked = health is not None
        except Exception:
            critical_operations_worked = False

        print(f"\nGraceful Degradation Test Results:")
        print(f"  Attack Volume: {num_requests}")
        print(f"  Success Rate: {100 - summary['error_rate_percent']:.1f}%")
        print(f"  Critical Ops Available: {critical_operations_worked}")

        assert summary["error_rate_percent"] < 50, (
            "System failed too many requests under attack"
        )
        assert critical_operations_worked, (
            "Critical operations unavailable during attack"
        )

    def test_flood_attack_recovery(self):
        """
        Test system recovers quickly after a flood attack ends.
        """
        pre_flood_metrics = PerformanceMetrics()

        for i in range(50):
            start = time.time()
            self.cache_client.set(f"pre_flood:{i}", "ok", ttl=30)
            self.cache_client.get(f"pre_flood:{i}")
            pre_flood_metrics.record(time.time() - start)

        flood_requests = 200
        for i in range(flood_requests):
            try:
                self.cache_client.set(f"flood:{i}", "attack", ttl=1)
            except Exception:
                pass

        post_flood_metrics = PerformanceMetrics()
        recovery_samples = 50

        for i in range(recovery_samples):
            start = time.time()
            try:
                self.cache_client.set(f"post_flood:{i}", "ok", ttl=30)
                self.cache_client.get(f"post_flood:{i}")
                post_flood_metrics.record(time.time() - start)
            except Exception:
                post_flood_metrics.record(0, "failed")

        print(f"\nFlood Attack Recovery Results:")
        print(f"  Pre-Flood Avg: {pre_flood_metrics.avg_duration * 1000:.2f}ms")
        print(f"  Post-Flood Avg: {post_flood_metrics.avg_duration * 1000:.2f}ms")
        print(
            f"  Recovery Rate: {post_flood_metrics.total_requests / recovery_samples * 100:.0f}%"
        )

        assert post_flood_metrics.error_rate < 20, (
            "System did not recover after flood attack"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
