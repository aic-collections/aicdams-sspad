import mimetypes
import re

import cherrypy

from urllib.parse import urlparse
from rdflib import URIRef, Literal, Variable

from sspad.connectors.datagrinder_connector import DatagrinderConnector
from sspad.connectors.lake_connector import LakeConnector
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.connectors.uidminter_connector import UidminterConnector
from sspad.modules.node import Node
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr

## Resource class.
#
#  Resources are all nodes in LAKE that can have metadata. They include two
#  main categories: holders and assets.
class Resource(Node):

	## Resource prefix.
	#
	#  This is used in the node UID and designates the resource type.
	#  It is mandatory to define it for each resource type.
	#  @TODO Call uidminter and generate a (cached) map of pfx to Resource subclass names.
	pfx = ''


	## RDF type.
	#
	#  This is a URI that reflects the node type set in the LAKE CND.
	#
	#  @sa https://github.com/aic-collections/aicdams-lake/tree/master-aic/fcrepo-webapp/src/aic/resources/cnd
	node_type = ns_collection['aic'].resource


	## Properties as specified in requests.
	#
	#  These map to #prop_lake_names.
	@property
	def prop_req_names(self):
		return super().prop_req_names + ('title',)


	## Tuples of LAKE namespaces and data types.
	#
	#  Data type string can be 'literal', 'uri' or 'variable'.
	@property
	def prop_lake_names(self):
		return super().prop_lake_names + ((ns_collection['dc'].title, 'literal'),)


	## Mix-ins considered for updating.
	@property
	def mixins(self):
		return (
			'aicmix:citi',
			'aicmix:citiPrivate',
		)


	## Base properties to assign to this node type.
	base_prop_tuples = [
		(ns_collection['rdf'].type, ns_collection['aic'].resource),
	]


	## Class constructor.
	#
	#  Sets up several connections and MIME types.
	def __init__(self):
		#self._setConnection()

		if not mimetypes.inited:
			mimetypes.init()
			for mt, ext, strict in self._add_mimetypes:
				mimetypes.add_type(mt, ext, strict)


