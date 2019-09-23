Maintenance
===========


Updating Python dependencies
----------------------------

To update the Python dependencies:

#. Execute script to refresh ``requirements{-dev}.txt`` files::

     $ ./contrib/refresh-requirements.sh

#. Stage and commit ``requirements{-dev}.txt`` files.


Updating frontend dependencies
------------------------------

The frontend dependencies are managed with ``npm``.
To update the frontend dependencies, while respecting semver:

#. Update all the packages listed in ``package.json``::

     $ npm update

#. Test and copy the newly downlodaded static assets::

     $ ./node_modules/.bin/gulp

#. Stage and commit ``package-lock.json`` file.
