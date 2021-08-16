from setuptools import setup, find_packages

setup(
   name='pyIGTLink',
   version='0.2.2',
   author='Daniel Hjelseth Høyer',
   url='https://github.com/Danielhiversen/pyIGTLink',
   description='python interface for OpenIGTLink',
   packages=find_packages(),
   install_requires=['crcmod', 'numpy', ]
)
