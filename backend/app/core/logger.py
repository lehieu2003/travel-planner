# backend/app/core/logger.py

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


# -------------------------------------------------------------------
# LOG DIRECTORY + FILE SETUP
# -------------------------------------------------------------------
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"


# -------------------------------------------------------------------
# FORMATTER
# -------------------------------------------------------------------
LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)

formatter = logging.Formatter(LOG_FORMAT)


# -------------------------------------------------------------------
# HANDLER: FILE (rotating)
# -------------------------------------------------------------------
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,   # 5 MB
    backupCount=5,              # keep 5 files
    encoding="utf-8"
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)


# -------------------------------------------------------------------
# HANDLER: CONSOLE
# -------------------------------------------------------------------
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)


# -------------------------------------------------------------------
# GLOBAL LOGGER
# -------------------------------------------------------------------
logger = logging.getLogger("travel_planner")
logger.setLevel(logging.DEBUG)   # allow all levels → handlers filter them

# Prevent duplicate handlers when reloading app
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# -------------------------------------------------------------------
# TEST MESSAGE WHEN LOGGER CREATED
# -------------------------------------------------------------------
logger.debug("Logger initialized successfully.")
