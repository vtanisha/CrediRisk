import os
import logging
import logging.config

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def setup_logging() -> None:
    is_production = os.getenv("LOG_FORMAT", "json") == "json"

    if is_production:
        try:
            from pythonjsonlogger import jsonlogger

            class _JsonFormatter(jsonlogger.JsonFormatter):
                def add_fields(self, log_record, record, message_dict):
                    super().add_fields(log_record, record, message_dict)
                    log_record["level"] = record.levelname
                    log_record["logger"] = record.name

            formatter_class = "logging_config._JsonFormatter"
            fmt = "%(asctime)s %(level)s %(logger)s %(message)s"
        except ImportError:
            is_production = False

    if not is_production:
        fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": fmt,
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            }
        },
        "root": {"level": LOG_LEVEL, "handlers": ["console"]},
        "loggers": {
            "uvicorn": {"propagate": True},
            "uvicorn.access": {"propagate": True},
            "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
        },
    })
