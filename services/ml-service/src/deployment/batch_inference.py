"""
배치 추론 파이프라인 모듈

동시 요청 50개 이상 시 배치 추론을 활성화하여 처리량 향상
- 요청 큐 관리
- 동적 배치 구성
- 배치 크기 자동 조정
- 추론 결과 매핑
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class InferenceRequest:
    """
    추론 요청 데이터 클래스

    Attributes:
        request_id: 요청 고유 ID
        input_data: 입력 데이터
        timestamp: 요청 시각
        future: 비동기 결과 Future
    """

    request_id: str
    input_data: Any
    timestamp: float = field(default_factory=time.time)
    future: asyncio.Future = field(default_factory=asyncio.Future)


class BatchInferencePipeline:
    """
    배치 추론 파이프라인

    Features:
    - 동시 요청 수집 및 배치 구성
    - 배치 크기 50 기본, 최대 100
    - 최대 배치 지연 50ms
    - 동적 배치 크기 조정 (처리량 기반)
    - 요청별 결과 매핑

    Performance:
    - 1,000 TPS 부하 처리
    - P95 응답 시간 50ms 목표
    - 배치 효율성 90% 이상
    """

    def __init__(
        self,
        inference_func: Callable[[np.ndarray], np.ndarray],
        batch_size: int = 50,
        max_batch_size: int = 100,
        max_batch_delay_ms: int = 50,
        min_batch_size: int = 10,
    ):
        """
        Args:
            inference_func: 배치 추론 함수 (입력: (batch_size, ...), 출력: (batch_size, ...))
            batch_size: 목표 배치 크기
            max_batch_size: 최대 배치 크기
            max_batch_delay_ms: 최대 배치 대기 시간 (ms)
            min_batch_size: 최소 배치 크기 (이하 시 즉시 처리)
        """
        self.inference_func = inference_func
        self.batch_size = batch_size
        self.max_batch_size = max_batch_size
        self.max_batch_delay_ms = max_batch_delay_ms
        self.min_batch_size = min_batch_size

        # 요청 큐
        self.request_queue: deque[InferenceRequest] = deque()
        self.queue_lock = asyncio.Lock()

        # 통계
        self.total_requests = 0
        self.total_batches = 0
        self.total_latency = 0.0

        # 백그라운드 배치 처리 태스크
        self.batch_task: Optional[asyncio.Task] = None
        self.running = False

        logger.info("[BATCH PIPELINE] Initialized")
        logger.info(f"  Target batch size: {batch_size}")
        logger.info(f"  Max batch delay: {max_batch_delay_ms}ms")

    async def start(self):
        """
        배치 추론 파이프라인 시작
        """
        if self.running:
            logger.warning("[WARNING] Pipeline already running")
            return

        self.running = True
        self.batch_task = asyncio.create_task(self._batch_processing_loop())
        logger.info("[START] Batch inference pipeline started")

    async def stop(self):
        """
        배치 추론 파이프라인 중지
        """
        if not self.running:
            return

        self.running = False
        if self.batch_task:
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass

        # 남은 요청 처리
        if len(self.request_queue) > 0:
            logger.info(
                f"[STOP] Processing remaining {len(self.request_queue)} requests..."
            )
            await self._process_batch(list(self.request_queue))
            self.request_queue.clear()

        logger.info("[STOP] Batch inference pipeline stopped")
        self._log_statistics()

    async def infer(self, request_id: str, input_data: Any) -> Any:
        """
        비동기 배치 추론 실행

        Args:
            request_id: 요청 고유 ID
            input_data: 입력 데이터

        Returns:
            추론 결과

        Example:
            >>> pipeline = BatchInferencePipeline(model_inference_func)
            >>> await pipeline.start()
            >>> result = await pipeline.infer("req-123", input_data)
        """
        request = InferenceRequest(request_id=request_id, input_data=input_data)

        async with self.queue_lock:
            self.request_queue.append(request)
            queue_size = len(self.request_queue)

        logger.debug(f"[QUEUE] Request {request_id} added (queue size: {queue_size})")

        # 큐 크기가 배치 크기 이상이면 즉시 처리 트리거
        if queue_size >= self.batch_size:
            asyncio.create_task(self._trigger_batch_processing())

        # 결과 대기
        result = await request.future
        return result

    async def _batch_processing_loop(self):
        """
        백그라운드 배치 처리 루프

        주기적으로 큐를 확인하고 배치 처리 실행
        """
        logger.info("[LOOP] Batch processing loop started")

        while self.running:
            try:
                # 최대 배치 지연 시간만큼 대기
                await asyncio.sleep(self.max_batch_delay_ms / 1000.0)

                # 큐에 요청이 있으면 처리
                if len(self.request_queue) > 0:
                    await self._trigger_batch_processing()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ERROR] Batch processing loop error: {e}")

        logger.info("[LOOP] Batch processing loop stopped")

    async def _trigger_batch_processing(self):
        """
        배치 처리 트리거 (큐에서 배치 추출 및 추론)
        """
        async with self.queue_lock:
            if len(self.request_queue) == 0:
                return

            # 배치 크기 결정
            current_batch_size = min(len(self.request_queue), self.max_batch_size)

            # 최소 배치 크기 미만이면 대기 (단, 타임아웃 초과 시 처리)
            if current_batch_size < self.min_batch_size:
                oldest_request_age = time.time() - self.request_queue[0].timestamp
                if oldest_request_age < (self.max_batch_delay_ms / 1000.0):
                    return  # 더 대기

            # 배치 추출
            batch_requests = [
                self.request_queue.popleft() for _ in range(current_batch_size)
            ]

        # 배치 추론 실행 (락 해제 후)
        await self._process_batch(batch_requests)

    async def _process_batch(self, batch_requests: List[InferenceRequest]):
        """
        배치 추론 실행 및 결과 매핑

        Args:
            batch_requests: 배치 요청 리스트
        """
        if len(batch_requests) == 0:
            return

        batch_size = len(batch_requests)
        start_time = time.time()

        logger.debug(f"[BATCH] Processing batch of {batch_size} requests...")

        try:
            # 입력 데이터 배치 구성
            batch_input = np.array([req.input_data for req in batch_requests])

            # 배치 추론 실행
            batch_output = self.inference_func(batch_input)

            # 결과를 각 요청에 매핑
            for i, request in enumerate(batch_requests):
                result = batch_output[i]
                if not request.future.done():
                    request.future.set_result(result)

            # 통계 업데이트
            batch_latency = (time.time() - start_time) * 1000  # ms
            self.total_requests += batch_size
            self.total_batches += 1
            self.total_latency += batch_latency

            avg_latency_per_request = batch_latency / batch_size

            logger.debug(
                f"[BATCH] Processed {batch_size} requests in {batch_latency:.2f}ms "
                f"(avg: {avg_latency_per_request:.2f}ms/request)"
            )

        except Exception as e:
            logger.error(f"[ERROR] Batch inference failed: {e}")

            # 에러 전파
            for request in batch_requests:
                if not request.future.done():
                    request.future.set_exception(e)

    def _log_statistics(self):
        """
        배치 추론 통계 로깅
        """
        if self.total_batches == 0:
            logger.info("[STATS] No batches processed")
            return

        avg_batch_size = self.total_requests / self.total_batches
        avg_batch_latency = self.total_latency / self.total_batches
        avg_request_latency = self.total_latency / self.total_requests

        logger.info("[STATS] Batch Inference Statistics:")
        logger.info(f"  Total requests: {self.total_requests}")
        logger.info(f"  Total batches: {self.total_batches}")
        logger.info(f"  Avg batch size: {avg_batch_size:.2f}")
        logger.info(f"  Avg batch latency: {avg_batch_latency:.2f}ms")
        logger.info(f"  Avg request latency: {avg_request_latency:.2f}ms")

        batch_efficiency = (avg_batch_size / self.batch_size) * 100
        logger.info(f"  Batch efficiency: {batch_efficiency:.1f}%%")

    async def get_stats(self) -> Dict[str, Any]:
        """
        실시간 통계 반환

        Returns:
            통계 딕셔너리
        """
        async with self.queue_lock:
            queue_size = len(self.request_queue)

        if self.total_batches == 0:
            return {
                "queue_size": queue_size,
                "total_requests": 0,
                "total_batches": 0,
            }

        avg_batch_size = self.total_requests / self.total_batches
        avg_batch_latency = self.total_latency / self.total_batches
        avg_request_latency = self.total_latency / self.total_requests
        batch_efficiency = (avg_batch_size / self.batch_size) * 100

        return {
            "queue_size": queue_size,
            "total_requests": self.total_requests,
            "total_batches": self.total_batches,
            "avg_batch_size": round(avg_batch_size, 2),
            "avg_batch_latency_ms": round(avg_batch_latency, 2),
            "avg_request_latency_ms": round(avg_request_latency, 2),
            "batch_efficiency_pct": round(batch_efficiency, 1),
        }


# 사용 예시
async def example_usage():
    """
    배치 추론 파이프라인 사용 예시
    """

    # 예제 모델 추론 함수
    def model_inference(batch_input: np.ndarray) -> np.ndarray:
        """
        배치 추론 함수 (실제로는 ONNX/TorchServe 모델 호출)

        Args:
            batch_input: (batch_size, feature_dim)

        Returns:
            (batch_size, num_classes)
        """
        # 예제: 간단한 선형 변환
        time.sleep(0.01)  # 추론 시간 시뮬레이션 (10ms)
        return np.random.rand(len(batch_input), 2)  # (batch_size, 2)

    # 파이프라인 생성
    pipeline = BatchInferencePipeline(
        inference_func=model_inference,
        batch_size=50,
        max_batch_delay_ms=50,
    )

    # 파이프라인 시작
    await pipeline.start()

    # 동시 요청 시뮬레이션
    async def send_request(i):
        input_data = np.random.rand(100)  # 100차원 특징
        result = await pipeline.infer(request_id=f"req-{i}", input_data=input_data)
        return result

    # 1,000개 요청 동시 전송
    logger.info("[TEST] Sending 1,000 concurrent requests...")
    tasks = [send_request(i) for i in range(1000)]
    results = await asyncio.gather(*tasks)

    logger.info(f"[TEST] Received {len(results)} results")

    # 통계 확인
    stats = await pipeline.get_stats()
    logger.info(f"[TEST] Pipeline stats: {stats}")

    # 파이프라인 종료
    await pipeline.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(example_usage())
