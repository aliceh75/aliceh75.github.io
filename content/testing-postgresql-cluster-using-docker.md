Title: Testing a PostgreSQL slave/master cluster using Docker
Date: 2015-01-12
Slug: testing-postgresql-cluster-using-docker
Tags: postgresql, docker, python
Summary: [Docker](https://www.docker.com) is extremely useful for deploying packages, but also for creating environments for running functional tests. Here I show how to easily setup a cluster of PostgreSQL servers in slave/master replication using Docker and drive them using the [Docker Python API](https://github.com/docker/docker-py).

Using Docker for tests
----------------------

Performing functional tests on an application that requires a PostgreSQL server requires installing a single PostgreSQL server. This is generally easy. Performing functional tests on a application that requires a cluster of PostgreSQL servers is, on the other hand, a more difficult task. While Ubuntu and other distributions make it very easy to install a single instance of PostgreSQL, additional instances need to be setup manually. 

Here [Docker](https://www.docker.com) comes in handy: by allowing us to containerize PostgreSQL we can easily run multiple instances on a single host for the purpose of testing. By using the [Docker Python API](https://github.com/docker/docker-py) we can then drive the cluster directly from our test suites.

_Note: The examples in this post are based on [Docker](https://www.docker.com) 1.4.1 and [docker-py](https://github.com/docker/docker-py) 0.7.0_

The master server
-----------------

The master server just needs typical PostgreSQL configuration: `pg_hba.conf` and `postgresql.conf` need to be setup. We will also initialize the master server with the database we want to use for our tests. Here is the [Dockerfile](https://docs.docker.com/reference/builder/):

```
FROM ubuntu:12.04

#
# Install postgresql
#
RUN apt-get update && apt-get install -y postgresql-9.1

#
# Setup configuration & restart
#
RUN /bin/echo -e "                                           \
        host    all             all     0.0.0.0/0   md5   \n \
        host    replication     all     0.0.0.0/0   trust \n \
    " >> /etc/postgresql/9.1/main/pg_hba.conf                \
    && /bin/echo -e "                                        \
        listen_addresses = '*'                            \n \
        port = 5432                                       \n \
        wal_level = hot_standby                           \n \
        max_wal_senders = 3                               \n \
        wal_keep_segments = 256                           \n \
    " >> /etc/postgresql/9.1/main/postgresql.conf            \
    && /etc/init.d/postgresql restart

#
# Create the test suite user and database
#
USER postgres
RUN /etc/init.d/postgresql start                                              \
    && psql -c "CREATE USER testsuite WITH UNENCRYPTED PASSWORD 'testsuite';" \
    && psql -c "CREATE DATABASE testsuite WITH OWNER testsuite;"

EXPOSE 5432
CMD /usr/lib/postgresql/9.1/bin/postgres -D /var/lib/postgresql/9.1/main -c config_file=/etc/postgresql/9.1/main/postgresql.conf
```

The slave servers
-----------------

The slave servers also need `recovery.conf` setup properly, and an additional setup step: we need to start by getting a copy of the master database. Given that the containers will destroyed and re-created for every test suite, we can simply do the copy as part of the startup process. We will be using [Docker links](https://docs.docker.com/userguide/dockerlinks/) to link the containers together, and the master host will be known as `pg_master`. Here is the Dockerfile:

```
FROM ubuntu:12.04

#
# Install postgresql
#
RUN apt-get update && apt-get install -y postgresql-9.1

#
# Setup configuration
#
RUN /bin/echo -e "                                               \
        host    all             all     0.0.0.0/0   md5      \n  \
        host    replication     all     0.0.0.0/0   trust    \n  \
    " >> /etc/postgresql/9.1/main/pg_hba.conf                    \
    && /bin/echo -e "                                            \
        listen_addresses = '*'                               \n  \
        port=5432                                            \n  \
        hot_standby = on                                     \n  \
    " >> /etc/postgresql/9.1/main/postgresql.conf                \
    && /bin/echo -e "                                            \
        standby_mode='on'                                    \n  \
        primary_conninfo = 'host=pg_master port=5432'        \n  \
        trigger_file = '/tmp/trigger_file0'                  \n  \
    " > /var/lib/postgresql/9.1/main/recovery.conf

#
# Add startup script. This will perform initial replication and start
# the server. This must be run with the master server running and linked
# at pg_master
#
COPY run.sh /var/lib/postgresql/9.1/run.sh

USER postgres
EXPOSE 5432
CMD /var/lib/postgresql/9.1/run.sh
```

The script `run.sh` performs the initial database copy, and then starts the server:

```sh
#!/bin/sh
#
# Snapshot the initial database
#
/usr/bin/pg_basebackup -h pg_master -p 5432 -D /var/lib/postgresql/9.1/main2 -U postgres -v -P -x
cp /var/lib/postgresql/9.1/main/recovery.conf /var/lib/postgresql/9.1/main2
cp /var/lib/postgresql/9.1/main/server.* /var/lib/postgresql/9.1/main2
rm -Rf /var/lib/postgresql/9.1/main
mv /var/lib/postgresql/9.1/main2 /var/lib/postgresql/9.1/main
chown -R postgres:postgres /var/lib/postgresql/9.1/main

#
# Start the postgresql server
#
/usr/lib/postgresql/9.1/bin/postgres -D /var/lib/postgresql/9.1/main -c config_file=/etc/postgresql/9.1/main/postgresql.conf
```

Building and running the servers from Python
--------------------------------------------

Using the [Docker Python API](https://github.com/docker/docker-py), we can easily build, start, pause the servers at will. You can install `docker-py` easily:

```
pip install docker-py
```

Here is some example code that builds the servers, starts them and simulates a temporary failure of the master server. It maps the master to port `5432` on the host, and the slaves to `5433`, `5434` and so on.

```python
import json
import docker

slave_count = 2
docker_url = 'unix://var/run/docker.sock'
docker_api_version = '1.14'
master_image_path = '/path/to/folder/containing/master/dockerfile'
slave_image_path = '/path/to/folder/containing/slave/dockerfile'

master = None
slaves = []

def build_image(client, path, tag):
    """ Helper function to build docker images """
    stream = client.build(path=path, tag=tag)
    for line in stream:
        info = json.loads(line)
        if 'error' in info:
            raise Exception(line)
    

# Create Docker client
client = docker.Client(base_url=docker_url, version=docker_api_version)

# Build images
build_image(client, master_image_path, 'test_master')
build_image(client, slave_image_path, 'test_slave')

# Create master container and start it
master = client.create_container(
    image='test_master',
    detach=True,
    ports=[5432],
    name='test_master'
)
client.start_container(
    container=master['Id'],
    port_bindings={5432:5432},
)

# Ensure the master is ready to be replicated
times.sleep(2)

# Create slaves and start them
for i in range(slave_count):
    slaves[i] = client.create_container(
        image='test_slave',
        detach=True,
        ports=[5432],
        name='test_slave_{}'.format(i)
    )
    client.start_container(
        container=slaves[i]['Id'],
        port_bindings={5432: 5433 + i},
        links={'test_master': 'pg_master'}
    )

# Now do some tests...
my_tests_with_servers_up()

# Bring master down temporarily, test again.
client.pause_container(container=master['Id'])
my_tests_with_master_down()

# Bring master back up, test again.
client.unpause_container(container=master['Id'])
my_tests_with_master_back()

# Stop and delete all containers
client.remove(container=master['Id'], force=True)
for i in range(slave_count):
    client.remove(container=slaves[i]['Id'], force=True)
```
