from itertools import chain
import cherrypy, requests
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
	

	def createOrUpdateDStream(self, uri, dsname, ds=None, path=None, mimetype = 'application/octet-stream'):
		# @TODO Optimize with with
		if not ds and not path:
			raise cherrypy.HTTPError('500 Internal Server Error', "No datastream or file path given.")
	
		data = ds or open(path)
	
		res = requests.put(
			uri + '/fcr:content', 
			data = data,
			headers = dict(chain(self.headers.items(),
				[(
					'content-disposition',
					'inline; filename="' + dsname + '"'
				)]
			))
		)
		print('Requesting URL:', res.url)
		print('Create/update datastream response:', res.status_code)
		res.raise_for_status()

		if 'location' in res.headers:
			return res.headers['location']


	def updateNodeProperties(self, uri, delete_props={}, insert_props={}, where_props={}):
		''' Modifies node properties using a SPARQL-update query. '''

		g = Graph(namespace_manager = ns_mgr)
		insert_triples, delete_triples = ('','')
		where_triples_list = [];
		for d in delete_props:
			delete_triples += '\n\t<> {} {} .'.format(d[0].n3(), d[1].n3())
		for i in insert_props:
			insert_triples += '\n\t<> {} {} .'.format(i[0].n3(), i[1].n3())
		for w in where_props:
			where_triples_list.append('\n\t{{<> {} {}}}'.format(w[0].n3(), w[1].n3()))
		where_triples = '\n\tUNION'.join(where_triples_list)
		#print('Triples:', triples)

		# @TODO Use namespaces
		body = 'DELETE {{{}\n}} INSERT {{{}\n}} WHERE {{{}\n}}'\
			.format(delete_triples, insert_triples, where_triples)
		cherrypy.log.error('Executing SPARQL update: ' + body)
		
		res = requests.patch(
			uri, 
			data = body.encode('utf-8'),
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

