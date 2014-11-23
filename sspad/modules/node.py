import cherrypy
import mimetypes
import re

from abc import ABCMeta, abstractmethod
from rdflib import URIRef, Literal, Variable
from urllib.parse import urlparse

from sspad.connectors.datagrinder_connector import DatagrinderConnector
from sspad.connectors.lake_connector import LakeConnector
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.resources.rdf_lexicon import ns_collection


class Node(metaclass=ABCMeta):
	## RDF type.
	#
	#  This is a URI that reflects the node type set in the LAKE CND.
	#
	#  @sa https://github.com/aic-collections/aicdams-lake/tree/master-aic/fcrepo-webapp/src/aic/resources/cnd
	node_type = ns_collection['fedora'].Resource


	## Additional MIME types.
	#
	#  They are added to the known list for guessing file extensions.
	_add_mimetypes = (
		('image/jpeg', '.jpeg', True),
		('image/psd', '.psd', False),
		('image/vnd.adobe.photoshop', '.psd', True),
		('image/x-psd', '.psd', False),
		# [...]
	)


	## Properties as specified in requests.
	#
	#  These map to #prop_lake_names.
	@property
	def prop_req_names(self):
		return ('type',)


	## Tuples of LAKE namespaces and data types.
	#
	#  Data type string can be 'literal', 'uri' or 'variable'.
	@property
	def prop_lake_names(self):
		return ((ns_collection['rdf'].type, 'uri'),)


	@property
	def props(self):
		return dict(zip(self.prop_req_names, self.prop_lake_names))


	## Sets up connections to external services.
	def _set_connection(self):
		'''Set connectors.'''

		cherrypy.log('Setting connectors...')
		cherrypy.request.app.config['connectors']['lconn'] = LakeConnector()
		cherrypy.request.app.config['connectors']['dgconn'] = DatagrinderConnector()
		cherrypy.request.app.config['connectors']['tsconn']  = TstoreConnector()

		self.lconn = cherrypy.request.app.config['connectors']['lconn']
		self.dgconn = cherrypy.request.app.config['connectors']['dgconn']
		self.tsconn = cherrypy.request.app.config['connectors']['tsconn']

 

	## Creates a node within a transaction in LAKE.
	#
	#  @FIXME This is currently broken due to a change in Fedora code that might or might not be
	#  a bug: https://www.pivotaltracker.com/story/show/79747630
	#
	#  @param uid		(string) UID of the node to be generated.
	#  @param tx_uri	(string) URI of the transaction.
	#
	#  @return tuple Two resource URIs: one in the transaction and one outside of it.
	def create_node_in_tx(self, uid, tx_uri):
		node_tx_uri = cherrypy.request.app.config['connectors']['lconn'].create_or_update_node(parent='{}/{}'.format(tx_uri,self.path))

		return (node_tx_uri, self.tx_uri_to_notx_uri(node_tx_uri))


	def tx_uri_to_notx_uri(self, tx_uri):
		'''Converts node URI inside transaction to URI outside of transaction.'''

		return re.sub(r'/tx:[^\/]+/', '/', tx_uri) # FIXME Ugly. Use more reliable methods.


	## Guesses file extension from MIME types.
	#
	#  @param mimetype	(string) MIME type, such as 'image/jpeg'
	#
	#  @return string Extetnsion guessed (including leading period)
	def _guess_file_ext(self, mimetype):
		ext = mimetypes.guess_extension(mimetype) or '.bin'
		cherrypy.log.error('Guessing MIME type for {}: {}'.format(mimetype, ext))
		return ext


	## Returns a RDF triple object from a value and a type.
	#
	#  The value must be in the #mixins list.
	#  Depending on the value of @p type, a literal object, a URI or a variable (?var) is created.
	#
	#  @param value		(string) Value to be processed.
	#  @oaram type		(string) One of 'literal', 'uri', 'variable'.
	def _build_prop_tuples(
			self, insert_props={}, delete_props={}, init_insert_tuples=[], ignore_broken_rels=True
			):
		''' Build delete, insert and where tuples suitable for #LakeConnector:update_node_properties.
		from a list of insert and delete properties.
		Also builds a list of nodes that need to be deleted and/or inserted to satisfy references.
		'''

		#cherrypy.log('Initial insert tuples: {}.'.format(init_insert_tuples))
		insert_tuples = init_insert_tuples
		delete_tuples, where_tuples = ([],[])
		insert_nodes, delete_nodes = ({},{})

		for req_name in self.props.keys():
			lake_name = self.props[req_name]

			# Delete tuples + nodes
			if req_name in delete_props:
				if isinstance(delete_props[req_name], list):
					# Delete one or more values from property
					for value in delete_props[req_name]:
						if req_name == 'tag':
							delete_nodes['tags'] = delete_props['tag']
							#value = lake_rest_api['tags_base_url'] + value
						elif req_name == 'comment':
							delete_nodes['comments'] = delete_props['comment']
						delete_tuples.append((lake_name[0], self._build_rdf_object(value, lake_name[1])))

				elif delete_props[req_name] == '':
					# Delete the whole property
					delete_tuples.append((lake_name[0], self._build_rdf_object('?' + req_name, 'variable')))
					where_tuples.append((lake_name[0], self._build_rdf_object('?' + req_name, 'variable')))

			# Insert tuples + nodes
			if req_name in insert_props:
				cherrypy.log('Adding req. name {} from insert_props {}...'.format(req_name, insert_props))
				cherrypy.log('Insert props: {}'.format(insert_props.__class__.__name__))
				for value in insert_props[req_name]:
					# Check if property is a relationship
					if req_name in self.reqprops_to_rels:
						rel_type = self.reqprops_to_rels[req_name]
						ref_uri = self.tsconn.get_node_uri_by_prop(ns_collection['aicdb'] + 'citi_pkey', value)
						if not ref_uri:
							if ignore_broken_rels:
								continue
							else:
								raise cherrypy.HTTPError(
									'404 Not Found',
									'Referenced CITI resource with CITI Pkey {} does not exist. Cannot create relationship.'.format(value)
								)
						value = ref_uri
					elif req_name == 'tag':
						insert_nodes['tags'] = insert_props['tag']
						#value = lake_rest_api['tags_base_url'] + value
						continue
					elif req_name == 'comment':
						insert_nodes['comments'] = insert_props['comment']
						continue
					cherrypy.log('Value for {}: {}'.format(req_name, value))
					insert_tuples.append((lake_name[0], self._build_rdf_object(value, lake_name[1])))

		return {
			'nodes' : (delete_nodes, insert_nodes),
			'tuples' : (delete_tuples, insert_tuples, where_tuples),
		}


	#
	#  @return (rdflib.URIRef | rdflib.Literal | rdflib.Variable) rdflib object.
	def _build_rdf_object(self, value, type):
			cherrypy.log('Converting value to RDF object: {}'.format(value))
			if type == 'literal':
					return Literal(value)
			elif type == 'uri':
				# @TODO Use rdflib tools instead of clunky string replacement if possible
				parsed_uri = urlparse(value)
				if parsed_uri.scheme and parsed_uri.netloc:
					return URIRef(value)
				elif ':' in value:
					ns, tname = value.split(':')
					if ns not in ns_collection or value not in self.mixins:
						cherrypy.HTTPError(
								'400 Bad Request', 'Relationship {} cannot be added or removed with this method.'.format(value))
					return URIRef(ns_collection[ns] + tname)
				else:
					raise ValueError('Value {} is not a valid fully-qualified or namespace-prefixed URI.'.format(value))
			elif type == 'variable':
					return Variable(value)


