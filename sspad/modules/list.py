from sspad.config.transforms import list_transforms

class List(Node):
	'''Authority list.'''

	exposed = True


	@property
	def _all_lists(self):
		'''Returns a list of all top-level lists.'''

		q = '''
		PREFIX olo:<http://purl.org/ontology/olo/core#>

		SELECT ?i ?l WHERE {
			?i a olo:OrderedList .
			MINUS { ?i a olo:Slot . }
		}'''

		return self.tsconn.query(q)


	def OPTIONS(self):
		'''Returns a list of all list URIs.'''
		
		return self.tsconn.get_all_lists()


	def GET(self, name):
		'''Return the hierarchy of a named list.'''

		list_uri = self.base_url + name
		if list_uri in self._all_lists:
			q = '''
			SELECT ?i ?l WHERE {
				olo:slot ?s .
				?s olo:item ?i .
				?i rdfs:label ?l
			}
			'''
			return self.tsconn.query(q)
		else:
			raise cherrypy.HTTPError(
				'404 Not Found',
				'Name "{}" was not found in transform map.'.format(name)
			)
