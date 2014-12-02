import mimetypes

import cherrypy

from sspad.models.node import Node
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr

class Resource(Node):
	'''Resource class.

	Resources are all nodes in LAKE that can have metadata. They include two
	main categories: holders and assets.
	'''

	@property
	def pfx(self):
		'''Resource prefix.

		This is used in the node UID and designates the resource type.
		It is mandatory to define it for each resource type.

		@return string

		@TODO Call uidminter and generate a (cached) map of pfx to Resource subclass names.
		'''

		return ''



	@property
	def node_type(self):
		return ns_collection['aic'].Resource



	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'title',
		)



	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['dc'].title, 'literal', 'string'),
		)



	@property
	def mixins(self):
		'''Mix-ins considered for updating.

		@return tuple
		'''
		return (
			'aicmix:Citi',
			'aicmix:CitiPrivate',
		)



	@property
	def base_prop_tuples(self):
		'''Base properties to assign to this node type.

		@return list
		'''

		return [
			(ns_collection['rdf'].type, self.node_type),
		]



	def __init__(self):
		'''Class constructor.

		Sets up several connections and MIME types.

		@return None
		'''
		super().__init__()
		if not mimetypes.inited:
			mimetypes.init()
			for mt, ext, strict in self._add_mimetypes:
				mimetypes.add_type(mt, ext, strict)



	def _validate_datastream(self, ds, dsname='', rules={}):
		'''Validate a datastream.

		Override this method for each Node subclass.
		'''

		pass


