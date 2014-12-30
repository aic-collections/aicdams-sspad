import mimetypes
import io
import json
import os

import cherrypy
import requests

from rdflib import URIRef, Literal, XSD

from sspad.config.datasources import lake_rest_api
from sspad.connectors.uidminter_connector import UidminterConnector
from sspad.models.resource import Resource
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr


class Instance(Resource):
    '''Instance class.

    An instance is a representation of an Asset, corresponding to a single
    digital file. Each Instance has a file node under it, and a separate container node
    for metadata fields.

    @package sspad.models
    @author Stefano Cossu <scossu@artic.edu>
    @date 12/29/2014
    '''

    @property
    def node_type(self):
        return ns_collection['aic'].Instance



    @property
    def inst_path(self):
        '''Path of the instance node relative to the Asset.

        New instances will be created under
        <asset URI>/<value of this variable>/<asset ID>

        @return string
        '''

        return 'instances'



    @property
    def content_path(self):
        '''Path to content node relative to instance.

        @return string'''

        return 'aic:content'



    @property
    def metadata_path(self):
        '''Path to metadata node relative to instance.

        @return string'''

        return 'aic:meta'



    def create(
            self, asset_uri, name, type='Instance', ref=None, file_name=None,
            ds=None, path=None, mimetype='application/octet-stream'
            ):
        '''Creates an instance.

        @param asset_uri (string) URI of the container Asset node for the instance.
        @param name (string) Name of the datastream, e.g. 'master' or 'source'.
        @param type (string) The instance type. It corresponds to a RDF type.
                Valid values are 'Instance' (default), 'Master', or 'Original'.
        @param ref (string, optional) Reference URI for remote source.
        @param file_name (string, optional) File name for the downloaded datastream.
                If empty, this is built from the asset UID and instance name (default).
        @param ds (BytesIO, optional) Raw datastream.
        @param path (string, optional) Reference path for source file in current filesystem.
        @param mimetype (string, optional) MIME type of provided datastream.
                Default is 'application/octet-stream'.

        @return (string) New instance URI.

        @throws cherrypy.HTTPError 509 Conflict if the instance already exists.
        '''

        self.uri = '{}/{}/{}'.format(asset_uri, self.inst_path, name)

        if self.connectors['lconn'].assert_node_exists(self.uri):
            raise cherrypy.HTTPError('409 Conflict', 'Node with URI {} already exists.'\
                    .format(self.uri))

        self._create_or_update_content(
                name, ref, file_name, ds, path, mimetype
                )



    def create_or_update(
            self, asset_uri, name, type='Instance', ref=None, file_name=None,
            ds=None, path=None, mimetype='application/octet-stream'
            ):
        '''Updates an instance or creates it if not existing.

        @sa Instance::create()

        @return (string) Instance URI.
        '''

        self.uri = '{}/{}/{}'.format(asset_uri, self.inst_path, name)

        if not self.connectors['lconn'].assert_node_exists(self.uri):
            self._create_container(asset_uri, name, type)

        self._create_or_update_content(
                name, ref, file_name, ds, path, mimetype
                )



    # # # PRIVATE METHODS # # #

    def _create_container(self, asset_uri, name, type):
        '''Create the instance container.

        @param asset_uri (string) URI of the container Asset node for the instance.
        @param name (string) Name of the datastream, e.g. 'master' or 'source'.
        @param type (string) The instance type. It corresponds to a RDF type.
        '''

        rdf_type = ns_collection['aic'].Master\
                if name == 'master' \
                else \
                ns_collection['aic'].Instance

        asset_uid = os.path.basename(asset_uri)
        inst_uri = self.connectors['lconn'].create_or_update_node(
            uri = inst_uri,
            props = self._build_prop_tuples(
                insert_props = {
                    'type' :  [rdf_type],
                    'label' : [asset_uid + '_' + name],
                },
                init_insert_tuples = []
            )
        )
        #cherrypy.log('Created instance: {}'.format(inst_uri))

        if type == 'Original':
            rel_name = 'has_original'
        elif type == 'Master':
            rel_name = 'has_master'
        else:
            rel_name = 'has_instance'

        return Asset().update_node(
            uri = asset_uri,
            props = {
                'insert_props' : {rel_name : [self.uri]},
                'init_insert_tuples' : [],
            }
        )




    def _create_or_update_content(
            self, name, ref, file_name, ds, path, mimetype
            ):
        '''Create or replace content datastream.

        @param name (string) Name of the datastream, e.g. 'master' or 'source'.
        @param ref (string, optional) Reference URI for remote source.
        @param file_name (string, optional) File name for the downloaded datastream.
                If empty, this is built from the asset UID and instance name (default).
        @param ds (BytesIO, optional) Raw datastream.
        @param path (string, optional) Reference path for source file in current filesystem.
        @param mimetype (string, optional) MIME type of provided datastream.
                Default is 'application/octet-stream'.

        @return (string) instance content URI.
        '''

        if not file_name:
            file_name = '{}_{}{}'.format(
                os.path.basename(inst_uri), name, self._guess_file_ext(mimetype)
            )

        if ref:
            inst_content_uri = self.connectors['lconn'].create_or_update_ref_datastream(
                uri = inst_uri + '/aic:content', ref = ref
            )
        else:
            inst_content_uri = self.connectors['lconn'].create_or_update_datastream(
                uri = inst_uri + '/aic:content',
                file_name=file_name, ds=ds, path=path, mimetype=mimetype
            )

        # Add relationship in parent node.

        return inst_content_uri

