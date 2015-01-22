import mimetypes
import io
import json
import os

import cherrypy
import requests

from rdflib import URIRef, Literal, XSD

from sspad.config.datasources import lake_rest_api
from sspad.connectors.uidminter_connector import UidminterConnector
from sspad.models.instance import Instance
from sspad.models.resource import Resource
from sspad.resources.rdf_lexicon import ns_collection as nsc, ns_mgr


class Asset(Resource):
    '''Asset class.

    This is the base class for all Assets.
    '''

    @property
    def node_type(self):
        '''@sa SspadModel::node_type'''

        return nsc['laketype'].Asset



    @property
    def master_mimetype(self):
        '''MIME type used for master generation.

        @return string

        @TODO Use another method to map MIME types to various generated datastreams.
        '''

        return 'image/jpeg'



    @property
    def props(self):
        '''@sa SspadModel::props'''

        return super().props + (
            (nsc['aic'].batchUid, 'literal', XSD.string),
            (nsc['aic'].citiAgentPKey, 'uri'),
            (nsc['aic'].citiExhibPKey, 'uri'),
            (nsc['aic'].citiObjPKey, 'uri'),
            (nsc['aic'].citiPlacePKey, 'uri'),
            (nsc['aic'].citiPrefAgentPKey, 'uri'),
            (nsc['aic'].citiPrefExhibPKey, 'uri'),
            (nsc['aic'].citiPrefObjPKey, 'uri'),
            (nsc['aic'].citiPrefPlacePKey, 'uri'),
			(nsc['aic'].created, 'literal', XSD.dateTime),
			(nsc['aic'].createdBy, 'literal', XSD.string),
            (nsc['aic'].hasComment, 'uri'),
            (nsc['aic'].hasInstance, 'uri'),
            (nsc['aic'].hasMasterInstance, 'uri'),
            (nsc['aic'].hasOriginalInstance, 'uri'),
            (nsc['aic'].hasTag, 'uri'),
            (nsc['aic'].isPrimaryRepresentationOf, 'uri'),
            (nsc['aic'].legacyUid, 'literal', XSD.string),
			(nsc['aic'].lastModified, 'literal', XSD.dateTime),
			(nsc['aic'].lastModifiedBy, 'literal', XSD.string),
            (nsc['aic'].represents, 'uri'),
        )



    @property
    def special_rels(self):
        return {
            nsc['aic'].citiAgentPKey : {
                'type' : nsc['aic'].Object,
                'uid' : 'citi_pkey',
                'rel' : nsc['aic'].represents,
            },
            nsc['aic'].citiExhibPKey : {
                'type' : nsc['aic'].Object,
                'uid' : 'citi_pkey',
                'rel' : nsc['aic'].represents,
            },
            nsc['aic'].citiObjPKey : {
                'type' : nsc['aic'].Actor,
                'uid' : 'citi_pkey',
                'rel' : nsc['aic'].represents,
            },
            nsc['aic'].citiPlacePKey : {
                'type' : nsc['aic'].Actor,
                'uid' : 'citi_pkey',
                'rel' : nsc['aic'].represents,
            },
            nsc['aic'].citiPrefAgentPKey : {
                'type' : nsc['aic'].Place,
                'uid' : 'citi_pkey',
                'rel' : nsc['aic'].isPrimaryRepresentationOf,
            },
            nsc['aic'].citiPrefExhibPKey : {
                'type' : nsc['aic'].Place,
                'uid' : 'citi_pkey',
                'rel' : nsc['aic'].isPrimaryRepresentationOf,
            },
            nsc['aic'].citiPrefObjPKey  : {
                'type' : nsc['aic'].Event,
                'uid' : 'citi_pkey',
                'rel' : nsc['aic'].isPrimaryRepresentationOf,
            },
            nsc['aic'].citiPrefPlacePKey : {
                'type' : nsc['aic'].Event,
                'uid' : 'citi_pkey',
                'rel' : nsc['aic'].isPrimaryRepresentationOf,
            },
        }



    @property
    def mixins(self):
        return super().mixins + (
            'aicmix:Derivable',
            'aicmix:Overlayable',
            'aicmix:Publ_Web',
        )



    @property
    def path(self):
        '''Path between the repo root and the asset node.

        @return string
        '''

        pfx = self.pfx + '/' if self.pfx else ''
        return 'resources/assets/' + pfx



    def create(self, mid, props={}, **dstreams):
        '''Create an asset.

        @sa AssetCtrl::POST()

        @return (dict) Message with new asset node information.
        '''

        # If neither source nor ref_source is present, throw error
        if 'original' not in dstreams.keys() and 'ref_original' not in dstreams.keys():
            raise cherrypy.HTTPError('400 Bad Request', 'Required original datastream missing.')

        # Wrap string props in one-element lists
        for p in props:
            if not props[p].__class__.__name__ == 'list':
                props[p] = [props[p]]

        # Before anything else, check if any of the legacy UIDs given has a duplicate.
        # If that is the case, throw a 409 Conflict HTTP error.
        if 'legacy_uid' in props:
            for legacy_uid in props['legacy_uid']:
                check_uri = self.tsconn.get_node_uri_by_prop(
                    nsc['aic'] + 'legacyUid', legacy_uid
                )
                if check_uri:
                    cherrypy.response.headers['link'] = check_uri
                    raise cherrypy.HTTPError('409 Conflict', 'A node with legacy UID \'{}\' exists already.'.format(legacy_uid))

        # Create a new UID
        self.uid = self.mint_uid(mid)

        # Generate master if not existing
        dstreams = self._generate_master(dstreams)

        # First validate all datastreams
        dsmeta = self._validate_dstreams(dstreams)

        # Open Fedora transaction
        self.tx_uri = self.lconn.open_transaction()
        #cherrypy.log('Created TX: {}'.format(self.tx_uri))

        try:
            # Create Asset node in tx
            self.create_node_in_tx(self.uid)

            # Set node props
            init_tuples = self.base_prop_tuples + [
                (nsc['dc'].title, Literal(self.uid, datatype=XSD.string)),
                (nsc['aic'].uid, Literal(self.uid, datatype=XSD.string)),
            ]

            cherrypy.log('Asset create init tuples: {}'.format(init_tuples))
            cherrypy.log('Asset create properties: {}'.format(props))

            self.update_node(
                self.temp_uri,
                props = {
                    'insert_props' : props,
                    'init_insert_tuples' : init_tuples
                }
            )

            # Loop over all datastreams and ingest them
            self._ingest_instances(dstreams, dsmeta)

        except:
            # Roll back transaction if something goes wrong
            self._rollback_transaction()
            raise

        # Commit transaction
        self._commit_transaction()

        return {"message": "Asset created.", "data": {"location": self.uri}}



    def update(self, props={}, **dstreams):
        '''Updates an asset.

        @sa AssetCtrl::PUT()

        @return (dict) Message with updated asset node information.
        '''

        if props:
            # @TODO Replace all props
            self.replace_props(props)

        if dstreams:
            # Generate master if not existing and if original is provided
            dstreams = self._generate_master(dstreams)

            # First validate all datastreams
            dsmeta = self._validate_dstreams(dstreams)

            # Open Fedora transaction
            self.tx_uri = self.lconn.open_transaction()
            self.uri_in_tx = self.uri.replace(lake_rest_api['base_url'], self.tx_uri + '/')

            # Loop over all datastreams and ingest them
            self._ingest_instances(dstreams, dsmeta)

            # Commit transaction
            self._commit_transaction()

        # @TODO Actually verify the URI from response headers.
        return {"message": "Resource updated.", "data": {"location": self.uri}}



    def replace_props(self, props):
        '''Replace the whole property set of a node.

        @param props (list) List of prpoerty dicts.

        @return (boolean) Whether the operation was successful.

        @TODO Stub.
        '''

        pass



    def mint_uid(self, mid=None):
        '''Calls an external service to generate and returns a UID.

        @param mid (string, optional) Second prefix needed for certain types.

        @return (string) Generated UID.
        '''

        try:
            self.uid = UidminterConnector().mint_uid(self.pfx, mid)
        except:
            raise RuntimeError('Could not generate UID.')
        return self.uid



    def set_uri(self, uri=None, uid=None, legacy_uid=None):
        '''Validates the existence of a node from provided URI, UID or legacy UID
        and sets #uri to a value according to the first valid one found.
        At least one of uri, uid or legacy_uid values must be provided.

        @param uri (string, optional) URI of node, if known.
        @param uid (string, optional) AIC UID of Asset, if known.
        @param legacy_uid (string, optional) Legacy UID of Asset, if known.

        @return (bool) Whether the class-level member #uri was set.
        '''

        if not uri and not uid and not legacy_uid:
            raise ValueError('No valid identifier provided.')

        self.uri = None

        # First check the URI.
        if uri:
            if self.lconn.assert_node_exists(uri):
                self.uri = uri
                return True
            else:
                raise cherrypy.HTTPError('404 Not Found', 'No node with the provided URI: {}'.format(uri))

        # If no URI is provided, check UID and legacy UID, in that order.
        if uid:
            check_prop = nsc['aic'] + 'uid'
            check_uid = uid
            self.uid = uid
        else:
            check_prop = nsc['aic'] + 'legacyUid'
            check_uid = legacy_uid

        check_uri = self.tsconn.get_node_uri_by_prop(check_prop, check_uid)

        if check_uri:
            self.uri = check_uri
            return True
        else:
            return False



    def has_uid_dupes(self, uid=None, legacy_uid=None):
        '''Checks if a node with a given UID or a given legacy UID exists.
        At least one of uid or legacy_uid must be provided.

        @param uid (string, optional) UID of node to check duplicates for.
        @param legacy_uid (string, optional) Legacy UID of node to check duplicates for.

        @return (boolean) Whether a duplicate has been found.
        '''

        if not uid and not legacy_uid:
            raise ValueError('Neither uid or legacy_uid were provided. Cannot check for duplicates.')

        if uid:
            uri_uid = self.tsconn.find_node_uri_by_prop(nsc['aic'] + 'uid', uid)
            if not self.uri == uri_uid:
                return {'uid' : uri_uid}
        if legacy_uid:
            uri_legacy_uid = self.tsconn.get_node_uri_by_prop(nsc['aic'] + 'legacyUid', legacy_uid)
            if not self.uri == uri_legacy_uid:
                return {'legacy_uid' : uri_uid}

        return False



    def _generate_master(self, dstreams):
        '''Generates master datastream from original if missing and returns the complete list of datastreams.

        @param dstreams (dict) Dict of datastreams where keys are datastream names and values are datastreams.

        @return (dict) Updated list of datastreams.
        '''

        if 'master' not in dstreams.keys() and 'ref_master' not in dstreams.keys():
            # Generate master if not present
            cherrypy.log('Master file not provided.')
            if 'ref_original' in dstreams.keys():
                cherrypy.log('Requesting {}...'.format(dstreams['ref_original']))
                ds_binary = self.lconn.get_binary_stream(dstreams['ref_original'])

                dstreams['master'] = self._generateMasterFile(ds_binary.content, self.uid + '_master.jpg')
            elif 'original' in dstreams.keys():
                dstreams['master'] = self._generateMasterFile(
                    self._get_iostream_from_req(dstreams['original']),
                    self.uid + '_master.jpg'
                )
            else:
                cherrypy.log('No original or ref_original provided. Not changing the list.')

        else:
            cherrypy.log('Master file provided.')

        return dstreams



    def _validate_dstreams(self, dstreams):
        '''Ensures that provided datastreams are valid and conform to a set of conditions.
        This methiod is overridden for each asset type.

        @param dstreams (dict) Dict of datastreams. Keys are dataastream names and values are datastreams.

        @return (dict) Datastream metadata coming from validators.
        '''

        dsmeta = {}
        for dsname in dstreams.keys():
            ds = self._get_iostream_from_req(dstreams[dsname])

            cherrypy.log('Validation round (' + dsname + '): class name: ' + ds.__class__.__name__)

            if dsname[:4] == 'ref_':
                cherrypy.log('Skipping validation for reference ds.')
            else:
                try:
                    dsmeta[dsname] = self._validate_datastream(ds, dsname)
                    cherrypy.log('Validation for ' + dsname + ': ' + str(dsmeta[dsname]))
                except Exception as e:
                    raise cherrypy.HTTPError(
                        '415 Unsupported Media Type', 'Validation for datastream {} failed with exception: {}.'\
                        .format(dsname, e)
                    )

        return dsmeta



    def _get_iostream_from_req(self, ds):
        '''Normalize the behaviour of a datastream object regardless of its original.

        If ds is a byte stream instead of a Part instance, wrap it in an
        anonymous object as a 'file' property.

        @param ds The BytesIO or bytes object to be normalized.

        @return (BytesIO)
        '''

        if hasattr(ds, 'file'):
            cherrypy.log('Normalizer: ds.file exists already and is of class type {}.'.format(
                ds.file.__class__.__name__
            ))
            return ds.file
        elif ds.__class__.__name__ == 'bytes':
            cherrypy.log('Normalizer: got a bytestream.')
            return io.BytesIO(ds)
        elif ds.__class__.__name__ == 'BytesIO':
            cherrypy.log('Normalizer: got a BytesIO.')
            return ds



    def _ingest_instances(self, dstreams, dsmeta):
        '''Loops over datastreams and ingests them by
            calling #_create_or_update_instance() iteratively within a transaction.

        @param dstreams (dict) Dict of datastreams. Keys are datastream names and values are datastreams.
        @param dsmeta (dict) Dict of datastream metadata.
            Keys are datastream names and values are dicts of property names and values.

        @return (boolean) True
        '''

        cherrypy.log('DSmeta: {}'.format(dsmeta))
        for dsname in dstreams.keys():

            if dsname[:4] == 'ref_':
                # Create a reference node.
                in_dsname = dsname [4:]
                cherrypy.log('Creating a reference ds with name: aic:ds_{}'.format(in_dsname))
                inst_uri = Instance().create_or_update(
                    asset_uri = self.temp_uri,
                    name = in_dsname,
                    type = in_dsname.capitalize(),
                    ref = dstreams[dsname]
                )
            else:
                in_dsname = dsname
                #cherrypy.log('Ingestion round (' + in_dsname + '): class name: ' + dstreams[dsname].__class__.__name__)
                # Create an actual datastream.
                ds = self._get_iostream_from_req(dstreams[dsname])
                ds.seek(0)
                inst_uri = Instance().create_or_update(
                    asset_uri = self.temp_uri,
                    name = in_dsname,
                    type = in_dsname.capitalize(),
                    ds = ds,
                    mimetype = dsmeta[dsname]['mimetype']
                )



