import json

import cherrypy

from sspad.controllers.sspad_controller import SspadController
from sspad.models.asset import Asset


class AssetCtrl(SspadController):
	'''Asset Controller class.

	This is the base class for all Assets.

	@package sspad.controllers
	'''


	@property
	def model(self):
		'''@see SspadController::model'''

		return Asset



	def GET(self, uid=None, legacy_uid=None):
		'''GET method.

		Lists all Assets or shows properties for an asset with given uid.

		@param uid (string) UID of Asset to display.

		@return string

		@TODO stub
		'''

		model = self.model()

		if uid:
			return {'message': '*stub* This is Asset #{}.'.format(uid)}
		elif legacy_uid:
			if model.connectors['tsconn'].assert_node_exists_by_prop(ns_collection['aic'] + 'legacyUid', legacy_uid):
				return {'message': '*stub* This is Asset with legacy UID #{}.'.format(legacy_uid)}
			else:
				raise cherrypy.HTTPError(
					'404 Not Found',
					'An asset with this legacy UID does not exist.'
				)
		else:
			return {'message': '*stub* This is a list of Assets.'}



	def POST(self, mid, props='{}', **dstreams):
		'''POST method.

		Create a new Asset node with automatic UID by providing data and node properties.

		@param mid			(string) Mid-prefix.
		@param props	(dict) Properties to be associated with new node.
		@param **dstreams	(BytesIO) Arbitrary datastream(s).
			Name of the parameter is the datastream name.
			If the datastream is to be ingested directly into LAKE, the variable value is the actual data.
			If the datastream is in an external URL and must be a reference,
			the variable name is prefixed with ref_ and the value is a URL (e.g. 'ref_source' will ingest a reference ds called 'source').
			Only the 'source' datastream is mandatory (or 'ref_source' if it is a reference).

		@return (dict) Message with new node information.
		'''

		cherrypy.log('\n')
		cherrypy.log('************************')
		cherrypy.log('Begin ingestion process.')
		cherrypy.log('************************')
		cherrypy.log('')

		props_dict = json.loads(props)

		return self.model().create(mid, props_dict, **dstreams)



	def PUT(self, uid=None, uri=None, props='{}', **dstreams):
		'''PUT method.

		Adds or replaces datastreams or replaces the whole property set of an Asset.

		@param uid		(string) Asset UID. Specify this or 'uri' only if the node is known to exist,
		   otherwise a 404 Not Found will be thrown.
		@param uri		(string) Asset URI. If this is not provided, node will be searched by UID.
		@param props	(dict) Properties to be associated with new or updated node.
		   The 'legacy_uid' property is searched for conflicts or to find nodes when neither 'uri' or 'uid' are known.
		@param **dstreams	(BytesIO) Arbitrary datastream(s). Name of the parameter is the datastream name.
		Only the 'source' datastream is mandatory. @sa POST

		@return (dict) Message with node information.

		@TODO Replacing property set is not supported yet, and might not be needed anyway.
		'''

		cherrypy.log('\n')
		cherrypy.log('*********************')
		cherrypy.log('Begin update process.')
		cherrypy.log('*********************')
		cherrypy.log('')

		props_dict = json.loads(props)

		legacy_uid = props_dict['legacy_uid'] if 'legacy_uid' in props_dict else None

		model = self.model()

		model.set_uri(uri, uid, legacy_uid)

		if not model.uri:
			return model.create('', props_dict, **dstreams)
			#raise cherrypy.HTTPError('404 Not Found', 'Node was not found for updating.')

		self._check_uid_dupes(uid, legacy_uid)
		return model.update(uid, None, props_dict, **dstreams)



	def PATCH(self, uid=None, uri=None, insert_props='{}', delete_props='{}'):
		'''PATCH method.

		@param uid (string) Asset UID.
		@param insert_props	(dict) Properties to be inserted.
		@param delete_props	(dict) Properties to be deleted.

		@return (dict) Message with new node information.
		'''

		cherrypy.log('\n')
		cherrypy.log('********************')
		cherrypy.log('Begin patch process.')
		cherrypy.log('********************')
		cherrypy.log('')

		model = self.model()

		try:
			model.patch(uid, uri, insert_props, delete_props)
		except:
			# @TODO
			raise cherrypy.HTTPError('400 Bad Request')

		cherrypy.response.status = 204
		# @TODO Actually verify the URI from response headers.
		cherrypy.response.headers['Location'] = model.uri

		return {"message": "Asset updated."}

