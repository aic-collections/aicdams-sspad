import cherrypy
import requests

from rdflib import URIRef, Literal

from sspad.config.datasources import lake_rest_api, datagrinder_rest_api
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.modules.node import Node
from sspad.modules.tagCat import TagCat
from sspad.resources.rdf_lexicon import ns_collection


class Tag(Node):


	exposed = True

	node_type = ns_collection['aiclist'].Tag


	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'category',
		)


	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['aic'].category, 'uri'),
		)



	## HTTP-EXPOSED METHODS ##

	def GET(self, cat_label=None, label=None):
		'''Get a tag or list of tags.'''

		self._set_connection()

		if label:
			cat_uri = TagCat().get_uri(cat_label)
			return self.get_uri(label, cat_label)
		else:
			return self.list(cat_label)


	def POST(self, cat, label):
		self._set_connection()

		return self.create(cat, label)



	## NON EXPOSED METHODS ##

	def list(self, cat_label=None):
		'''Lists all tags, optionally narrowing down the selection to a category.'''

		cat_cond = '''
		?cat <{}> ?cl .
		FILTER(STR(?cl="{}")) .
		'''.format(ns_collection['aic'].label, cat_label) \
				if cat_label \
				else ''

		q = '''
		SELECT ?uri ?label ?cat WHERE {{
			?uri a <{}> . 
			?uri <{}> ?label . 
			?uri <{}> ?cat .
			?cat a <{}> .
			{} }}
		'''.format(
			self.node_type,
			ns_collection['aic'].label, 
			ns_collection['fcrepo'].hasParent,
			ns_collection['aiclist'].TagCat, cat_cond
		)
		res = cherrypy.request.app.config['connectors']['tsconn'].query(q)
		cherrypy.log('Res: {}'.format(res))

		return res

	
	def get_uri(self, label, cat_uri):
		'''Gets tag URI by a given label.'''

		props = [
			(
				self._build_rdf_object(*self.props['label']),
				Literal(label, datatype=XSD.string),
			),
			(
				self._build_rdf_object(self.props['type']),
				URIRef(self.node_type),
			),
			(
				self._build_rdf_object(self.props['category']),
				URIRef(cat_uri),
			),
		]
		
		return cherrypy.request.app.config['connectors']['tsconn'].get_node_uri_by_props(props)


	def create(self, cat_label, label):
		'''Creates a new tag within a category and with a given label.'''

		cat_uri = TagCat().get_uri(cat_label)
		if not cat_uri:
			raise cherrypy.HTTPError(
				'404 Not Found',
				'Tag category with label \'{}\' does not exist. Cannot create tag.'\
						.format(cat_label)
			)
		if self.get_uri(label, cat_uri):
			raise cherrypy.HTTPError(
				'409 Conflict',
				'A tag with label \'{}\' exists in category \'{}\' already.'.\
						format(label, cat_label)
			)
		else:
			tag_uri = cherrypy.request.app.config['connectors']['lconn'].\
					create_or_update_node(
				parent = cat_uri,
				props = self._build_prop_tuples(
					insert_props = {
						'type' :  [self.node_type],
						'label' : [label],
						'category' : [cat_uri],

					},
					delete_props = {},
					init_insert_tuples = []
				)
			)

		return tag_uri


