Title: A look into Docker concepts
Date: 2015-02-12
Slug: a-look-into-docker-concepts
Tags: docker
Summary: [Docker](https://www.docker.com) is a tool to help in the deployment of applications across host systems. Virtualization, union file systems, image registries, orchestration services - while Docker is a useful tool for staging and deployment, there is a learning curve to get to grips with the whole ecosystem.

[Docker](https://www.docker.com) is a tool to help in the deployment of applications across host systems. Virtualization, union file systems, image registries, orchestration services - while Docker is a useful tool for staging and deployment, there is a learning curve to get to grips with the whole ecosystem.

This is not an introduction to Docker, and it is not a tutorial. This is an ad-hoc collection of knowledge pulled from numerous sources across the internet,  aimed at people who've started looking into Docker, possibly created their first containers - and are trying to understand what is happening.

This was written based on Docker 1.4.1.

Virtualization
--------------

The first, and most important point, to understand is that Docker containers are not virtual machines. Docker uses virtualization technologies to separate process space, memory and file system between containers - but a Docker container does not contain it's own operating system. It uses the host's operating system.

This means Docker containers are far more efficient than virtual machines - you do not need to simulate the hardware, and you do not need to run another operating system on top of the host. You also do not need to "boot" a container - the startup times are very fast. A container does not automatically start any services - if you want to run a service inside a container, you must start it explicitly (see *Running a container* for more on this topic).

If you want to deploy an application that has a hard dependency on a kernel feature, then you must ensure the host kernel has the feature. But in practice this is something quite rare.

Union File System
-----------------

Docker uses [union mount](http://en.wikipedia.org/wiki/Union_mount) file systems to create it's containers. The idea is that you create an apparent file system based on several file systems layered on top of each other - such that each layer has priority over the layers below. Only the final layer is read/write, all the others being read only.

The advantage of this approach is that containers are actually lightweight. Say you have a host that runs two containers: one running PostgreSQL and one running Apache2. Assuming that you've build both containers on top of a base Ubuntu 12.04 image, then your host will only store a single copy of the Ubuntu 12.04 base layer and use it for both containers.

So your Postgresql container would look like this:
                               
    -- Read/write layer        --  | A read operation will go down through the layers
    -- Postgresql layer        --  | Until it finds a matching file.
    -- Ubuntu 12.04 base layer --  V 

And your Apache2 container would look like this:

    -- Read/write layer        --  | 
    -- Apache2 layer           --  |
    -- Ubuntu 12.04 base layer --  V

Your server would only have one copy of the Ubuntu 12.04 base layer. The other advantage of this approach is that you only need to distribute your custom layers - making your container images much lighter to deploy. Common images, such as the Ubuntu 12.04 base image, are fetched from the [Docker hub](https://hub.docker.com) (You can use Docker's or roll out your own).

Images and containers
---------------------

The second important point to understand is the difference between images and containers. A docker _image_ is a read only layered file system (and meta data). A docker _container_ is build from a docker image, with an additional read/write layer added on top of it.

A docker _image_ is build from the instructions contained in a [Dockerfile](https://docs.docker.com/reference/builder/). While you may pass additional arguments when creating a container, containers are not created from a set of instructions. A container is, in effect, an instance of an image running on a host.

Docker does allow you to get into a running container, download additional packages, change configuration on the fly and so on. You can even export such a container - or create an image from it. This is useful for emergency fixes, but by doing so you circumvent what makes Docker useful. The person who deploys an application should be able to pull a new image from the developer, and use that to replace a running containers without any additional steps. If the container has been modified, then this won't be possible.

So:

- Images should be host independent so you can easily pull an image from any host, and run a container based on that image;
- You do not distribute containers, you distribute images. Containers are created as an instance of an image on a given host;
- You may pass parameters when creating a container to customize it for the current host.

A consequence of this is that containers should not hold any permanent data. This is what [Docker volumes](https://docs.docker.com/userguide/dockervolumes/) are for - you can specify that certain paths are _volumes_ which can, for instance, be mounted from the host. So your Postgresql container would mount it's `/var/lib/postgresql/9.3/main` from the host. You can then remove that container, pull an upgraded image, and create a new container with the same volume mount. This way you upgraded your database server without having to manually install the server and it's dependencies - but you kept your data intact. (See *Data only containers* for more on this topic).

Running a container
-------------------

A container, once again, is not a server. A container represents a single service. When you run a container, it will run the single command you specified under `CMD` in the Dockerfile. When that command exits, the container exits.

This means that this command should not daemonize. Indeed, the "daemonization" part is one of the things docker does for you - running each container in the background. Because many applications daemonize by default, you will often have to specifically instruct them not to. For instance, for a Postgresql server, your `CMD` line might look like:

```
CMD /usr/lib/postgresql/9.3/bin/postgres -D /var/lib/postgresql/9.3/main -c config_file=/etc/postgresql/9.3/main/postgresql.conf
```

Where the `-D` flag instructs Postgresql not to daemonize. Remember, once again, that a Docker container does not contain an OS and does not boot. It means that services are not started automatically - so when you start your container, PostgreSQL will not start on it's own as it would on a virtual machine - you need to indicate that you want it to start. For some applications, that expect services such as syslog, this may be a problem, and you will need to start all required services explicitly.

This does not mean that a container should only run a single process. Indeed one of the great advantages of Docker is that it makes it easy to combine multiple components into a single deployable service. For instance imagine an application that saves it's running status to a file. You want to make the status available via HTTP as well. The options are:

1. Require the user to install a separate web server and serve the status file;
2. Include a lightweight web server within your application to serve the status file;
3. Provide a Docker image which contains both your application and a lightweight web server.

We can clearly see the advantage of the last option: you do not require extra deployment steps from your user, and you also do not need to add an HTTP service within your application.

To do this however, we need to add within the container a way to manage our multiple processes - remember the container does not run any startup service. There are numerous ways to achieve this - a commonly used tool is [supervisord](http://supervisord.org/). To do this:

- Ensure supervisor is included in the image (e.g.. `RUN apt-get install -y supervisord`);
- Define each process you want to run in `supervisord.conf` (and copy that into the image);
- Start your container with `CMD ["/usr/bin/supervisord"]`

You can read more about this in [Using Supervisor with Docker](https://docs.docker.com/articles/using_supervisord/)

A last note on running containers: The `docker run` command can be misleading because it does two things at once. In effect it first creates (and name) a container; and it then starts this container. It is the equivalent of running `docker create` followed by `docker start`.

Container logs
--------------

So we keep the data outside the container - what about logs? Well remembering that a container runs a single process, Docker allows you access to that process' stdout and stderr by doing `docker logs <container>`. So the easiest approach is to get your dockerized application to send it's log to stdout and stderr. If you are using supervisor, you will need to setup your entries in `supervisord.conf` to redirect their output to the supervisord output.

Data only containers
--------------------

Mounting the host file system in the container can have it's disadvantages - in particular when it comes to mapping uids, gids and permissions. A commonly used approach is [data only containers](http://container42.com/2013/12/16/persistent-volumes-with-docker-container-as-volume-pattern/) - using a container which is used only to store data. To do this:

- Ensure that the volumes are declared in the base image using the `VOLUME` setting in your Dockerfile;
- Create a container using the same base image as the container you want to run (the data only container);
- Create your actual container specifying `--volumes-from=<data only container>`.

Your container will run using the volumes from the specified data container. There are two advantages to this approach:

- Since you are using the same base image, uids, gids and permissions will be the same. Also you will save space by not needing a different image;
- You can upgrade your application container - the data only container is persisting the actual data.

The data is still, of course, stored on the host - within Docker's file hierarchy. But you do not need to worry about uids, gids or permissions. The only downside of this approach is that the volumes will only persist as long as the data container (or another container) are using them. So you have to be extra careful when deleting containers.

Connecting containers and orchestration services
------------------------------------------------

Images should always be host independent - the whole point being to make deployment easier. We do however need to get our containers to talk to each other! There are multiple approaches:

### Docker links

If you containers are running on the same host, you can use [Docker Links](https://docs.docker.com/userguide/dockerlinks/). This allows you to add, when creating a container, entries in `/etc/hosts` that map to existing containers. So for example I can build a PostgreSQL slave server image that replicates from a master called "postgres-master". When creating the slave container, I would then specify `--link <master container name>:postgres-master`. My container would then have an entry in `/etc/hosts` that links to the master server container.

The advantage of this approach is that your containers (not just the images) are host independent. The downside is that it only works if all the containers are running on the same host.

One approach to linking containers across multiple hosts without using an orchestration service is to use [ambassador containers](https://docs.docker.com/articles/ambassador_pattern_linking/) - containers that proxy requests between two containers. This way if one container moves host, you only need to reconfigure the proxy containers, and you can leave the application containers intact.

### Container configuration

Sometimes links don't work - for instance in a PostgreSQL server you might want to specify which IP addresses are allowed to connect to the server by specifying an IP address and a netmask. One approach to do this is to use a custom entry point in your docker. If you specify `ENTRYPOINT ["/usr/local/bin/run.sh"]` in your Dockerfile, the script `run.sh` will be the base command that starts you container. You can then pass additional parameters to that script, for instance the IP address and netmask. The `run.sh` script would take care of allowing the given network before starting PostgreSQL. Such a container would be created by doing:

```
   docker create postgres_image 192.168.0.0/24
```

This is a simple approach, and it allows you to run a container that is configured for it's environment based on a generic image. Another similar approach is to use environment variables rather that parameters.

### Orchestration services

Docker links and container configuration only go so far. When you have multiple hosts and multiple containers, it can start to be overwhelming. Orchestration services help manage such setups. There are various third party services such as [flocker](https://github.com/clusterhq/flocker), and [Docker have started rolling their own](http://blog.docker.com/2014/12/announcing-docker-machine-swarm-and-compose-for-orchestrating-distributed-apps/).

These services provide various tools such as:

- Linking containers across hosts;
- Workload placement across multiple Docker hosts;
- Network routing for live migration of containers.

There are other services and other tools out there - this is a fast moving ecosystem.

Docker is an advanced tool
--------------------------

Docker is an environment unto itself, and there are many more things to understand, more gotchas to stumble upon. It is an advanced tool for system administrators who are willing to take the time to understand it. Hopefully this guide will give you a head start!


