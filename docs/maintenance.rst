Maintenance
===========


Updating Python dependencies
----------------------------
To update the Python dependencies:

#. Execute script to refresh `requirements{-dev}.txt` files:

    $ ./contrib/refresh-requirements.sh

#. Stage and commit `requirements{-dev}.txt` files


Updating frontend dependencies
------------------------------
The frontend dependencies are managed with `npm` as defined in the `package.json`.
The following are required to perform an update of the dependencies:

#. Bump versions in `package.json`

#. Download and install the latest version of the dependencies

    $ npm install

#. Move the installed version into to satnogs-network source tree

    $ ./node_modules/.bin/gulp

#. Stage & commit the updated files in `network/static/`.
