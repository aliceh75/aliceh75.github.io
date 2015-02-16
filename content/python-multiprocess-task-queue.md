Title: A Python multi-process task queue
Date: 2014-07-04
Slug: python-multiprocess-task-queue
Tags: python
Summary: Looking to integrate a task queue manager in a service I was implementing, I discarded existing task queues and libraries as over complex for my need and implemented a simple solution based on existing examples found online.

Overview
--------
I was implementing a service (in Python) that enqueues and run specific tasks. [There are plenty of task queue managers out there](http://queues.io/), but they all require an external service - either the whole stack is external, or they are Python libraries but require an external service to store the queue (such as [redis](http://redis.io/)).

My needs being simple, I searched online and found a number of simple solutions based on Pythons' [multiprocessing](https://docs.python.org/2/library/multiprocessing.html) and decided to start from those to implement a simple solution.

As my solution builds on the existing simple solutions I found, I thought I would share it here.


Simple approach
---------------

The basic approach using multiprocessing (the one I found explained on various sites) looks something like this:

    :::python
    import multiprocessing

    def _worker(queue):
        while True:
            task = queue.get()
            task.run()

    class TaskQueue():
        def __init__(self, workers):
            self._queue = multiprocessing.Queue()
            self._pool = multiprocessing.Pool(workers, _worker, (self._queue,))
        
        def add(self, task):
            self._queue.put(task)

And that's it - it is really simple to implement. The tasks need to be an object with a `run` method, for instance:

    :::python
    class MyTask():
        def __init__(self, param):
            # This is run on the main process, when the task is crated
            self.param = param

        def run(self):
            # This is run on the child process. We can do something with param
            # (note that we must be able to pickle param)
            pass

Managing the workers
--------------------

There are a number of things I wanted that do not work with this approach however:

- I wanted workers to stop after a certain amount of requests;
- I wanted to be able to terminate the workers.

To implement this with the previous approach of using a `Queue` requires a bit of work. The workers would have to have a loop to exit after a certain number of requests; we'd have to be able to instruct the workers to terminate, and we would need a separate thread to restart workers that have stopped.

Instead we can use `multiprocessing.Pool` - it allows us to specify the number of requests served by each worker by specifying `maxtasksperchild`. Our workers cannot be an infinite loop anymore however, so we need another way to send parameters to the workers. Calling `apply_async` for each task does just that - and `multiprocessing.Pool` handles the queueing for us. Arguably this approach is actually simpler than the previous one - though not one I found online.

`Pool.close` and `Pool.terminate` can be used to write a `terminate` method. So the implementation would now be:

    :::python
    def _worker(task):
        task.run()
        return True


    class TaskQueue():
        def __init__(self, worker_count, requests_per_worker=None):
            self._pool = multiprocessing.Pool(worker_count, maxtasksperchild=requests_per_worker)

        def add(self, task):
            self._pool.apply_async(_worker, (task,))

    def terminate(self, timeout=5):
        self._pool.close()
        time.sleep(timeout)
        self._pool.terminate()
        self._pool.join()


Note the implementation of terminate here is a bit naive. We don't have a way to tell when a worker has stopped, so `terminate` will sleep even if all the tasks closed immediately. We will improve on this later on.

Tracking operations
-------------------

We'd like to be able to tell how many tasks are in the queue, and how many have been processed altogether. For this we'll use `apply_async`'s return object which tells us when a task has finished (as well as it's return value, though we don't care about this in the current implementation). This will also allow us to implement `terminate` properly. The implementation is straightforward - though I'll include it here for completeness.

    :::python
    class TaskQueue():
        def __init__(self, worker_count, requests_per_worker=None):
            self._pool = multiprocessing.Pool(worker_count, maxtasksperchild=requests_per_worker)
            self._tasks = []
            self._processed_count = 0
            self._open = True

        def add(self, task):
            r = self._pool.apply_async(_worker, (task,))
            self._tasks.append(r)
            # Call flush here to ensure we clean up even if length/processed are never called.
            self._flush()

        def length(self):
            self._flush()
            return len(self._tasks)

        def processed(self):
            self._flush()
            return self._processed_count

        def terminate(self, timeout=5):
            self._pool.close()
            self._flush()
            time_waited = 0
            while len(self._tasks) > 0 and time_waited < timeout:
                time.sleep(0.1)
                time_waited += 0.1
                self._flush()
            self._pool.terminate()
            self._pool.join()

        def _flush(self):
            new_tasks = []
            for t in self._tasks:
                if not t.ready():
                    new_tasks.append(t)
                else:
                    self._processed_count += 1
            self._tasks = new_tasks

Note that `length` returns the number of items that are either in the queue, or currently being processed. This is fine for my use case - to make the distinction between the queues we'd have to track (using a `Queue`) when each worker actually starts processing the task.

Logging
-------

We want to log what's happening - when workers start, when they are killed, when they start and finish processing tasks. We can't use the normal logger classes as they do not work across processes - instead we need to use the logger provided by `multiprocessing.get_logger`. Setting the log level to `INFO` will ensure `multiprocessing` logs when the workers start and end, and we can log when tasks start and end ourselves in `_worker`:

    :::python
    def _worker(task):
        logger = multiprocessing.get_logger()
        id = os.getpid()
        try:
            desc = str(task)
        except Exception as e:
            logger.error("Worker {} failed to get task description. {}".format(id, format_exc()))
            desc = '(unknown)'
        logger.info("Worker {} processing task {}".format(id, desc))
        try:
            task.run()
        except Exception as e:
            logger.error("Worker {} failed task {}. {}".format(id, desc, format_exc()))
        logger.info("Worker {} done with task {}".format(id, desc, e))
        return True

Note that we use `format_exc` (import it from `traceback`) to display the full backtrace of any exception that makes it that far - there is nothing above us, and the exception will get lost if we don't display it.

If you are embedding this in a larger application, you may not have the opportunity to change the application's logger object to use the multiprocessing one (so that all logs go to the same place). Assuming you can set the log handler used by the application you can deal with this issue by implementing a log handler which forwards logs to the multiprocessing logger:

    :::python
    import logging
    import multiprocessing


    class MultiprocessingLogHandler(logging.Handler):
        """A log handler that forwards messages to the multiprocessing logger."""
        def emit(self, record):
            logger = multiprocessing.get_logger()
            logger.handle(record)


You can then replace the application's log handler with an instance of this one. For example in Flask:

    :::python
    # Set up the multiprocessing logger
    m_logger = multiprocessing.get_logger()
    m_logger.setLevel(logging.INFO)
    m_logger.addHandler(login.StreamHandler(sys.stderr))

    # Remove any existing log handlers in the application handler
    while len(app.logger.handlers) > 0:
        app.logger.removeHandler(app.logger.handlers[0])

    # And add our custom handler to the application logger
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(MultiprocessingLogHandler())
    
Testing
-------

I have written a test suite (using nosetest) for this. It is not based on the exact version of the code described here, but should give you a good head start for writing tests for your own implementation. You can find it on [GitHub](https://github.com/NaturalHistoryMuseum/ckanpackager/blob/master/ckanpackager/tests/queue.py).

Conclusion
----------

If your requirements are simple enough then it's easier to use Python built-in libraries to implement a queue in this way. Of course it lacks many features of a more full fledged solution: email error reporting, queue persistence, scheduling, etc. If these are important to you, then you should probably use an existing solution!

