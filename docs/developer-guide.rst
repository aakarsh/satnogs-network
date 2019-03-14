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

To be able to manage the required javascript libraries, install the development dependencies with npm::

  $ npm install

Development tasks like the download of assets, code linting and tests are managed with gulp::

  $ gulp

Frontend dependencies are stored in packages.json, handled by yarn. To add a new dependency, e.g. satellite.js, call::

  $ yarn add satellite.js

Manually add the new required files to the list of "assets" in packages.json, then start the download with::

  $ gulp assets

The assets are stored in the repository, thus don't forget to create a commit after you add/update/remove dependencies.

Simulating station heartbeats
-----------------------------

Only stations which have been seen by the server in the last hour (by default, can be customized by `STATION_HEARTBEAT_TIME`) are taken into consideration when scheduling observations.
In order to simulate an heartbeat of the stations 7, 23 and 42, the following command can be used::

  $ sudo docker-compose run web python manage.py update_station_last_seen 7 23 42

Coding Style
------------

Follow the `PEP8 <http://www.python.org/dev/peps/pep-0008/>`_ and `PEP257 <http://www.python.org/dev/peps/pep-0257/#multi-line-docstrings>`_ Style Guides.

What to work on
---------------
You can check `open issues <https://gitlab.com/librespacefoundation/satnogs/satnogs-network/issues>`_.
We regurarly open issues for tracking new features. You pick one and start coding.
