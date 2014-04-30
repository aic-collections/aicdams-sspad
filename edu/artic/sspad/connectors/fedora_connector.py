from itertools import chain
import mimetypes, requests
from os.path import basename
from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql.processor import prepareQuery

from edu.artic.sspad.config import host
from edu.artic.sspad.config.datasources import fedora_rest_api
from edu.artic.sspad.resources.rdf_lexicon import ns_mgr


class FedoraConnector:
	
	conf = fedora_rest_api
	base_url = '{}://{}{}'. format(conf['proto'], conf['host'], conf['root'])


	def __init__(self, auth):
		self.headers = {'Authorization': auth}
		#print('Headers:', self.headers)


	def openTransaction(self):
		res = requests.post(
			self.base_url + 'fcr:tx', 
			headers = self.headers
		)
		print('Requesting URL:', res.url)
		print('Open transaction response:', res.status_code)
		res.raise_for_status()

		return res.headers['location']


	def createOrUpdateNode(self, uri, props=None, ds=None, file=None):
		if props != None:
			g = Graph(namespace_manager = ns_mgr)
			for t in props:
				g.add((URIRef(''), t[0], t[1]))

			body = g.serialize(format='turtle')
		else:
			body = ''

		res = requests.put(
			uri, 
			data = body,
			headers = dict(chain(self.headers.items(),
				[('Content-type', 'text/turtle')]
			))
		)
		print('Requesting URL:', res.url)
		print('Create/update node response:', res.status_code)
		res.raise_for_status()

		return res.headers['location']
	

	def createOrUpdateDStream(self, uri, ds=None, file=None, mimetype = 'application/octet-stream'):
		# @TODO Optimize with with
		body = ds.read()\
			if ds != None\
			else\
			open(file)

		res = requests.post(
			uri + '/fcr:content', 
			data = body,
			headers = dict(chain(self.headers.items(),
				[(
					'content-disposition',
					'inline; filename="' + basename(uri) + mimetypes.guess_extension(mimetype) + '"'
				)]
			))
		)
		print('Requesting URL:', res.url)
		print('Create/update datastream response:', res.status_code)
		res.raise_for_status()

		return res.headers['location']
	

	def updateNodeProperties(self, uri, props):
		g = Graph(namespace_manager = ns_mgr)
		triples = ''
		for t in props:
			triples += '\n<> {} {} .'.format(t[0].n3(), t[1].n3())
		#print('Triples:', triples)

		# @TODO Use namespaces
		body = 'INSERT {' + triples + '\n} WHERE {}'
		#print('Body:', body)
		res = requests.patch(
			uri, 
			data = body,
			headers = dict(chain(self.headers.items(),
				[('Content-type', 'application/sparql-update')]
			))
		)
		print('Requesting URL:', res.url)
		print('Update datastream properties response:', res.status_code)
		res.raise_for_status()

		return True


	def commitTransaction(self, tx_uri):
		print('Committing transaction:', tx_uri)
		res = requests.post(
			tx_uri + '/fcr:tx/fcr:commit',
			headers=self.headers
		)
		print('Requesting URL:', res.url)
		print('Commit transaction response:', res.status_code)
		res.raise_for_status()
		
		return True


	def rollbackTransaction(self, tx_uri):
		print('Committing transaction:', tx_uri)
		res = requests.post(
			tx_uri + '/fcr:tx/fcr:rollback',
			headers=self.headers
		)
		print('Requesting URL:', res.url)
		print('Rollback transaction response:', res.status_code)
		res.raise_for_status()
		
		return True

