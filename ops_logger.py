"""
Ops Logger — Operasyonel loglama modülü.
Maritime Shorts pipeline için basit event logging.
"""

import logging
import time

logger = logging.getLogger(__name__)


class OpsLogger:
    """Pipeline operasyonlarını logla."""

    def __init__(self, project: str, component: str):
        self.project = project
        self.component = component
        self._start_time = None

    def start(self, operation: str, detail: str = ""):
        self._start_time = time.time()
        logger.info(f"🟢 [{self.project}/{self.component}] START: {operation} {detail}")

    def success(self, operation: str, detail: str = ""):
        elapsed = ""
        if self._start_time:
            elapsed = f" ({time.time() - self._start_time:.1f}s)"
            self._start_time = None
        logger.info(f"✅ [{self.project}/{self.component}] SUCCESS: {operation}{elapsed} {detail}")

    def error(self, operation: str, exception: Exception = None, message: str = ""):
        elapsed = ""
        if self._start_time:
            elapsed = f" ({time.time() - self._start_time:.1f}s)"
            self._start_time = None
        err = f" | {type(exception).__name__}: {exception}" if exception else ""
        logger.error(f"❌ [{self.project}/{self.component}] ERROR: {operation}{elapsed} {message}{err}")

    def info(self, message: str):
        logger.info(f"ℹ️ [{self.project}/{self.component}] {message}")

    def wait_for_logs(self):
        """Log flush için bekle."""
        time.sleep(0.5)


def get_ops_logger(project: str, component: str) -> OpsLogger:
    return OpsLogger(project, component)
