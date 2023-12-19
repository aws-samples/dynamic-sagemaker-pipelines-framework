# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
from typing import Union, List


class Logger:
    """
    Logger class that implement custom formattin messages

    Attibutes:
    ----------
    - logger (logging.Logger): The logger object from the logging module.

    Methods:
    ----------
    - log_debug(*messages: Union[str, List[str]]): Logs debug messages
    - log_info(*messages: Union[str, List[str]]): Logs informational messages
    - log_warning(*messages: Union[str, List[str]]): Logs warning messages
    - log_error(*messages: Union[str, List[str]]): Logs error messages
    - log_critical(*messages: Union[str, List[str]]): Logs critical messages
    """

    def __init__(self, config: Union[dict, None] = None):
        """
        Initializes the Loger class.

        Args:
        ----------
        - config (dict): Configuration for the logger
        """
        # Get logger
        self.logger = logging.getLogger(self.__class__.__name__)

        # Create the formatter
        formatter = logging.Formatter(
            "%(asctime)s :::: [Log %(name)s] :::: %(message)s",
            datefmt="[%Y-%m-%d %H:%M:%S %Z%z]"
        )

        # Create the console handler and add formatter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Add handlers to the loger
        self.logger.addHandler(console_handler)

    def _log_messages(self, level: str, prefix: str, *messages: Union[str, List[str]]):
        """
        Logs messages with the specified level.

        Args:
        ----------
        - level:     (str): The logging level
        - prefix:    (str): Message prefix to be used
        - *messages: (Union[str, List[str]]): Single or List of messages
        """
        for msg in messages:
            level(f"[Level: {prefix}] :::: {msg}")

    def log_debug(self, *messages: Union[str, List[str]]):
        """
        Logs debug messages

        Args:
        ----------
        - *messages: (Union[str, List[str]]): Single or List of messages
        """
        self.logger.setLevel(logging.DEBUG)
        self._log_messages(self.logger.debug, "DEBUG   ", *messages)

    def log_info(self, *messages: Union[str, List[str]]):
        """
        Logs informational messages

        Args:
        ----------
        - *messages: (Union[str, List[str]]): Single or List of messages
        """
        self.logger.setLevel(logging.INFO)
        self._log_messages(self.logger.info, "INFO    ", *messages)

    def log_warning(self, *messages: Union[str, List[str]]):
        """
        Logs warining messages

        Args:
        ----------
        - *messages: (Union[str, List[str]]): Single or List of messages
        """
        self.logger.setLevel(logging.WARNING)
        self._log_messages(self.logger.warning, "WARNING ", *messages)

    def log_error(self, *messages: Union[str, List[str]]):
        """
        Logs error messages

        Args:
        ----------
        - *messages: (Union[str, List[str]]): Single or List of messages
        """
        self.logger.setLevel(logging.ERROR)
        self._log_messages(self.logger.error, "ERROR   ", *messages)

    def log_critical(self, *messages: Union[str, List[str]]):
        """
        Logs critical messages

        Args:
        ----------
        - *messages: (Union[str, List[str]]): Single or List of messages
        """
        self.logger.setLevel(logging.CRITICAL)
        self._log_messages(self.logger.critical, "CRITICAL", *messages)
