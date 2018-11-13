# pyIGTLink [![Build Status](https://travis-ci.org/Danielhiversen/pyIGTLink.svg?branch=master)](https://travis-ci.org/Danielhiversen/pyIGTLink) [![Coverage Status](https://coveralls.io/repos/Danielhiversen/pyIGTLink/badge.svg?branch=master&service=github)](https://coveralls.io/github/Danielhiversen/pyIGTLink?branch=master)
Python implementation of [OpenIGTLink](http://openigtlink.org/)

ALso support sending data from Matlab over IGTLink

Only ImageMessages, TransformMessages, and StringMessages are implementated at the moment.

Python 2.7 and Python 3 support.
Tested with [CustusX](http://custusx.org/) and [3D Slicer](https://www.slicer.org).

## Install

```
pip install pyIGTLink
```



## Example


python pyIGTLink.py    - Will send 2D image with random noise as local server 

python pyIGTLink.py  1 - Will send 2D image with moving circle as local server
