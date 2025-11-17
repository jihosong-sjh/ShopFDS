#!/usr/bin/env python3
"""
ShopFDS 성능 벤치마크 검증 스크립트
목표: FDS 100ms, API 200ms, 1000 TPS
"""

import asyncio
import time
import statistics
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import aiohttp
import numpy as np
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import psutil
import matplotlib.pyplot as plt
import seaborn as sns


@dataclass
class PerformanceResult:
    """성능 측정 결과"""
    service: str
    endpoint: str
    latency_p50: float
    latency_p95: float
    latency_p99: float
    latency_mean: float
    latency_std: float
    success_rate: float
    throughput: float
    total_requests: int
    success_count: int
    error_count: int
    target_met: bool


class PerformanceBenchmark:
    """성능 벤치마크 실행 클래스"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = []
        self.start_time = None
        self.end_time = None

        # 성능 목표
        self.targets = {
            "fds_latency_ms": 100,      # FDS 평가 100ms 이내
            "api_latency_ms": 200,      # API 응답 200ms 이내
            "throughput_tps": 1000,     # 초당 1000 거래 처리
            "success_rate": 99.9,       # 99.9% 성공률
        }

        # 테스트 사용자 데이터
        self.test_users = [
            {"email": f"perftest{i}@example.com", "password": "TestPass123!"}
            for i in range(100)
        ]

        # 테스트 상품 ID
        self.test_products = list(range(1, 101))

    def log(self, message: str, level: str = "INFO"):
        """로그 출력"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")

    async def measure_latency(
        self,
        session: aiohttp.ClientSession,
        url: str,
        method: str = "GET",
        json_data: dict = None,
        headers: dict = None
    ) -> Tuple[float, bool]:
        """단일 요청 지연시간 측정"""
        start = time.perf_counter()
        success = False

        try:
            async with session.request(
                method,
                url,
                json=json_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                await response.read()
                success = response.status < 400
                latency = (time.perf_counter() - start) * 1000  # ms 변환
                return latency, success
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return latency, False

    async def benchmark_endpoint(
        self,
        name: str,
        url: str,
        method: str = "GET",
        json_data: dict = None,
        headers: dict = None,
        request_count: int = 1000,
        concurrency: int = 50
    ) -> PerformanceResult:
        """엔드포인트 벤치마크"""
        self.log(f"벤치마킹 시작: {name} ({url})")

        latencies = []
        success_count = 0
        error_count = 0

        async with aiohttp.ClientSession() as session:
            # 워밍업
            self.log(f"  워밍업 중... (10 요청)")
            for _ in range(10):
                await self.measure_latency(session, url, method, json_data, headers)

            # 실제 벤치마크
            self.log(f"  벤치마크 실행 중... ({request_count} 요청, 동시성 {concurrency})")
            start_time = time.perf_counter()

            # 동시 요청 배치 실행
            for batch_start in range(0, request_count, concurrency):
                batch_size = min(concurrency, request_count - batch_start)
                tasks = [
                    self.measure_latency(session, url, method, json_data, headers)
                    for _ in range(batch_size)
                ]

                results = await asyncio.gather(*tasks)

                for latency, success in results:
                    latencies.append(latency)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1

            total_time = time.perf_counter() - start_time

        # 통계 계산
        latencies_sorted = sorted(latencies)
        result = PerformanceResult(
            service=name.split(" - ")[0] if " - " in name else name,
            endpoint=name.split(" - ")[1] if " - " in name else url,
            latency_p50=np.percentile(latencies_sorted, 50),
            latency_p95=np.percentile(latencies_sorted, 95),
            latency_p99=np.percentile(latencies_sorted, 99),
            latency_mean=statistics.mean(latencies),
            latency_std=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            success_rate=(success_count / request_count) * 100,
            throughput=request_count / total_time,
            total_requests=request_count,
            success_count=success_count,
            error_count=error_count,
            target_met=False  # 나중에 평가
        )

        # 목표 달성 여부 평가
        if "FDS" in name:
            result.target_met = result.latency_p95 <= self.targets["fds_latency_ms"]
        else:
            result.target_met = result.latency_p95 <= self.targets["api_latency_ms"]

        self.log(f"  완료: P95={result.latency_p95:.2f}ms, 성공률={result.success_rate:.1f}%, TPS={result.throughput:.1f}")

        return result

    async def benchmark_fds_evaluation(self) -> List[PerformanceResult]:
        """FDS 평가 API 벤치마크"""
        self.log("=" * 60)
        self.log("FDS 평가 성능 벤치마크")
        self.log("=" * 60)

        results = []

        # 다양한 리스크 레벨 거래 데이터
        test_transactions = [
            {
                # Low Risk - 정상 거래
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 50000,
                "currency": "KRW",
                "merchant": "정상상점",
                "card_bin": "411111",
                "ip_address": "211.234.123.45",
                "shipping_address": "서울특별시 강남구",
                "items": [{"product_id": 1, "quantity": 1, "price": 50000}]
            },
            {
                # Medium Risk - 중간 위험
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "amount": 500000,
                "currency": "KRW",
                "merchant": "전자상가",
                "card_bin": "555555",
                "ip_address": "192.168.1.1",
                "shipping_address": "부산광역시 해운대구",
                "items": [{"product_id": 2, "quantity": 5, "price": 100000}]
            },
            {
                # High Risk - 고위험
                "user_id": "123e4567-e89b-12d3-a456-426614174002",
                "amount": 5000000,
                "currency": "KRW",
                "merchant": "해외직구",
                "card_bin": "400000",
                "ip_address": "192.0.2.1",
                "shipping_address": "Unknown",
                "items": [{"product_id": 3, "quantity": 100, "price": 50000}]
            }
        ]

        for i, transaction in enumerate(test_transactions):
            risk_level = ["Low Risk", "Medium Risk", "High Risk"][i]
            result = await self.benchmark_endpoint(
                f"FDS - {risk_level}",
                "http://localhost:8001/v1/fds/evaluate",
                method="POST",
                json_data=transaction,
                request_count=500,
                concurrency=20
            )
            results.append(result)

        return results

    async def benchmark_ecommerce_api(self) -> List[PerformanceResult]:
        """이커머스 API 벤치마크"""
        self.log("=" * 60)
        self.log("이커머스 API 성능 벤치마크")
        self.log("=" * 60)

        results = []

        # 주요 엔드포인트 테스트
        endpoints = [
            ("Ecommerce - Health Check", "http://localhost:8000/health", "GET", None),
            ("Ecommerce - Product List", "http://localhost:8000/v1/products", "GET", None),
            ("Ecommerce - Product Detail", "http://localhost:8000/v1/products/1", "GET", None),
            ("Ecommerce - User Login", "http://localhost:8000/v1/auth/login", "POST", {
                "email": "perftest@example.com",
                "password": "TestPass123!"
            }),
        ]

        for name, url, method, data in endpoints:
            result = await self.benchmark_endpoint(
                name,
                url,
                method=method,
                json_data=data,
                request_count=500,
                concurrency=25
            )
            results.append(result)

        return results

    async def benchmark_order_flow(self) -> List[PerformanceResult]:
        """주문 플로우 전체 벤치마크 (FDS 포함)"""
        self.log("=" * 60)
        self.log("주문 플로우 전체 성능 벤치마크")
        self.log("=" * 60)

        results = []

        # 인증 토큰 획득
        async with aiohttp.ClientSession() as session:
            # 로그인
            login_resp = await session.post(
                "http://localhost:8000/v1/auth/login",
                json={"email": "perftest@example.com", "password": "TestPass123!"}
            )

            if login_resp.status == 200:
                auth_data = await login_resp.json()
                headers = {"Authorization": f"Bearer {auth_data.get('access_token')}"}
            else:
                headers = {}

            # 주문 생성 데이터
            order_data = {
                "shipping_name": "성능테스트",
                "shipping_address": "서울특별시 강남구 테헤란로 123",
                "shipping_phone": "010-1234-5678",
                "payment_info": {
                    "card_number": "4111111111111111",
                    "card_expiry": "12/25",
                    "card_cvv": "123"
                }
            }

            # 주문 생성 (FDS 평가 포함)
            result = await self.benchmark_endpoint(
                "Order Flow - Create Order with FDS",
                "http://localhost:8000/v1/orders",
                method="POST",
                json_data=order_data,
                headers=headers,
                request_count=200,  # 주문은 적은 수로 테스트
                concurrency=10
            )
            results.append(result)

        return results

    async def stress_test_throughput(self) -> Dict[str, float]:
        """처리량 스트레스 테스트 (1000 TPS 목표)"""
        self.log("=" * 60)
        self.log("처리량 스트레스 테스트 (목표: 1000 TPS)")
        self.log("=" * 60)

        target_tps = self.targets["throughput_tps"]
        test_duration = 10  # 10초 테스트
        total_requests = target_tps * test_duration

        self.log(f"목표: {test_duration}초 동안 {total_requests} 요청 처리")

        # FDS 평가 요청 (가장 중요한 성능 지표)
        transaction_data = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "amount": random.randint(10000, 100000),
            "currency": "KRW",
            "merchant": f"Merchant-{random.randint(1, 100)}",
            "card_bin": "411111",
            "ip_address": f"211.234.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "shipping_address": "서울특별시",
            "items": [{"product_id": random.randint(1, 100), "quantity": 1, "price": 50000}]
        }

        request_count = 0
        success_count = 0
        error_count = 0
        latencies = []

        start_time = time.perf_counter()

        async with aiohttp.ClientSession() as session:
            # 동시 요청 수를 점진적으로 증가
            concurrency_levels = [50, 100, 150, 200]

            for concurrency in concurrency_levels:
                if request_count >= total_requests:
                    break

                self.log(f"  동시성 레벨: {concurrency}")

                batch_size = min(concurrency * 10, total_requests - request_count)
                tasks = []

                for _ in range(batch_size):
                    # 각 요청마다 약간 다른 데이터
                    data = transaction_data.copy()
                    data["amount"] = random.randint(10000, 100000)
                    data["merchant"] = f"Merchant-{random.randint(1, 100)}"

                    tasks.append(
                        self.measure_latency(
                            session,
                            "http://localhost:8001/v1/fds/evaluate",
                            "POST",
                            data
                        )
                    )

                results = await asyncio.gather(*tasks)

                for latency, success in results:
                    latencies.append(latency)
                    request_count += 1
                    if success:
                        success_count += 1
                    else:
                        error_count += 1

                # 중간 통계
                elapsed = time.perf_counter() - start_time
                current_tps = request_count / elapsed
                self.log(f"    진행: {request_count}/{total_requests} 요청, TPS={current_tps:.1f}")

                if current_tps < target_tps * 0.8:  # 목표의 80% 미달 시
                    self.log(f"    경고: TPS가 목표에 미달 ({current_tps:.1f} < {target_tps * 0.8:.1f})")

        total_time = time.perf_counter() - start_time

        # 최종 통계
        actual_tps = request_count / total_time
        success_rate = (success_count / request_count) * 100 if request_count > 0 else 0

        results = {
            "target_tps": target_tps,
            "actual_tps": actual_tps,
            "total_requests": request_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_rate,
            "test_duration": total_time,
            "mean_latency": statistics.mean(latencies) if latencies else 0,
            "p95_latency": np.percentile(latencies, 95) if latencies else 0,
            "target_met": actual_tps >= target_tps
        }

        self.log(f"결과: TPS={actual_tps:.1f}, 성공률={success_rate:.1f}%, P95={results['p95_latency']:.2f}ms")
        self.log(f"목표 달성: {'[OK]' if results['target_met'] else '[FAIL]'}")

        return results

    def monitor_system_resources(self) -> Dict[str, float]:
        """시스템 리소스 모니터링"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_read_mb": disk_io.read_bytes / (1024**2) if disk_io else 0,
            "disk_write_mb": disk_io.write_bytes / (1024**2) if disk_io else 0,
            "network_sent_mb": net_io.bytes_sent / (1024**2),
            "network_recv_mb": net_io.bytes_recv / (1024**2),
        }

    def generate_report(self, all_results: Dict) -> bool:
        """성능 테스트 리포트 생성"""
        self.log("=" * 60)
        self.log("성능 벤치마크 결과 요약")
        self.log("=" * 60)

        # 전체 성공 여부
        all_passed = True

        # 1. FDS 성능 결과
        self.log("\n[FDS 평가 성능]")
        for result in all_results.get("fds", []):
            status = "[OK]" if result.target_met else "[FAIL]"
            self.log(f"  {status} {result.endpoint}: P95={result.latency_p95:.2f}ms (목표: {self.targets['fds_latency_ms']}ms)")
            if not result.target_met:
                all_passed = False

        # 2. API 성능 결과
        self.log("\n[이커머스 API 성능]")
        for result in all_results.get("ecommerce", []):
            status = "[OK]" if result.target_met else "[FAIL]"
            self.log(f"  {status} {result.endpoint}: P95={result.latency_p95:.2f}ms (목표: {self.targets['api_latency_ms']}ms)")
            if not result.target_met:
                all_passed = False

        # 3. 주문 플로우 성능
        self.log("\n[주문 플로우 성능]")
        for result in all_results.get("order_flow", []):
            status = "[OK]" if result.target_met else "[FAIL]"
            self.log(f"  {status} {result.endpoint}: P95={result.latency_p95:.2f}ms")
            if not result.target_met:
                all_passed = False

        # 4. 처리량 테스트 결과
        self.log("\n[처리량 (Throughput) 테스트]")
        throughput = all_results.get("throughput", {})
        if throughput:
            status = "[OK]" if throughput.get("target_met") else "[FAIL]"
            self.log(f"  {status} 실제 TPS: {throughput.get('actual_tps', 0):.1f} (목표: {self.targets['throughput_tps']} TPS)")
            self.log(f"      성공률: {throughput.get('success_rate', 0):.1f}%")
            self.log(f"      P95 지연시간: {throughput.get('p95_latency', 0):.2f}ms")
            if not throughput.get("target_met"):
                all_passed = False

        # 5. 시스템 리소스
        self.log("\n[시스템 리소스 사용량]")
        resources = all_results.get("resources", {})
        if resources:
            self.log(f"  CPU: {resources.get('cpu_percent', 0):.1f}%")
            self.log(f"  메모리: {resources.get('memory_percent', 0):.1f}%")
            self.log(f"  가용 메모리: {resources.get('memory_available_gb', 0):.2f} GB")

        # 6. 최종 판정
        self.log("\n" + "=" * 60)
        if all_passed:
            self.log("[SUCCESS] 모든 성능 목표 달성!", "SUCCESS")
            self.log("  - FDS 평가: 100ms 이내")
            self.log("  - API 응답: 200ms 이내")
            self.log("  - 처리량: 1000 TPS 이상")
        else:
            self.log("[ERROR] 일부 성능 목표 미달성", "ERROR")
            self.log("  성능 최적화가 필요합니다.")

        # 상세 리포트 파일 저장
        report_path = self.project_root / "performance_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            # PerformanceResult 객체를 dict로 변환
            serializable_results = {}
            for key, value in all_results.items():
                if isinstance(value, list):
                    serializable_results[key] = [asdict(r) if hasattr(r, '__dict__') else r for r in value]
                else:
                    serializable_results[key] = value

            json.dump(serializable_results, f, indent=2, ensure_ascii=False, default=str)

        self.log(f"\n상세 리포트 저장: {report_path}")

        return all_passed

    def generate_charts(self, all_results: Dict):
        """성능 차트 생성"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # GUI 없이 실행

            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle("ShopFDS 성능 벤치마크 결과", fontsize=16)

            # 1. FDS 지연시간 분포
            ax1 = axes[0, 0]
            fds_results = all_results.get("fds", [])
            if fds_results:
                labels = [r.endpoint.split(" - ")[-1] for r in fds_results]
                p95_values = [r.latency_p95 for r in fds_results]
                colors = ['green' if v <= 100 else 'red' for v in p95_values]

                ax1.bar(labels, p95_values, color=colors)
                ax1.axhline(y=100, color='r', linestyle='--', label='목표: 100ms')
                ax1.set_ylabel("P95 지연시간 (ms)")
                ax1.set_title("FDS 평가 성능")
                ax1.legend()

            # 2. API 지연시간 분포
            ax2 = axes[0, 1]
            api_results = all_results.get("ecommerce", [])
            if api_results:
                labels = [r.endpoint.split(" - ")[-1][:15] for r in api_results]
                p95_values = [r.latency_p95 for r in api_results]
                colors = ['green' if v <= 200 else 'red' for v in p95_values]

                ax2.bar(labels, p95_values, color=colors)
                ax2.axhline(y=200, color='r', linestyle='--', label='목표: 200ms')
                ax2.set_ylabel("P95 지연시간 (ms)")
                ax2.set_title("이커머스 API 성능")
                ax2.tick_params(axis='x', rotation=45)
                ax2.legend()

            # 3. 처리량 (TPS)
            ax3 = axes[1, 0]
            throughput = all_results.get("throughput", {})
            if throughput:
                categories = ['목표 TPS', '실제 TPS']
                values = [
                    throughput.get('target_tps', 1000),
                    throughput.get('actual_tps', 0)
                ]
                colors = ['blue', 'green' if values[1] >= values[0] else 'red']

                ax3.bar(categories, values, color=colors)
                ax3.set_ylabel("초당 거래 수 (TPS)")
                ax3.set_title("처리량 성능")
                ax3.text(1, values[1], f"{values[1]:.1f}", ha='center', va='bottom')

            # 4. 시스템 리소스
            ax4 = axes[1, 1]
            resources = all_results.get("resources", {})
            if resources:
                categories = ['CPU', '메모리']
                values = [
                    resources.get('cpu_percent', 0),
                    resources.get('memory_percent', 0)
                ]

                ax4.bar(categories, values, color=['skyblue', 'lightgreen'])
                ax4.set_ylabel("사용률 (%)")
                ax4.set_title("시스템 리소스 사용량")
                ax4.set_ylim(0, 100)

                for i, v in enumerate(values):
                    ax4.text(i, v, f"{v:.1f}%", ha='center', va='bottom')

            plt.tight_layout()

            # 차트 저장
            chart_path = self.project_root / "performance_charts.png"
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            self.log(f"성능 차트 저장: {chart_path}")

        except ImportError:
            self.log("matplotlib가 설치되지 않아 차트를 생성할 수 없습니다.", "WARNING")
        except Exception as e:
            self.log(f"차트 생성 실패: {str(e)}", "ERROR")

    async def run(self) -> bool:
        """전체 벤치마크 실행"""
        self.start_time = datetime.now()

        self.log("=" * 60)
        self.log("ShopFDS 성능 벤치마크 시작")
        self.log(f"시작 시간: {self.start_time}")
        self.log("=" * 60)

        all_results = {}

        try:
            # 시스템 리소스 초기 상태
            self.log("\n시스템 리소스 확인 중...")
            all_results["resources"] = self.monitor_system_resources()

            # 1. FDS 평가 벤치마크
            fds_results = await self.benchmark_fds_evaluation()
            all_results["fds"] = fds_results

            # 2. 이커머스 API 벤치마크
            ecommerce_results = await self.benchmark_ecommerce_api()
            all_results["ecommerce"] = ecommerce_results

            # 3. 주문 플로우 벤치마크
            order_results = await self.benchmark_order_flow()
            all_results["order_flow"] = order_results

            # 4. 처리량 스트레스 테스트
            throughput_results = await self.stress_test_throughput()
            all_results["throughput"] = throughput_results

            # 시스템 리소스 최종 상태
            all_results["resources_final"] = self.monitor_system_resources()

        except Exception as e:
            self.log(f"벤치마크 실행 중 오류: {str(e)}", "ERROR")
            return False

        self.end_time = datetime.now()
        execution_time = (self.end_time - self.start_time).total_seconds()

        self.log(f"\n실행 시간: {execution_time:.2f}초")

        # 리포트 생성
        success = self.generate_report(all_results)

        # 차트 생성
        self.generate_charts(all_results)

        return success


async def main():
    """메인 함수"""
    benchmark = PerformanceBenchmark()
    success = await benchmark.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)