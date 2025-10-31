import logging
import os
from datetime import datetime

class FileLogger:
    """
    A class to handle logging messages to a file.
    """
    def __init__(self, log_file_name="application.log", log_level=logging.INFO):
        """
        Initializes the FileLogger with a specified log file name and level.

        Args:
            log_file_name (str): The name of the file to log to.
            log_level (int): The minimum level of messages to log (e.g., logging.INFO, logging.DEBUG).
        """
        
        logging.INFO
        logging.DEBUG
        logging.ERROR
        logging.CRITICAL
        logging.WARNING
        logging.NOTSET
        logging.FATAL
        logging.WARN

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)

        # Create a file handler
        # 'a' mode appends to the file if it exists, otherwise creates it.
        file_handler = logging.FileHandler(log_file_name, mode='a')
        file_handler.setLevel(log_level)

        # Create a formatter for the log messages
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add the handler to the logger
        self.logger.addHandler(file_handler)

    def debug(self, message):
        """Logs a message with level DEBUG."""
        self.logger.debug(message)

    def info(self, message):
        """Logs a message with level INFO."""
        self.logger.info(message)

    def warning(self, message):
        """Logs a message with level WARNING."""
        self.logger.warning(message)

    def error(self, message):
        """Logs a message with level ERROR."""
        self.logger.error(message)

    def critical(self, message):
        """Logs a message with level CRITICAL."""
        self.logger.critical(message)

# Example Usage:
if __name__ == "__main__":
    # Create a logger instance
    my_logger = FileLogger(log_file_name="my_app_logs.log", log_level=logging.DEBUG)

    # Log some messages
    my_logger.debug("This is a debug message.")
    my_logger.info("An informational event occurred.")
    my_logger.warning("Something might be going wrong here.")
    my_logger.error("An error has definitely occurred!")
    my_logger.critical("Critical system failure!")

    print("Log messages have been written to 'my_app_logs.log'")

    # You can also create multiple loggers for different parts of your application
    another_logger = FileLogger(log_file_name="another_module.log", log_level=logging.WARNING)
    another_logger.warning("Warning from another module.")