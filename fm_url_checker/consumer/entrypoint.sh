#!/bin/sh

echo "Waiting for RabbitMQ to start"
sleep 10
exec python fm_url_checker/consumer/run.py