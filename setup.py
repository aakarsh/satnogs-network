from os import getenv

from setuptools import setup

import versioneer

setup_args = {
    'version': versioneer.get_version(),
    'cmdclass': versioneer.get_cmdclass(),
}

if getenv('READTHEDOCS') == 'True':
    setup_args['install_requires'] = ['setuptools']

setup(**setup_args)
