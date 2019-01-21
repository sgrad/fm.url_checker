#!/bin/sh

echo "Waiting for RabbitMQ to start"
sleep 10
exec uwsgi --ini fm_url_checker/producer/conf.ini
