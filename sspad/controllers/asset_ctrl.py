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
            if model.tsconn.assert_node_exists_by_prop(
                ns_collection['aic'] + 'legacyUid', legacy_uid
            ):
                return {
                    'message': '*stub* This is Asset with legacy UID #{}.'\
                            .format(legacy_uid)
                }
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

        @param mid          (string) Mid-prefix.
        @param props    (dict) Properties to be associated with new node.
        @param **dstreams   (BytesIO) Arbitrary datastream(s).
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

        model = self.model()

        props_dict = model.convert_req_propnames(json.loads(props))

        try:
            ret = model.create(mid, props_dict, **dstreams)
        except:
            # @TODO Diffrentiate exceptions
            raise

        cherrypy.response.status = 201
        cherrypy.response.headers['Location'] = model.uri

        return ret



    def PUT(self, uid=None, uri=None, props='{}', **dstreams):
        '''PUT method.

        Adds or replaces datastreams or replaces the whole property set of an Asset.

        @param uid      (string) Asset UID. Specify this or 'uri' only if the node is known to exist,
           otherwise a 404 Not Found will be thrown.
        @param uri      (string) Asset URI. If this is not provided, node will be searched by UID.
        @param props    (dict) Properties to be associated with new or updated node.
           The optional 'legacy_uid' property is searched for conflicts or to find nodes when neither 'uri' or 'uid' are known.
        @param **dstreams   (BytesIO) Arbitrary datastream(s). Name of the parameter is the datastream name.
        Only the 'source' datastream is mandatory. @sa POST

        @return (dict) Message with node information.

        @TODO Replacing property set is not supported yet.
        '''

        cherrypy.log('\n')
        cherrypy.log('*********************')
        cherrypy.log('Begin update process.')
        cherrypy.log('*********************')
        cherrypy.log('')

        model = self.model()

        props_dict = model.convert_req_propnames(json.loads(props))

        legacy_uid = props_dict['legacy_uid'] if 'legacy_uid' in props_dict else None

        if not model.set_uri(uri, uid, legacy_uid):
            # If no URI could be set from given parameters, create new node.
            try:
                ret = model.create('', props_dict, **dstreams)
            except:
                # @TODO Diffrentiate exceptions
                raise

            cherrypy.response.status = 201
            cherrypy.response.headers['Location'] = model.uri

        else:

            # If a URI is found, update the node.
            try:
                ret = model.update(props=props_dict, **dstreams)
            except:
                raise

            cherrypy.response.status = 204
            cherrypy.response.headers['Location'] = model.uri

        return ret



    def PATCH(self, uid=None, uri=None, insert_props='{}', delete_props='{}'):
        '''PATCH method.

        @sa SspadModel::patch()
        '''

        cherrypy.log('\n')
        cherrypy.log('********************')
        cherrypy.log('Begin patch process.')
        cherrypy.log('********************')
        cherrypy.log('')

        model = self.model()
        model.set_uri(uri, uid)

        try:
            insert_props_dict = model.convert_req_propnames(json.loads(insert_props))
            delete_props_dict = model.convert_req_propnames(json.loads(delete_props))
        except:
            raise cherrypy.HTTPError(
                '400 Bad Request',
                'Properties are invalid. Please review your request.'
            )

        try:
            model.patch(insert_props_dict, delete_props_dict)
        except:
            # @TODO
            raise cherrypy.HTTPError('400 Bad Request')

        cherrypy.response.status = 204
        cherrypy.response.headers['Location'] = model.uri

        return {"message": "Asset updated."}

