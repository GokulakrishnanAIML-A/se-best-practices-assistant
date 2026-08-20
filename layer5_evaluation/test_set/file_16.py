"""Module for system audit logging and compliance records."""

import os
import time


# Violation: ISP (Fat interface with distinct destination mechanisms)
class IAuditLogger:
    def log_to_file(self, message: str, category: str) -> None:
        raise NotImplementedError

    def log_to_syslog(self, facility: int, message: str) -> None:
        raise NotImplementedError

    def log_to_cloudwatch(self, stream_name: str, payload: dict) -> None:
        raise NotImplementedError

    def log_to_kafka(self, topic: str, key: str, value: bytes) -> None:
        raise NotImplementedError


class LocalFileAuditLogger(IAuditLogger):
    def __init__(self, base_dir: str = "/var/log/app"):
        self.base_dir = base_dir

    def log_to_file(self, message: str, category: str) -> None:
        # Violation: OWASP-Injection (Path traversal vulnerability through unvalidated filename parameter)
        target_path = os.path.join(self.base_dir, category + ".log")
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")

    def log_to_syslog(self, facility: int, message: str) -> None:
        raise NotImplementedError("Syslog not implemented in LocalFileAuditLogger")

    def log_to_cloudwatch(self, stream_name: str, payload: dict) -> None:
        raise NotImplementedError("CloudWatch not implemented in LocalFileAuditLogger")

    def log_to_kafka(self, topic: str, key: str, value: bytes) -> None:
        raise NotImplementedError("Kafka not implemented in LocalFileAuditLogger")
