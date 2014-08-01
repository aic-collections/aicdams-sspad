aicdams-sspad
=============

Shared Service Provider for the AIC DAMS

This application simplifies and standardized manipulation of resources in LAKE to conform the AIC's content model.

Dependencies:
- Python 3.x
- Cherrypy
- Psycopg2
- Rdflib
- Wand

You also need a connection to uidminter (@TODO create project).

Usage
-----
Copy sspad/config/host.py.template to sspad/config/host.py and adapt this file to your system needs.

Run server.py with Python to start the HTTP server.

Include auth string in request, which will be used to authenticate into LAKE.
