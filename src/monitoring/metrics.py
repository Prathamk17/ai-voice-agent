"""
Prometheus Metrics

Module 5: Dashboard, Analytics & Monitoring
Prometheus metrics collection for monitoring system performance.
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Define metrics

# Call metrics
calls_initiated_total = Counter(
    'calls_initiated_total',
    'Total number of calls initiated',
    ['campaign_id', 'status']
)

calls_completed_total = Counter(
    'calls_completed_total',
    'Total number of calls completed',
    ['campaign_id', 'outcome']
)

call_duration_seconds = Histogram(
    'call_duration_seconds',
    'Call duration in seconds',
    ['campaign_id'],
    buckets=[30, 60, 120, 180, 300, 600]
)

# Active call tracking
active_calls = Gauge(
    'active_calls',
    'Number of currently active calls'
)

queued_calls = Gauge(
    'queued_calls',
    'Number of calls waiting in queue'
)

# Campaign metrics
campaign_status = Gauge(
    'campaign_status',
    'Campaign status (1=running, 0=not running)',
    ['campaign_id', 'campaign_name']
)

# AI Service metrics
llm_request_duration = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

stt_request_duration = Histogram(
    'stt_request_duration_seconds',
    'STT request duration in seconds',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

tts_request_duration = Histogram(
    'tts_request_duration_seconds',
    'TTS request duration in seconds',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
)

# WebSocket metrics
websocket_connections = Gauge(
    'websocket_connections',
    'Number of active WebSocket connections'
)

# Error tracking
errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'component']
)


class MetricsCollector:
    """
    Collect and expose Prometheus metrics
    """

    @staticmethod
    def record_call_initiated(campaign_id: int, status: str):
        """Record when a call is initiated"""
        calls_initiated_total.labels(
            campaign_id=str(campaign_id),
            status=status
        ).inc()

    @staticmethod
    def record_call_completed(campaign_id: int, outcome: str, duration: float):
        """Record when a call is completed with outcome and duration"""
        calls_completed_total.labels(
            campaign_id=str(campaign_id),
            outcome=outcome
        ).inc()

        call_duration_seconds.labels(
            campaign_id=str(campaign_id)
        ).observe(duration)

    @staticmethod
    def set_active_calls(count: int):
        """Update the number of active calls"""
        active_calls.set(count)

    @staticmethod
    def set_queued_calls(count: int):
        """Update the number of queued calls"""
        queued_calls.set(count)

    @staticmethod
    def set_campaign_status(campaign_id: int, name: str, is_running: bool):
        """Update campaign status"""
        campaign_status.labels(
            campaign_id=str(campaign_id),
            campaign_name=name
        ).set(1 if is_running else 0)

    @staticmethod
    def record_llm_request(model: str, duration: float):
        """Record LLM request duration"""
        llm_request_duration.labels(model=model).observe(duration)

    @staticmethod
    def record_stt_request(duration: float):
        """Record STT request duration"""
        stt_request_duration.observe(duration)

    @staticmethod
    def record_tts_request(duration: float):
        """Record TTS request duration"""
        tts_request_duration.observe(duration)

    @staticmethod
    def set_websocket_connections(count: int):
        """Update the number of WebSocket connections"""
        websocket_connections.set(count)

    @staticmethod
    def record_error(error_type: str, component: str):
        """Record an error occurrence"""
        errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()

    @staticmethod
    def get_metrics() -> Response:
        """
        Return metrics in Prometheus format
        """
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )


# Global instance
metrics = MetricsCollector()
