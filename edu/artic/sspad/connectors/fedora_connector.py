import bottle
from http.client import HTTPConnection, HTTPSConnection
from itertools import chain
from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql.processor import prepareQuery

from edu.artic.sspad.config import host
from edu.artic.sspad.config.datasources import fedora_rest_api
from edu.artic.sspad.resources.rdf_lexicon import ns_mgr


class FedoraConnector:
	
	def __init__(self):
		self.auth = bottle.request.headers.get('Authorization')
		self.headers = {'Authorization': self.auth}

	def openSession(self):
		session = \
			HTTPSConnection(fedora_rest_api['host'], fedora_rest_api['port']) \
			if fedora_rest_api['ssl'] \
			else \
			HTTPConnection(fedora_rest_api['host'], fedora_rest_api['port'])
		if host.app_env != 'prod':
			session.set_debuglevel(1)
		return session


	def openTransaction(self):
		session = self.openSession()
		session.request(\
			'POST', fedora_rest_api['root'] + 'fcr:tx', \
			headers = self.headers\
		)
		res = session.getresponse()
		print('Response:', res.msg)
		session.close()
		return res.msg['location']


	def createOrUpdateNode(self, uri, props=None, ds=None, file=None):
		session = self.openSession()
		if props != None:
			g = Graph(namespace_manager = ns_mgr)
			for t in props:
				g.add((URIRef(''), t[0], t[1]))

			body = g.serialize(format='turtle')
		elif ds != None:
			body = ds
		elif file != None:
			body = open(file)
		else:
			body = ''
		print('Body:', body)

		session.request(\
			'PUT', uri, \
			body = body,\
			headers = dict(chain(self.headers.items(),\
				[('Content-type', 'text/turtle')]\
			))\
		)
		res = session.getresponse()
		print('Response:', res.msg)
		session.close()

		return res.msg['location']
	

	def updateNodeProperties(self, uri, props):
		session = self.openSession()
		g = Graph(namespace_manager = ns_mgr)
		triples = ''
		for t in props:
			triples += '\n<> ' + t[0].n3() + ' ' + t[1].n3() + ' .'
		#print('Triples:', triples)

		# @TODO Use namespaces
		body = 'INSERT {' + triples + '\n} WHERE {}'
		print('Body:', body)
		session.request(\
			'PATCH', uri, \
			body = body,\
			headers = dict(chain(self.headers.items(),\
				[('Content-type', 'application/sparql-update')]\
			))\
		)
		res = session.getresponse()
		print('Response:', res.msg)
		session.close()

		return res.msg['location']


	def commitTransaction(self, tx_uri):
		print('Committing transaction:', tx_uri)
		session = self.openSession()
		session.request('POST', tx_uri + '/fcr:tx/fcr:commit',\
			headers=self.headers)
		res = session.getresponse()
		print('Response:', res.msg)
		session.close()


	def rollbackTransaction(self, tx_uri):
		session = self.openSession()
		print('Rolling back transaction:', tx_uri)
		session.request('POST', tx_uri + '/fcr:tx/fcr:rollback',\
			headers=self.headers)
		res = session.getresponse()
		print('Response:', res.msg)
		session.close()

