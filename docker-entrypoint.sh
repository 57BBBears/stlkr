#!/bin/bash
alembic upgrade head

gunicorn src.main:app -w ${WORKERS} -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000