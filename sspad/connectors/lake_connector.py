from itertools import chain

from os.path import basename

import cherrypy
import requests

from rdflib import Graph, URIRef, Literal
from rdflib.plugins.sparql.processor import prepareQuery

from sspad.config.datasources import lake_rest_api
from sspad.resources.rdf_lexicon import ns_collection, ns_mgr

class LakeConnector:
    '''@package sspad.connectors

    Handles communication with the LAKE (Fedora) REST API.
    '''


    @property
    def conf(self):
        '''LAKE host configuration.

        @return dict
        '''

        return lake_rest_api



    def __init__(self):
        '''Class constructor.

        Set authorization parameters based on incoming auth headers.

        @return None
        '''

        auth_str = cherrypy.request.headers['Authorization']\
            if 'Authorization' in cherrypy.request.headers\
            else None
        self.headers = {'Authorization': auth_str}



    def assert_node_exists(self, uri):
        '''Check if a node exists already.

        @param uri (string) URI to check.

        @return (boolean) Whether node exists.

        @throw HTTPError If the request is invalid (i.e. any other HTTP error than 404)
        '''

        res = requests.head(uri, headers = self.headers)
        cherrypy.log('Check if node exists: {}'.format(res.status_code))
        if res.status_code == 404:
            return False
        elif res.status_code < 399:
            return True
        else:
            res.raise_for_status()



    def open_transaction(self):
        '''Open Fedora transaction.

        @return (string) The transaction URI.
        '''

        res = requests.post(
            self.conf['base_url'] + 'fcr:tx',
            headers = self.headers
        )
        #cherrypy.log('Requesting URL: {}'.format(res.url))
        cherrypy.log('Open transaction response: {}'.format(res.status_code))
        res.raise_for_status()

        return res.headers['location']



    def get_binary_stream(self, uri):
        '''Get a binary stream.'''

        res = requests.get(uri, headers=self.headers)
        res.raise_for_status()

        return res



    def create_or_update_node(self, uri=None, parent='/', props=None):
        '''Create a container node if it does not exist,
            or update it if it exists already.

        @param uri (string, optional) URI of the node to be created or updated.
        @param parent (string, optional) Parent path relative to
            repository root. Default is '/'.
        @param props (dict, optional) Dictionary of properties to be
            associated with the node.

        @return (string) New node URI.
        '''
        if props:
            g = Graph(namespace_manager = ns_mgr)
            cherrypy.log('Received prop tuples: {}'.format(props))
            for t in props['tuples'][1]:
                g.add((URIRef(''), t[0], t[1]))

            body = g.serialize(format='turtle')
        else:
            body = ''

        if uri:
            #cherrypy.log('Creating node by PUT with RDF properties: {}'.format(body))
            res = requests.put(
                uri,
                data = body,
                headers = dict(chain(self.headers.items(),
                    [('Content-type', 'text/turtle')]
                ))
            )
        else:
            cherrypy.log('Creating node by POST with RDF properties: {}'.format(body))
            res = requests.post(
                parent,
                data = body,
                headers = dict(chain(self.headers.items(),
                    [('Content-type', 'text/turtle')]
                ))
            )
        cherrypy.log('Requesting URL: {}'.format(res.url))
        cherrypy.log('Create/update node response:' + str(res.status_code))
        if res.status_code > 399:
            cherrypy.log('HTTP Error: {}'.format(res.text))
        res.raise_for_status()

        return res.headers['location']



    def create_or_update_datastream(
            self, uri, file_name, ds=None, path=None,
            mimetype='application/octet-stream'):
        '''Create a datastream under an existing container
            node if it does not exist, or update it if it exists already.

        @param uri (string) URI of the datastream node to be created or updated.
        @param file_name (string) Name of the datastream as a downloaded file.
        @param ds (BytesIO, optional) Datastream to be ingested.
            Alternative to \p path.
        @param path (string, optional) Path to the datastream.
            Alternative to \p ds.
        @param mimetype (string, optional) MIME type of the datastream.
            Default: application/octet-stream

        @return (string | None) New node URI if a new node is created.
        '''

        # @TODO Optimize with with
        if not ds and not path:
            raise cherrypy.HTTPError(
                '500 Internal Server Error', "No datastream or file path given."
            )

        data = ds or open(path, 'rb')
        #cherrypy.log('Data peek: {}'.format(data))

        cherrypy.log('Ingesting datastream from class type: {}'\
                .format(data.__class__.__name__))
        res = requests.put(
            uri,
            data = data.read(),
            headers = dict(chain(
                self.headers.items(),
                [
                    ('content-disposition', 'inline; filename="' + file_name + '"'),
                    ('content-type', mimetype),
                ]
            ))
        )
        cherrypy.log('Requesting URL: {}'.format(res.url))
        #cherrypy.log('Request headers: {}'.format(res.request.headers))
        #cherrypy.log('Response headers: {}'.format(res.headers))
        cherrypy.log('Create/update datastream response:' + str(res.status_code))
        res.raise_for_status()

        if 'location' in res.headers:
            return res.headers['location']



    def create_or_update_ref_datastream(self, uri, ref):
        '''Create or update a datastream with an externally referenced content.

        @param uri (string) URI of the datastream node to be created or updated.
        @param ref (string) External source as a HTTP URL.

        @eturn (string) New datasteram URI if a new one is crated.
        '''

        cherrypy.log('Creating an externally referenced node: ' + uri)
        # Check that external reference exists
        check = requests.head(ref, headers=self.headers)
        check.raise_for_status()

        res = requests.put(
            uri,
            headers = dict(chain(
                self.headers.items(),
                [('content-type', 'message/external-body; access-type=URL; URL="{}"'.format(ref))]
            ))
        )
        res.raise_for_status()

        #cherrypy.log('Requesting URL: {}'.format(res.url))
        #cherrypy.log('Create/update datastream response:' + str(res.status_code))

        cherrypy.log('Response headers for reference DS:' + str(res.headers))
        if 'location' in res.headers:
            return res.headers['location']



    def update_node_properties(self, uri, delete_props=[], insert_props=[], where_props=[]):
        '''Update the properties of an existing node from a set of insert, delete
            and where tuples formatted by Node::_build_prop_tuples .

        @param uri (string) Node URI.
        @param delete_props (dict) Properties to be deleted.
        If the value of a property is a tuple or a list, thespecific value(s) will be deleted.
        If it is an empty string (""), the whole property and its values are deleted.
        @param insert_props (dict) Properties to be inserted.
        Keys are property names, values are tuples or lists of values.
        Non-empty string can be used as single values.
        @param where_props  (dict) Conditions. Same syntax as @p insert_props.

        @return (boolean) True on success.
        '''


        if not delete_props and not insert_props:
            cherrypy.log('Not received any properties to update.')
            return False

        cherrypy.log("URI: {}\nDelete props: {}\nInsert props: {}\nwhere props: {}".format(
            uri, delete_props, insert_props, where_props
        ))
        insert_triples, delete_triples = ('','')
        where_triples_list = [];

        for d in delete_props:
            delete_triples += '\n\t<> {} {} .'.format(d[0].n3(), d[1].n3())

        for i in insert_props:
            insert_triples += '\n\t<> {} {} .'.format(i[0].n3(), i[1].n3())

        for w in where_props:
            where_triples_list.append('\n\t{{<> {} {}}}'.format(w[0].n3(), w[1].n3()))
        where_triples = '\n\tUNION'.join(where_triples_list)

        body = 'DELETE {{{}\n}} INSERT {{{}\n}} WHERE {{{}\n}}'\
            .format(delete_triples, insert_triples, where_triples)
        cherrypy.log.error('Executing SPARQL update: ' + body)

        cherrypy.log('URI: {}'.format(uri))
        res = requests.patch(
            uri,
            data = body.encode('utf-8'),
            headers = dict(chain(self.headers.items(),
                [('Content-type', 'application/sparql-update')]
            ))
        )
        cherrypy.log('Requesting URL: {}'.format(res.url))
        cherrypy.log('Update datastream properties response:' + str(res.status_code))
        if res.status_code > 399:
            cherrypy.log('HTTP Error: {}'.format(res.text))
        res.raise_for_status()

        return True



    def commit_transaction(self, tx_uri):
        '''Commit an open transaction.

        @param tx_uri The full transaction URI.

        @return (boolean) True on success.
        '''

        cherrypy.log.error('Committing transaction: {}'.format(tx_uri.split('tx:')[-1]))
        res = requests.post(
            tx_uri + '/fcr:tx/fcr:commit',
            headers=self.headers
        )
        cherrypy.log.error('Commit transaction response: {}'.format(res.status_code))
        res.raise_for_status()

        return True



    def rollback_transaction(self, tx_uri):
        '''Roll back an open transaction.

        @param tx_uri The full transaction URI.

        @return (boolean) True on success.
        '''

        cherrypy.log.error('Rolling back transaction: {}'.format(tx_uri.split('tx:')[-1]))
        res = requests.post(
            tx_uri + '/fcr:tx/fcr:rollback',
            headers=self.headers
        )
        #cherrypy.log('Requesting URL: {}'.format(res.url))
        cherrypy.log.error('Rollback transaction response: {}'.format(res.status_code))
        res.raise_for_status()

        return True

