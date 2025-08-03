"""Structured logging configuration."""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import structlog


def setup_logging():
    """Set up structured logging with file rotation."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Clean up old logs (16+ days)
    cleanup_old_logs(logs_dir)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"github_tracker_{timestamp}.log"
    
    # Configure structlog
    logging.basicConfig(
        format="%(message)s",
        stream=open(log_file, "w", encoding="utf-8"),
        level=logging.DEBUG,
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Also log to console for immediate feedback
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(console_handler)
    
    return structlog.get_logger()


def cleanup_old_logs(logs_dir: Path, max_age_days: int = 16):
    """Remove log files older than max_age_days."""
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    
    for log_file in logs_dir.glob("github_tracker_*.log"):
        try:
            # Extract timestamp from filename
            timestamp_str = log_file.stem.replace("github_tracker_", "")
            file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            if file_date < cutoff_date:
                log_file.unlink()
                print(f"Cleaned up old log: {log_file}")
        except (ValueError, OSError):
            # Skip files that don't match our naming pattern
            continue