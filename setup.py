import os
from setuptools import setup, find_packages

version = '0.0.1'

if os.getenv("BRANCH_NAME") is not None:
    name="python-build-{}".format(os.getenv("BRANCH_NAME"))
else:
    from pygit2 import Repository
    branch = Repository('.').head.shorthand
    print("Branch taken from pygit2")
    name="python-build-{}".format(branch)

setup(name=name,
      url='https://github.com/diogozedan/python-build-dynamic.git',
      version=version,
      description='Custom build for python',
      maintainer='Diogo Zedan',
      maintainer_email='diogozedan@gmail.com',
      keywords='python-build-dynamic',
      package_dir={'': 'src'},
      packages=[''],
      package_data={' ': ['*.yaml']},
      install_requires=[
          'pandas',
          'numpy',
          'ruamel_yaml',
          'numexpr',
          'regex',
          'pygit2'
      ],
      include_package_data=True
)