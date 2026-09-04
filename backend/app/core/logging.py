import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-7s %(name)s  %(message)s", datefmt="%H:%M:%S"))
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("market_detective").setLevel(level)
