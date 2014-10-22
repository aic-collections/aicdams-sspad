from abc import ABCMeta, abstractmethod

from sspad.resources.rdf_lexicon import ns_collection


class Node(metaclass=ABCMeta):
	## RDF type.
	#
	#  This is a URI that reflects the node type set in the LAKE CND.
	#
	#  @sa https://github.com/aic-collections/aicdams-lake/tree/master-aic/fcrepo-webapp/src/aic/resources/cnd
	node_type = ns_collection['fedora'].resource


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
		return zip(self.prop_req_names, self.prop_lake_names)


	## Sets up connections to external services.
	def _setConnection(self):
		'''Set connectors.'''

		print('Setting up connections.')
		self.auth_str = cherrypy.request.headers['Authorization']\
			if 'Authorization' in cherrypy.request.headers\
			else None
		self.lconn = LakeConnector(self.auth_str)
		self.dgconn = DatagrinderConnector(self.auth_str)
		self.tsconn = TstoreConnector(self.auth_str)


	## Creates a node within a transaction in LAKE.
	#
	#  @FIXME This is currently broken due to a change in Fedora code that might or might not be
	#  a bug: https://www.pivotaltracker.com/story/show/79747630
	#
	#  @param uid		(string) UID of the node to be generated.
	#  @param tx_uri	(string) URI of the transaction.
	#
	#  @return tuple Two resource URIs: one in the transaction and one outside of it.
	def createNodeInTx(self, uid, tx_uri):
		node_tx_uri = self.lconn.createOrUpdateNode('{}/{}{}'.format(tx_uri,self.path,uid))
		node_uri = re.sub(r'/tx:[^\/]+/', '/', node_tx_uri)

		return (node_tx_uri, node_uri)


	## Guesses file extension from MIME types.
	#
	#  @param mimetype	(string) MIME type, such as 'image/jpeg'
	#
	#  @return string Extetnsion guessed (including leading period)
	def _guessFileExt(self, mimetype):
		ext = mimetypes.guess_extension(mimetype) or '.bin'
		cherrypy.log.error('Guessing MIME type for {}: {}'.format(mimetype, ext))
		return ext


	## Validate a datastream.
	#
	#  Override this method for each Node subclass.
	@abstractmethod
	def _validateDStream(self, ds, dsname='', rules={}):
		pass


	## Returns a RDF triple object from a value and a type.
	#
	#  The value must be in the #mixins list.
	#  Depending on the value of @p type, a literal object, a URI or a variable (?var) is created.
	#
	#  @param value		(string) Value to be processed.
	#  @oaram type		(string) One of 'literal', 'uri', 'variable'.
	#
	#  @return (rdflib.URIRef | rdflib.Literal | rdflib.Variable) rdflib object.
	def _rdfObject(self, value, type):
			#cherrypy.log('Value: ' + str(value))
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

