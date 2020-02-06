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

#. Test the changes by `Running the tests locally`_ and fix any errors.

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

#. Install dependencies with ``npm``:

   .. code-block:: bash

     npm install

#. Test and copy the newly downlodaded static assets:

   .. code-block:: bash

     ./node_modules/.bin/gulp

To add new or remove existing third-party static assets:

#. Install a new dependency:

   .. code-block:: bash

     npm install <package>

#. Uninstall an existing dependency:

   .. code-block:: bash

     npm uninstall <package>

#. Copy the newly downlodaded static assets:

   .. code-block:: bash

     ./node_modules/.bin/gulp assets


Simulating station heartbeats
-----------------------------

Only stations which have been seen by the server in the last hour (by default, can be customized by `STATION_HEARTBEAT_TIME`) are taken into consideration when scheduling observations.
In order to simulate an heartbeat of the stations 7, 23 and 42, the following command can be used:

.. code-block:: bash

  docker-compose exec web django-admin update_station_last_seen 7 23 42


Manually run a celery tasks
---------------------------

The following procedure can be used to manually run celery tasks in the local development environment:

#. :doc:`Install the docker-based development environment <installation-docker>`.

#. Start a django-admin shell:

   .. code-block:: bash

    docker-compose exec web django-admin shell

#. Run an asnyc task and check if it succeeded:

   .. code-block:: python

    from network.base.tasks import update_all_tle
    task = update_all_tle.delay()
    assert(task.ready())

#. (optional) Check the celery log for the task output:

   .. code-block:: bash

      docker-compose logs celery


.. tests-guide:

Running the tests locally
-------------------------

To test your changes to the code locally with `tox <https://tox.readthedocs.io/en/latest/>`_ in the same way the CI does you can follow these steps:

#. Setup a new virtual environment (this shouldn't be the same virtual environment you might have created for the :doc:`VirtualEnv Installation <installation-virtualenv>`):

   .. code-block:: bash
   
       mkvirtualenv network-test -a .

#. Install tox in the same version defined by ``GITLAB_CI_PYPI_TOX`` in `.gitlab-ci.yml <https://gitlab.com/librespacefoundation/satnogs/satnogs-network/-/blob/master/.gitlab-ci.yml>`_:

   .. code-block:: bash
   
       pip install tox~=3.8.0

#. Run the tests:

   .. code-block:: bash
   
      tox -e "flake8,isort,yapf,pylint"


Coding Style
------------

Follow the `PEP8 <http://www.python.org/dev/peps/pep-0008/>`_ and `PEP257 <http://www.python.org/dev/peps/pep-0257/#multi-line-docstrings>`_ Style Guides.


What to work on
---------------
You can check `open issues <https://gitlab.com/librespacefoundation/satnogs/satnogs-network/issues>`_.
We regurarly open issues for tracking new features. You pick one and start coding.
