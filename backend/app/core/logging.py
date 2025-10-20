import logging
from fastapi import FastAPI

def configure_logging(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.logger = logging.getLogger(app.title)
