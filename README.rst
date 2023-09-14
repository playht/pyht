.. image:: assets/logo_200w.png

|Python compat| |PyPi| |GHA tests| |Codecov report| |readthedocs|

.. inclusion-marker-do-not-remove

pyht
==============

pyht is a


Features
========

Installation
============

playht requires Python ``>=3.8`` and can be installed via:

.. code-block:: bash

   python -m pip install pyht


Usage
=====

.. code-block:: python

   from datetime import datetime
   from pathlib import Path

   import pyaudio

   from pyht import Client

   client = Client(
      user_id="<YOUR_USER_ID>",
      api_key="<YOUR_API_KEY>",
   )

   for chunk in client.tts("Hello World!", voice="<YOUR_VOICE_URI>"):
      # do something with the audio chunk


.. |GHA tests| image:: https://github.com/playht/pyht/workflows/tests/badge.svg
   :target: https://github.com/playht/pyht/actions?query=workflow%3Atests
   :alt: GHA Status
.. |Codecov report| image:: https://codecov.io/github/playht/pyht/graph/badge.svg?token=YQALN60PXB
   :target: https://codecov.io/github/playht/pyht
   :alt: Coverage
.. |readthedocs| image:: https://readthedocs.org/projects/pyht/badge/?version=latest
        :target: https://pyht.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status
.. |Python compat| image:: https://img.shields.io/badge/>=python-3.8-blue.svg
.. |PyPi| image:: https://img.shields.io/pypi/v/pyht.svg
        :target: https://pypi.python.org/pypi/pyht
