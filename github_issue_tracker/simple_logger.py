"""Dead simple logging that actually works."""

import sys
from datetime import datetime
from pathlib import Path

class SimpleLogger:
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"github_tracker_{timestamp}.log"
        
        # Open file in unbuffered mode so it writes immediately
        self.file = open(self.log_file, "w", buffering=1)
        
    def log(self, message):
        """Write a log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        
        # Write to file
        self.file.write(log_line)
        self.file.flush()  # Force flush
        
        # Also print to stderr so we can see it
        print(log_line.strip(), file=sys.stderr)
    
    def __del__(self):
        """Ensure file is closed."""
        if hasattr(self, 'file'):
            self.file.close()

# Global logger instance
_logger = None

def get_logger():
    """Get or create the global logger."""
    global _logger
    if _logger is None:
        _logger = SimpleLogger()
    return _logger

def log(message):
    """Log a message."""
    get_logger().log(message)