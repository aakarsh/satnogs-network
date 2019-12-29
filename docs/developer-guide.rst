Developer Guide
===============

Thank you for your interest in developing SatNOGS!
There are always bugs to file; bugs to fix in code; improvements to be made to the documentation; and more.

The below instructions are for software developers who want to work on `satnogs-network code <http://gitlab.com/librespacefoundation/satnogs/satnogs-network>`_.


Workflow
--------

When you want to start developing for SatNOGS, you should :doc:`follow the installation instructions <installation>`, then...

#. Read CONTRIBUTING.md file carefully.

#. Fork the `upstream repository <https://gitlab.com/librespacefoundation/satnogs/satnogs-network/forks/new>`_ in GitLab.

#. Code!

#. Test the changes and fix any errors by running `tox <https://tox.readthedocs.io/en/latest/>`_.

#. Commit changes to the code!

#. When you're done, push your changes to your fork.

#. Issue a merge request on Gitlab.

#. Wait to hear from one of the core developers.

If you're asked to change your commit message or code, you can amend or rebase and then force push.

If you need more Git expertise, a good resource is the `Git book <http://git-scm.com/book>`_.


Templates
---------

satnogs-network uses `Django's template engine <https://docs.djangoproject.com/en/dev/topics/templates/>`_ templates.


Frontend development
--------------------

Third-party static assets are not included in this repository.
The frontend dependencies are managed with ``npm``.
Development tasks like the copying of assets, code linting and tests are managed with ``gulp``.

To download third-party static assets:

#. Install dependencies with ``npm``::

     $ npm install

#. Test and copy the newly downlodaded static assets::

     $ ./node_modules/.bin/gulp

To add new or remove existing third-party static assets:

#. Install a new dependency::

     $ npm install <package>

#. Uninstall an existing dependency::

     $ npm uninstall <package>

#. Copy the newly downlodaded static assets::

     $ ./node_modules/.bin/gulp assets


Simulating station heartbeats
-----------------------------

Only stations which have been seen by the server in the last hour (by default, can be customized by `STATION_HEARTBEAT_TIME`) are taken into consideration when scheduling observations.
In order to simulate an heartbeat of the stations 7, 23 and 42, the following command can be used::

  $ docker-compose exec web django-admin update_station_last_seen 7 23 42


Manually run a celery tasks
---------------------------

The following procedure can be used to manually run celery tasks in the local (docker-based) development environment:

- Setup local dev env (docker).
- Start django shell
  ```
  docker-compose exec web django-admin shell
  ```
- Run an asnyc task and check if it succeeded.
  ```
  > from network.base.tasks import update_all_tle
  > task = update_all_tle.delay()
  > assert(task.ready())
  ```
- (optional) Check the celery log for the task output:
  ```
  docker-compose logs celery
  ```

Coding Style
------------

Follow the `PEP8 <http://www.python.org/dev/peps/pep-0008/>`_ and `PEP257 <http://www.python.org/dev/peps/pep-0257/#multi-line-docstrings>`_ Style Guides.


What to work on
---------------
You can check `open issues <https://gitlab.com/librespacefoundation/satnogs/satnogs-network/issues>`_.
We regurarly open issues for tracking new features. You pick one and start coding.
