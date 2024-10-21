#!/bin/bash
flask db upgrade

gunicorn app:app -w ${WORKERS} -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000