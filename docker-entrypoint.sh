#!/bin/bash
flask db upgrade

gunicorn app:app -w ${WORKERS} -k gevent -b 0.0.0.0:5000