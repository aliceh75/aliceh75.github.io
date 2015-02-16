Title: Interrupting urlopen in Python
Date: 2014-07-25
Slug: interrupting-urlopen-in-python
Tags: python
Summary: While the Python ecosystem is replete with libraries for fetching data over the web, none of them give you an easy way to interrupt requests before the queried server has returned the response headers. As more often than not servers will only output response headers once they have the full response at hand, this does not make it possible to release resources early. Here I show a possible implementation based on sockets and Httplib.

Overview
--------

While the Python ecosystem is replete with libraries for fetching data over the web, none of them give you an easy way to interrupt requests before the queried server has returned the response headers. As more often than not servers will only output response headers once they have the full response at hand, this does not make it possible to release resources early.

Let's say I want to get a resource from a web server. This resource is not static, and takes a long time to generate - several seconds. It is possible that within those few seconds I decide I do not want the resource any more. To ease the load on the web server, I want to close the connection - I know the server will detect this and stop it's work.

As is often the case, this web server doesn't output anything (including response headers) until it has the full response at hand. Unfortunately, while most Python libraries for fetching web content allow us to split the work in multiple calls (send request, read data, close request) the initial send request typically does not return until the response headers are available. This is the case for [urlopen](https://docs.python.org/2/library/urllib2.html), [httplib](https://docs.python.org/2/library/httplib.html) and, as far as I call tell, [request](http://docs.python-requests.org/en/latest/)

Sending a request
-----------------

In fact the highest level library that will allow us to do this is [socket](https://docs.python.org/2/library/socket.html). This means we are going to build the HTTP request ourselves - this is straightforward, though for more complicated cases `httplib` might be useful. The following method will build an HTTP GET request:

    :::python
    from urlparse import urlparse
    def http_request(url):
        url_p = urlparse(url)
        if url_p.path:
          path = url_p.path
        else:
          path = '/'
        if url_p.query:
          path = path + '?' + url_p.query
        request = [
            "GET {} HTTP/1.1".format(path),
            "Host: {}".format(url_p.netloc),
            "Connection: close",
            "User-Agent: here-be-dragrons/0.1"
        ]
        return "\r\n".join(request) + "\r\n\r\n"

Note that the request must end with an empty line, and that the line separator should be "\r\n". You can add more headers there as needed, though those are sufficient.

Now that we have a request string, we need to send it. Using the socket library this is straightforward:

    :::python
    import socket
    def send_request(url):
        url_p = urlparse(url)
        if ':' in url_p.netloc:
          (host, port) = url_p.netloc.split(':')
        else:
          host = url_p.netloc
          port = 80

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, int(port))
            sock.sendall(http_request(url))
        except Exception as e:
            sock.close()
            raise e

And that's it, the request has been send. To check whether the reply has arrived we can use the [select](https://docs.python.org/2/library/select.html) library:

    :::python
    import socket

    def wait_for_request(sock, test_interrupt, sleep_time=0.1)
        rl = []
        while (len(rl) == 0):
           test_interrupt()
           rl, wl, xl = select.select([self._sock], [], [], sleep_time)

`test_interrupt` is a function which will raise an exception should the query be interrupted. The caller should make sure to close the socket properly when this happens.

Reading the result
------------------

Once the data is ready, we can read it with `socket.recv`. This however means we would have to parse the HTTP request ourselves. Depending on which server we are contacting, this is a bit more difficult than generating the HTTP query was. Instead of parsing it ourselves, we can us [`httplib.HTTPResponse`](https://docs.python.org/2/library/httplib.html#httplib.HTTPResponse). While the documentation suggests this class is not instantiated directly by the user, it doesn't say we shouldn't - the class' definition is documented and, lo and behold, the first argument to that is a socket. Using this reading the server response is easy:

    :::python
    from httplib import HTTPResponse
    def read_response(sock):
      r = HTTPResponse(sock)
      try:
        r.begin()
        status = r.status
        body = r.read()
      finally:
        r.close() # Note that this does not close the socket.
      return (status, body)

That's all - we can now get the response status code and the response body. A complete example using the various functions we've implemented:

    :::python
    class GiveUp(Exception):
      pass

    def test_interrupt():
        if event_has_happened():
          raise GiveUp()
    
    sock = send_request('http://example.com/big-data-please?quantity=lots')
    try:
        wait_for_request(sock, test_interrupt)
        (status, body) = read_response(sock)
        print "We got response code " + str(status) + " and body " + str(body)
    finally:
        sock.close()
      
Conclusion
----------

Python libraries are not always the best when it come to this kind of low-level optimization but with a bit of effort it is usually possible to achieve what we want.



