from loguru import logger

from config.settings import LOG_DIR

LOG_DIR.mkdir(exist_ok=True)

logger.add(
    LOG_DIR / "attendance.log",
    rotation="10 MB",
    retention="30 days",
    level="INFO"
)