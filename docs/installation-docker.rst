Docker Installation
===================

#. **Requirements**

   You will need `docker <https://docs.docker.com/installation/#installation>`_ and `docker-compose <https://docs.docker.com/compose/install/>`_.


#. **Get the source code**

   Clone source code from the `repository <https://gitlab.com/librespacefoundation/satnogs/satnogs-network>`_::

     $ git clone https://gitlab.com/librespacefoundation/satnogs/satnogs-network.git
     $ cd satnogs-network

#. **Configure settings**

   Set your environmental variables::

     $ cp env-dist .env

#. **Install frontend dependencies**

   Install dependencies with ``npm``::

     $ npm install

   Test and copy the newly downlodaded static assets::

     $ ./node_modules/.bin/gulp

#. **Run it!**

   Run satnogs-network::

     $ docker-compose up -d --build

#. **Populate database**

   Create, setup and populate the database with demo data::

     $ docker-compose exec web djangoctl.sh initialize

   Your satnogs-network development instance is available in localhost:8000. Go hack!

#. **Clean database**

   Clean up the database in case of problems::

     $ docker-compose exec web django-admin flush

#. **Build the documentation locally**

     $ tox -e docs
