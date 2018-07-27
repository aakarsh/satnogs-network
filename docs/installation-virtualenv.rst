VirtualEnv Installation
=======================

#. **Install the requirements**

   Generic requirements which you will need:: 

     python, python-virtualenvwrapper, pip and git, libmysqlclient-dev (mysql_config)

   Debian Stretch (9) specific requirements ::

     $ sudo apt-get install libmariadbclient-dev python-pip virtualenvwrapper 

#. **Build the environment**

   Clone source code from the `repository <https://gitlab.com/librespacefoundation/satnogs/satnogs-network>`_::

     $ git clone https://gitlab.com/librespacefoundation/satnogs/satnogs-network.git

   Set up the virtual environment. On first run you should create it and link it to your project path.::

     $ cd satnogs-network
     $ mkvirtualenv satnogs-network -a .

   Set your environmental variables::

     $ cp env-dist .env

   Activate your python virtual environment::

     $ workon satnogs-network

   Install local development requirements::

     $ (satnogs-network)$ pip install --require-hashes --no-deps -r requirements/dev.txt


#. **Database**

   Create, setup and populate the database with demo data::

     (satnogs-network)$ ./manage.py initialize

   Note that the above command requires internet connection, since it fetches
   Satellite and Transmitter data from `SatNOGS-DB <https://db.satnogs.org/>`_


#. **Run it!**

  Just run it::

    (satnogs-network)$ ./manage.py runserver

  Your satnogs-network development instance is available in localhost:8000. Go hack!
