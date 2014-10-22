from itertools import chain
import cherrypy, requests
from os.path import basename
from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql.processor import prepareQuery

from sspad.config.datasources import lake_rest_api
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr

class LakeConnector:

	conf = lake_rest_api


	## Class constructor.
	#
	#  Sets authorization parameters based on incoming auth headers.
	#
	#  @param auth	(string) Authorization string as passed by incoming headers.
	def __init__(self, auth):
		self.headers = {'Authorization': auth}
		#cherrypy.log('Headers:', self.headers)


	## Open Fedora transaction.
	#
	#  @return string The transaction URI.
	def openTransaction(self):
		res = requests.post(
			self.conf['base_url'] + 'fcr:tx',
			headers = self.headers
		)
		#cherrypy.log('Requesting URL:', res.url)
		cherrypy.log('Open transaction response: {}'.format(res.status_code))
		res.raise_for_status()

		return res.headers['location']


	## Creates a container node if it does not exist, or updates it if it exists already.
	#
	#  @param uri	(string) URI of the node to be created or updated.
	#  @param props	(dict) Dictionary of properties to be associated with the node.
	def createOrUpdateNode(self, uri, props=None):
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
		cherrypy.log('Requesting URL:' + res.url)
		cherrypy.log('Create/update node response:' + str(res.status_code))
		res.raise_for_status()

		return res.headers['location']


	## Creates a datastream under an existing container node if it does not exist,\
	#  or updates it if it exists already.
	#
	#  @param uri		(string) URI of the datastream node to be created or updated.
	#  @param dsname	(string) Name of the datastream as a downloaded file.
	#  @param ds		(BytesIO) Datastream to be ingested. Alternative to \p path.
	#  @param path		(string) Path to the datastream. Alternative to \p ds.
	#  @param mimetype	(string) MIME type of the datastream. Default: application/octet-stream
	def createOrUpdateDStream(self, uri, dsname, ds=None, path=None, mimetype = 'application/octet-stream'):
		# @TODO Optimize with with
		if not ds and not path:
			raise cherrypy.HTTPError('500 Internal Server Error', "No datastream or file path given.")

		data = ds or open(path, 'rb')

		cherrypy.log('Ingesting datastream from class type: ' + data.__class__.__name__)
		res = requests.put(
			uri + '/fcr:content',
			data = data,
			headers = dict(chain(
				self.headers.items(),
				[('content-disposition', 'inline; filename="' + dsname + '"')]
			))
		)
		cherrypy.log('Requesting URL:' + res.url)
		cherrypy.log('Create/update datastream response:' + str(res.status_code))
		res.raise_for_status()

		if 'location' in res.headers:
			return res.headers['location']


	## Creates or updates a datastream with an externally referenced content.
	#
	#  @param uri		(string) URI of the datastream node to be created or updated.
	#  @param ref		(string) External source as a HTTP URL.
	def createOrUpdateRefDStream(self, uri, ref):
		cherrypy.log('Creating an externally referenced node: ' + uri)
		# Check that external reference exists
		check = requests.head(ref, headers=self.headers)
		check.raise_for_status()

		# Create ds with empty content
		res = requests.put(uri + '/fcr:content', headers=self.headers)
		res.raise_for_status()

		#cherrypy.log('Requesting URL:' + res.url)
		#cherrypy.log('Create/update datastream response:' + str(res.status_code))

		# Add external source
		self.updateNodeProperties(uri, insert_props=[
			(ns_collection['fedorarelsext'].hasExternalContent, URIRef(ref))
		])

		cherrypy.log('Response headers for reference DS:' + str(res.headers))
		if 'location' in res.headers:
			return res.headers['location']




	## Updates the properties of an existing node.
	#
	#  @param uri			(string) Node URI.
	#  @param delete_props	(dict) Properties to be deleted.\
	#  If the value of a property is a tuple or a list, thespecific value(s) will be deleted.\
	#  If it is an empty string (""), the whole property and its values are deleted.
	#  @param insert_props	(dict) Properties to be inserted.\
	#  Keys are property names, values are tuples or lists of values. Non-empty string can be used as single values.
	#  @param where_props	(dict) Conditions. Same syntax as \p insert_props.
	def updateNodeProperties(self, uri, delete_props=[], insert_props=[], where_props=[]):
		''' Modifies node properties using a SPARQL-update query. '''

		cherrypy.log.error("Delete props: " + str(delete_props) + "; Insert props: " + str(insert_props) + "; where props: " + str(where_props))
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
		cherrypy.log('Requesting URL:' + res.url)
		cherrypy.log('Update datastream properties response:' + str(res.status_code))
		res.raise_for_status()

		return True


	## Commits an open transaction.
	#
	# @param tx_uri The full transaction URI.
	def commitTransaction(self, tx_uri):
		cherrypy.log.error('Committing transaction: {}'.format(tx_uri.split('tx:')[-1]))
		res = requests.post(
			tx_uri + '/fcr:tx/fcr:commit',
			headers=self.headers
		)
		#cherrypy.log('Requesting URL:', res.url)
		cherrypy.log.error('Commit transaction response: {}'.format(res.status_code))
		res.raise_for_status()

		return True


	## Rolls back an open transaction.
	#
	# @param tx_uri The full transaction URI.
	def rollbackTransaction(self, tx_uri):
		cherrypy.log.error('Rolling back transaction: {}'.format(tx_uri.split('tx:')[-1]))
		res = requests.post(
			tx_uri + '/fcr:tx/fcr:rollback',
			headers=self.headers
		)
		#cherrypy.log('Requesting URL:', res.url)
		cherrypy.log.error('Rollback transaction response: {}'.format(res.status_code))
		res.raise_for_status()

		return True

