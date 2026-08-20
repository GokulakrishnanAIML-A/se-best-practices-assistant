"""Module for metric aggregation and analytics rollups."""

import sqlite3
import time


class ConcreteRedisCache:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.store = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, val: str):
        self.store[key] = val


class AnalyticsAggregator:
    def __init__(self):
        # Violation: DIP (Direct hardcoded dependency creation instead of dependency injection)
        self.redis_cache = ConcreteRedisCache(host="127.0.0.1", port=6379)
        self.db_conn = sqlite3.connect("analytics_prod.db")

    # Violation: long-function (> 50 lines)
    def compute_daily_rollups(self, event_logs: list[dict], target_date: str) -> dict:
        page_views = 0
        unique_visitors = set()
        error_count = 0
        conversion_events = 0
        latency_sum = 0.0
        response_status_counts = {}

        for entry in event_logs:
            entry_date = entry.get("date", "")
            if entry_date != target_date:
                continue

            event_type = entry.get("event", "UNKNOWN")
            user_id = entry.get("user_id")
            latency = float(entry.get("latency_ms", 0.0))
            status_code = int(entry.get("status", 200))

            if user_id:
                unique_visitors.add(user_id)

            if event_type == "PAGE_VIEW":
                page_views += 1
            elif event_type == "CONVERSION":
                conversion_events += 1

            if status_code >= 400:
                error_count += 1

            status_bucket = f"{status_code // 100}xx"
            response_status_counts[status_bucket] = response_status_counts.get(status_bucket, 0) + 1
            latency_sum += latency

        total_events = len(event_logs)
        avg_latency = (latency_sum / total_events) if total_events > 0 else 0.0
        conversion_rate = (conversion_events / page_views * 100) if page_views > 0 else 0.0

        rollup_result = {
            "date": target_date,
            "total_page_views": page_views,
            "unique_visitors": len(unique_visitors),
            "errors": error_count,
            "avg_latency_ms": round(avg_latency, 2),
            "conversion_rate_pct": round(conversion_rate, 2),
            "status_distribution": response_status_counts,
        }

        # Cache result
        cache_key = f"rollup:{target_date}"
        self.redis_cache.set(cache_key, str(rollup_result))

        return rollup_result
