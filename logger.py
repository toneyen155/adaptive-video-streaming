import logging
import sys

class Logger:
    """
    A reusable logger that includes class/module name in log messages.
    
    Usage:
        # In your class:
        self.logger = Logger.get_logger(__name__, enable_logging=True)
        self.logger.info("This is an info message")
    
    """
    @staticmethod
    def get_logger(name: str, enable_logging: bool = True, level: int = logging.DEBUG) -> logging.Logger:
        logger = logging.getLogger(name)
        # Remove existing handlers to avoid duplicates (if called multiple times)
        if logger.handlers:
            logger.handlers.clear()
        if enable_logging:
            logger.setLevel(level)
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)  
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        else:
            logger.setLevel(logging.WARNING)
            
        logger.propagate = False
        
        return logger
        