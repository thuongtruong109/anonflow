import logging, sys

def setup_logger():
    logger = logging.getLogger("my_app")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # file_handler = logging.FileHandler("app.log", encoding="utf-8")
    # file_handler.setLevel(logging.DEBUG)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    logger.propagate = False

    return logger
