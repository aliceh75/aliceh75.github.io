Title: Testing Python asyncio code with SSL
Date: 2018-03-01
Slug: testing-asyncio-with-ssl
Tags: python, async, asyncio
Summary: The [asyncio](https://docs.python.org/3/library/asyncio.html) library introduced in Python 3.4 allows us to write concurrent code running, amongst other things, network clients and servers. Here I show how to unit-test asyncio code to ensure it is possible to use it over an SSL connection.

The [asyncio](https://docs.python.org/3/library/asyncio.html) library introduced in Python 3.4 allows us to write concurrent code running, amongst other things, network clients and servers. Here I show how to unit-test asyncio code to ensure it is possible to use it over an SSL connection. 

The first thing to note is that asyncio handles SSL transparently - so unit tests only need to ensure the SSL connection can happen, they don't need to repeat all the tests over SSL. Also note I'm using the [async/await](https://docs.python.org/3/library/asyncio-task.html) syntax introduced in Python 3.5.

So let's assume we have a client library with the following code (this example merely sends a line of data, reads one line of reply and returns it):

```python
import asyncio
import re

class DataFetcher():
      def __init__(self, host, port, ssl_context=None):
          self.host = host
          self.port = port
          self.ssl_context = ssl_context
  
      async def get_the_data(self, the_question):
          reader, writer = await asyncio.open_connection(
              self.host, self.port, ssl=self.ssl_context
          )
          writer.write(the_question.strip().encode('utf-8') + b"\n")
          await writer.drain()
  
          data = await reader.readline()
          writer.close()
          return str(data, 'utf-8').strip()
```

As you can see the client library allows for an optional `ssl_context`, which should be an instance of [ssl.SSLContext](https://docs.python.org/3/library/ssl.html#ssl.SSLContext) typically created using [ssl.create_default_context](https://docs.python.org/3/library/ssl.html#ssl.create_default_context).

Now let's assume that, for the purpose of unit testing, you've created a mock server that implements enough of the protocol you're working with for your purpose (in this instance, our server is an echo server which upcases it's input):

```python
import asyncio

class MockDataServer():
      def __init__(self, host, port, ssl_context=None):
          self.host = host
          self.port = port
          self.ssl_context = ssl_context
  
      def start(self):
          return asyncio.start_server(self.handle_connection, self.host, self.port, ssl=self.ssl_context)
  
      async def handle_connection(self, reader, writer):
          data = await reader.readline()
          data = str(data, 'utf-8')
          writer.write(data.strip().upper().encode('utf-8') + b"\n")
          await writer.drain()
          writer.close()
```

Similarly this takes an optional `ssl_context`. Note that as this is a server component the ssl context would need to be created with a valid certificate. There are multiple ways to do this:

1. Include a self-signed certificate in your test suites;
2. Generate a self-signed certificate while running the tests using command line tools such as [OpenSSL](https://www.openssl.org/);
3. Generate a self-signed certificate while running the tests using the [pyOpenSSL python library](https://pyopenssl.org/en/stable/);

The first option works (you can set an expiry year of 9999 in your certificate), though limits your test's ability to customise the certificate; the second option requires the test host to have the OpenSSL command line tool installed, and has the risk of that tool's parameters changing. So here I will look at the third option.

The following code uses [pyOpenSSL](https://pyopenssl.org/en/stable/) to generate a self signed certificate in a temporary file, returning both the certificate and the key file (please feel free to re-use this code in your own projects):

```python
import os
import tempfile

from OpenSSL import crypto


def create_temp_self_signed_cert():
    """ Create a self signed SSL certificate in temporary files for host
        'localhost'

    Returns a tuple containing the certificate file name and the key
    file name.

    It is the caller's responsibility to delete the files after use
    """
    # create a key pair
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 1024)

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "UK"
    cert.get_subject().ST = "London"
    cert.get_subject().L = "London"
    cert.get_subject().O = "myapp"
    cert.get_subject().OU = "myapp"
    cert.get_subject().CN = 'localhost'
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha1')

    # Save certificate in temporary file
    (cert_file_fd, cert_file_name) = tempfile.mkstemp(suffix='.crt', prefix='cert')
    cert_file = os.fdopen(cert_file_fd, 'wb')
    cert_file.write(
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    )
    cert_file.close()

    # Save key in temporary file
    (key_file_fd, key_file_name) = tempfile.mkstemp(suffix='.key', prefix='cert')
    key_file = os.fdopen(key_file_fd, 'wb')
    key_file.write(
        crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
    )
    key_file.close()

    # Return file names
    return (cert_file_name, key_file_name)
```

With this function at hand we can now write a test that ensures it's possible to use SSL with our asyncio library. Note that this test uses the [asynctest](https://asynctest.readthedocs.io/en/latest/) library to write asyncio tests.


```python
import asyncio
import asynctest
import ssl
import os

class TestSSLDataFetcher(asynctest.TestCase):
      def setUp(self):
          # Create the certificate file and key
          self._cert_file, self._cert_key = create_temp_self_signed_cert()
  
          # Start the mock server, with an SSL context using our certificate
          ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
          ssl_context.load_cert_chain(self._cert_file, self._cert_key)
          self._server = self.loop.run_until_complete(
              MockDataServer(host='localhost', port=1234, ssl_context=ssl_context).start()
          )
  
      async def tearDown(self):
          self._server.close()
          await asyncio.wait_for(self._server.wait_closed(), 1)
          os.remove(self._cert_file)
          os.remove(self._cert_key)
  
      async def test_client_can_connect_to_server_over_ssl(self):
          ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self._cert_file)
          fetcher = DataFetcher(host='localhost', port=1234, ssl_context=ssl_context)
          data = await fetcher.get_the_data('hello')
          assert data == 'HELLO'
  
      async def test_invalid_certificate_raises_error(self):
          other_cert_file, other_cert_key = create_temp_self_signed_cert()
          ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=other_cert_file)
          fetcher = DataFetcher(host='localhost', port=1234, ssl_context=ssl_context)
          try:
              await fetcher.get_the_data('hello')
          except ssl.SSLError:
              assert True
          else:
              assert False
```

If these tests pass you know your client library can communicate over SSL if required. As it's handled transparently by asyncio (and if you trust asyncio itself is well tested), you don't need to repeat all your other tests under SSL - just making sure a connection can happen is enough.
