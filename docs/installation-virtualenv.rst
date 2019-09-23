VirtualEnv Installation
=======================

#. **Requirements**

   You will need python, python-virtualenvwrapper, pip and git

#. **Get the source code**

   Clone source code from the `repository <https://gitlab.com/librespacefoundation/satnogs/satnogs-network>`_::

     $ git clone https://gitlab.com/librespacefoundation/satnogs/satnogs-network.git
     $ cd satnogs-network

#. **Build the environment**

   Set up the virtual environment. On first run you should create it and link it to your project path.::

     $ mkvirtualenv satnogs-network -a .

#. **Configure settings**

   Set your environmental variables::

     $ cp env-dist .env

#. **Install frontend dependencies**

   Install dependencies with ``npm``::

     $ npm install

   Test and copy the newly downlodaded static assets::

     $ ./node_modules/.bin/gulp

#. **Run it!**

   Activate your python virtual environment::

     $ workon satnogs-network

   Just run it::

    (satnogs-network)$ ./bin/djangoctl.sh develop .

#. **Populate database**

   Create, setup and populate the database with demo data::

     (satnogs-network)$ ./bin/djangoctl.sh initialize

   Your satnogs-network development instance is available in localhost:8000. Go hack!
