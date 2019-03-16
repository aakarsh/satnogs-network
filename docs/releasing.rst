Releasing
=========


Versioning scheme
-----------------

This repository follows `PEP-440 <https://www.python.org/dev/peps/pep-0440/>`_ versioning scheme.
All releases must use a `X.Y` segment version which signifies a final project release and is compatible with `Semantic Versioning <https://semver.org/>`_.
The versions must be numbered in a consistently increasing fashion.
Major `X` will never need to be increased unless the application is completely rewritten.
Minor `Y` shall be increased on each release.
A Patch or additional segments, as described in SemVer, shall not be used.


Release procedure
-----------------

To make a new release:

#. Find the next available minor version among the whole set of already present tags in the repository.

#. Create an annotated tag from `master` branch in GitLab with a commit message::

     Tag version 'X.Y'
