Title: Python asynchronous cooperative mode
Date: 2018-06-30
Slug: python-asynchronous-cooperative-mode
Tags: python, async
Summary: With the addition of [asyncio](https://docs.python.org/3.5/library/asyncio.html) in the Python 3.4 stdlib and the [async/await syntax](https://www.python.org/dev/peps/pep-0492/) in Python 3.5, co-operative asynchronous programing is now an official part of Python. The co-operative asynchronous mode is not complicated to use - but the Python ecosystem is a bit confusing at first. Here I give an introduction to asynchronous programing concepts and eco-system in Python. 

With the addition of [asyncio](https://docs.python.org/3.5/library/asyncio.html) in the Python 3.4 stdlib and the [async/await syntax](https://www.python.org/dev/peps/pep-0492/) in Python 3.5, co-operative asynchronous programing is now an official part of Python. The co-operative asynchronous mode is not complicated to use - but the Python ecosystem is a bit confusing at first. Here I give an introduction to asynchronous programing concepts and eco-system in Python. 

## Definitions

- _asynchronous_ means you don't wait on blocking operations - eg. file reads or http connections. You allow other code to run while you wait;

- _co-operative_ means that the code decides when it's time to pause (on some IO operation in most cases) and allow other code to run. There isn't a scheduler to take control away.

## Single threaded

The point of Python's asynchronous mode is that it's single threaded. All the logic of switching between tasks is done in Python, in a single OS thread. The typical use case is for concurrent services that serve multiple requests at the same time and are IO bound (ie. where most of the time is spent waiting on IO operations, such as file reads, database queries or remote API queries) - eg. web servers.

Because each request spends most of it's time waiting on IO, many requests can be served on a single thread - avoiding thread context switches which are comparatively expensive (or process context switches which are even more expensive). The idea of implementing web servers in that way has been around for a while, and was popularised by [Node.js](https://nodejs.org)

It's worth noting some Python asynchronous libraries will use threads in the background - for examples [aiofiles](https://pypi.org/project/aiofiles/) does that because of [operating system limitations](https://github.com/python/asyncio/wiki/ThirdParty#filesystem]), so using asynchronous libraries does not completely remove the need for threads ([Node.js does the same](https://stackoverflow.com/questions/20346097/does-node-js-use-threads-thread-pool-internally#20346545)).

## Async/Await syntax

Historically in NodeJS asynchronicity was implemented using either callbacks or [Promises](https://en.wikipedia.org/wiki/Promise_(programming)). Callbacks notoriously make code hard to reason about, and while Promises and Futures partly help with that they still rely on code being invoked separately later, making reasoning sometimes difficult. Nathaniel J. Smith's post "[Notes on structured concurrency, or: Go statement considered harmful](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/)" goes some length into looking at why code that relies on callbacks, promises or futures is ultimately harder to reason about.

The `async/await` syntax provides an alternative. The syntax exists in various languages amongst which C#, Python and Javascript (in ES7, though people already use it thanks to transpilers).

In Python it is used like this:

    :::python
    async def my_function():
        url = prepare_my_url()
        result = await make_some_http_request(url)
        return process_the_result(result) 

Where:

- `async def` means the function is one that might pause itself by calling `await`;
- `await make_somt_http_request(url)` means that the function will pause execution at that point, to be resumed only after the `make_some_http_request` returns a result.

Internally the call to `await` is actually run using `yield from` - it uses the same mechanisms as `yield` to pause the execution of a function.

## The Python eco-system

While the syntax is simple, the eco-system is a bit complicated at first. Here are some points worth noting:

- The `async/await` *keywords* were introduced in Python 3.5. These are just keywords, they don't do much of their own - you need an asynchronous library to make the thing happen;

- The Python stdlib asynchronous library - [asyncio](https://docs.python.org/3.5/library/asyncio.html) - was introduced in Python 3.4, before the `async/await` keywords. So you'll see some documentation that refers to the old syntax (`@coroutine` decorator instead of `async def`, and `yield from` instead of `await`);

- Libraries must be designed to be non-blocking. You can't use the stdlib file operations, because they are blocking. You need to use an asynchronous file library instead. You can't use the stdlib http module because it's blocking, you need an asynchronous http library, etc. This means all IO libraries must be duplicated, which doesn't sound ideal, but is necessary if you want true single-threaded non-blocking IO;

- When using [asyncio](https://docs.python.org/3.5/library/asyncio.html) (or, presumably, any low level async library) you have to create the event loop, add tasks to it, and run the event loop yourself. People with some Javascript experience will be used to this being handled by the execution environment - in Python it's down to libraries to do it. The advantage is that people can implement this in different ways depending on their needs (see next point). Higher level frameworks (such as ready-made async web frameworks) might do this for you;

- There are alternatives to asyncio. As all Python itself defines are some keywords, anyone can write an asynchronous framework. Two possible alternatives are [curio](https://github.com/dabeaz/curio) and [trio](https://trio.readthedocs.io/en/latest/). You also have libraries that replace parts of the system only - for example [uvloop](https://github.com/MagicStack/uvloop) is a faster drop-in replacement for asyncio's event loop.

## Further reading

There is, of course, the Python documentation as well as numerous tutorials on-line which are easy to find. In addition to those, here are a few posts that I have found interesting while trying to understand how asynchronous programing works in Python, it's background and it's problems:

- [Comparison of async await syntax in .NET, Python and JavaScript](https://robertoprevato.github.io/Comparisons-of-async-await/)
- [Some thoughts on asynchronous API design in a post-async/await world](https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/)
- [Notes on structured concurrency, or: Go statement considered harmful](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/)
