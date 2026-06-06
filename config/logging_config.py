import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from .settings import Settings, get_settings


def configure_logging(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved.log_level.upper())
