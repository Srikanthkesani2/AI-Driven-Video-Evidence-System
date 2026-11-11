import logging
import sys
from pathlib import Path

# Create logs directory
LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

def setup_logger(name: str = "evidence_analysis") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers if logger is imported multiple times
    if logger.handlers:
        return logger

    # Console Handler (clean text format)
    console_handler = sys.stderr
    console_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    c_handler = logging.StreamHandler(console_handler)
    c_handler.setFormatter(console_format)
    c_handler.setLevel(logging.INFO)
    logger.addHandler(c_handler)

    # File Handler (detailed debugging logs)
    f_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_format = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "file": "%(filename)s", "line": %(lineno)d, "message": "%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    )
    f_handler.setFormatter(file_format)
    f_handler.setLevel(logging.DEBUG)
    logger.addHandler(f_handler)

    return logger

# Global application logger
logger = setup_logger()
