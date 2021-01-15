Installation
============


Requirements and info
---------------------

**Python**: CPython 3.6+

**Operating system**: Linux

**Prerequisites**: `docker-compose <https://docs.docker.com/compose/install/>`_ (recommended) or `virtualenv <https://pypi.org/project/virtualenv/>`_, `npm <https://www.npmjs.com/get-npm>`_.

**Git repository**: https://gitlab.com/librespacefoundation/satnogs/satnogs-network.git


Clone
-----

Consult the `GitLab page <https://gitlab.com/librespacefoundation/satnogs/satnogs-network>`_ on how to clone the repository.


Configuration
-------------

Set your environmental variables::

  $ cp env-dist .env
  $ ${EDITOR} .env


Installation
------------


Quick install
^^^^^^^^^^^^^

The recommended quick install method is to use **Docker Compose**.
This method will start separate containers for Django runserver, Celery, MariaDB and Redis.

The **Virtualenv** quick install method lacks a task queue, uses SQLite as a database and memcached for caching.
It is only recommended for frontend development.

Docker Compose (recommended)
""""""""""""""""""""""""""""

Change into the cloned repository directory::

  $ cd <path/to/clone>

To run SatNOGS Network service::

  $ ./satnogs.sh up

To stop SatNOGS Network service::

  $ ./satnogs.sh down

To clean-up SatNOGS Network installation::

  $ ./satnogs.sh clean


Virtualenv
""""""""""

This installation method is recommended only for frontend development purposeses.

Change into cloned repository directory::

  $ cd <path/to/clone>

To run SatNOGS Network in a virtualenv::

  $ ./satnogs.sh develop

To remove SatNOGS Network virtualenv::

  $ ./satnogs.sh remove


Production install
^^^^^^^^^^^^^^^^^^

For production installations, check `Deploying Django <https://docs.djangoproject.com/en/3.1/howto/deployment/>`_.


Gunicorn
""""""""

If ``gunicorn`` is used as the WSGI server then to start the application use::

  $ ./bin/djangoctl.sh run

and to bring Celery up::

  $ ./bin/djangoctl.sh run_celery
