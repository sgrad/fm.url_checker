# fm.url_checker
Sample producer consumer application

# Technology choices
Flask producer -> rabbitmq queue -> asyncio consumer 
## Producer
Went with a Flask API, it's mature, stable and has a lot of extensibility. Another Option would be to use something
like FastAPI (ASGI on top of uvicorn) it is a lot faster than Flask, but it's a bit young and doesn't have as many
features and libs available as Flask.

The other choice here was to use connexion, which handles the documentation, mapping and data validation for the API.

## Consumer
Celery is the defacto standard when it comes to RabbitMQ in python, but I'd try to avoid it as much as possible because:
 - it isn't Python3.7 compatible (https://github.com/celery/celery/issues/4500)
 - it has a lot of nice features which end up creating a very complex framework, with a lot of "magic" that is prone to 
 weird bugs and in this particular case all was needed was a simple producer consumer 
 - the project is now quite dead, the original developer hasn't committed anything in almost two years and the current 
 active developers are barely able to tackle the known bugs
 
 So I chose a simple implementation based on asyncio and aio-pika. Pika is the official supported library by RabbitMQ 
 and aio-pika only provides non-blocking io, leaving all the logic in the base library.
 
## Deployment
Docker containers offer a lot of advantages like:
 - easy portability
 - easy to create multiple environments (dev, test, prod, etc.)
 - no state, which reduces bugs
  
For the sake of this example the rabbitmq server is also running in docker, in a real world environment I'd have that 
running directly on AWS instances or bare metal


# Issues
This is a proof of concept and nowhere near a proper production ready setup, hence there are some issues:

The app is configured with a single producer and a single consumer, normally there would be at least two of each and in 
the case of the producer there would be a load balancer in front (Kubnernetes, AWS ELB, HA Proxy, etc)

Besides redundancy (consumer dies, producer fills up the queue) there's another issue with running a single consumer, 
with the current configuration, if a task takes a long time all other jobs will end up loading the rabbitmq queue. 
There are a couple of ways to avoid this:
 - change the prefetch count in the worker to pull more messages, which will work ok until the worker get's saturated 
 with multiple long running tasks (plus memory concerns, etc)
 - add a timeout to the tasks
 - use multiple workers
 - all of the above for best results
 
 The other issue is with the tasks themselves, if the consumer dies during the execution of a task the task will be put 
 back in the queue and processed by another worker. But, currently, if a task fails for any reason it's discarded which
 is not entirely desirable. If the website it's trying to read is down, there can be a retry mechanism. The easiest way 
 to do this is by requeuing the message in a special delay queue that has a ttl (either per queue or per message) and a 
 dead-letter back to the original queue. This in combination with a requeue counter (message headers and/or amqp 
 basic settings) can achieve a reliable exponential back-off retry system. Jobs that still fail after this can be put in
 a separate dead-letter queue for human intervention or different automatic processing.
 
 ## Running
 To run the project all you need to do is have docker with docker-compose set up and run:
 `docker-compose up`. This will build and start the required containers and print to stdout all the logging output from 
 the containers.
 
 In order to develop you need to setup the python virtual environment, from the project dir run: `pipenv install --dev`
 
 For the API documentation, once the producer is started, go to http://localhost:8080/ui/
 
 
 ## Notes
 Normally the producer and consumer would be in separate repos, and any shared code in separate libraries. For the sake 
 of brevity I've included both in this repo but still kept them separate.
 
 To run the producer in development mode run the pipenv shell and in it run the `producer/run.py` file. All paths are 
 set up to be ran from the main project directory.
