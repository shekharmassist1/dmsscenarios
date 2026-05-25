# utilities/logger.py

import logging

logging.basicConfig(
    filename="logs/test.log",
    level=logging.INFO,
    format="%(asctime)s : %(levelname)s : %(message)s"
)