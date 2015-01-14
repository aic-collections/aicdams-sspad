import cherrypy
import mimetypes
import re
import uuid

from abc import ABCMeta, abstractmethod
from rdflib import URIRef, Literal, Variable, XSD
from urllib.parse import urlparse

from sspad.config.datasources import lake_rest_api
from sspad.connectors.datagrinder_connector import DatagrinderConnector
from sspad.connectors.lake_connector import LakeConnector
from sspad.connectors.tstore_connector import TstoreConnector
from sspad.resources.rdf_lexicon import ns_collection as nsc


class SspadModel(metaclass=ABCMeta):
    '''SspadModel class.

    This is the base class for all Fedora nodes.
    This class is initialized by instantiation from a controller. Therefore, its constructor
    method can refer to cherrypy request parameters.

    @package sspad.models
    '''

    @property
    def node_type(self):
        '''RDF type.

        This is a URI that reflects the node type set in the LAKE CND.

        @sa https://github.com/aic-collections/aicdams-lake/tree/master-aic/fcrepo-webapp/src/aic/resources/cnd

        @return rdflib.URIRef
        '''

        return nsc['fedora'].Resource



    @property
    def _add_mimetypes(self):
        '''Additional MIME types.

        They are added to the known list for guessing file extensions.

        @return tuple
        '''

        return (
            ('image/jpeg', '.jpeg', True),
            ('image/psd', '.psd', False),
            ('image/vnd.adobe.photoshop', '.psd', True),
            ('image/x-psd', '.psd', False),
        )



    @property
    def special_rels(self):
        '''Properties to resource prefix mapping.

        This list allows to create relationships with nodes in special locations such as federated
        database records, by entering an external identifier which is not thenode URI.
        The node is searched by that identifier and, if it exists, its URI is used to build
        the relationships.

        Dict keys correspond to keys in SspadModel::props.
        Values are dicts containing the following keys:
            - 'type' is a rdf:type that uniquely identifies the group of nodes searched.
            - 'uid' is the property name of the external identifier that should be unique
                within the 'type' parameter above.
            - 'rel' is the name of the actual relationship that is created.

        @return dict
        '''

        return {}




    @property
    def props(self):
        '''Tuples defining properties stored in LAKE for this model.

        First tuple element is the property URI.
        Second element is a string defining property type, which can be
            'literal', 'uri' or 'variable'.
        Third element is optional and only available for 'literal' data type
            and defines the XMLSchema data type.

        @return tuple

        @TODO Add lang option.
        '''

        return (
            (nsc['rdf'].type, 'uri'),
            (nsc['aic'].label, 'literal', XSD.string),
        )



    @property
    def base_prop_tuples(self):
        '''Base properties to assign to this node type.

        @return list
        '''

        return [
            (nsc['rdf'].type, self.node_type),
        ]



    #@property
    #def tx_uri(self):
    #    '''Returns the current transaction URI.

    #    If no transaction is open, it opens a new one.


    #    @return string
    #    '''

    #    if not self._tx_uri:
    #        self._open_transaction()

    #    return self._tx_uri



    @property
    def temp_uri(self):
        '''Returns the current model's URI in the current transaction if a transaction
            is open; otherwise it returns the permanent model URI.

        @return string
        '''

        return self.uri_in_tx if self.uri_in_tx else self.uri



    ## GENERAL METHODS ##

    def __init__(self):
        '''Sets up connections to external services.

        Connector objects are available via the #connectors dict.
        If this method needs to be redefined in subclasses, make sure that this superclass __init__
        is called first, to make sure that connections to external services are appropriately established.

        @return None
        '''

        cherrypy.log('Setting connectors...')
        self.lconn = LakeConnector()
        self.dgconn = DatagrinderConnector()
        self.tsconn = TstoreConnector()



    ## CRUD METHODS ##

    def create_node_in_tx(self, uid):
        '''Creates a node within a transaction in LAKE.

        @param uid      (string) UID of the node to be generated.

        @return None
        '''

        if not self.tx_uri:
            self._open_connection()

        self.uri_in_tx = self.lconn.create_or_update_node(
            parent='{}/{}'.format(self.tx_uri,self.path)
        )

        self.uri = self._tx_uri_to_notx_uri(self.uri_in_tx)



    def update_node(self, uri, props):
        '''Updates a node inserting and deleting related nodes if necessary.

        @param uri (string) URI of the node to be updated.
        @param props (dict) Map of properties and nodes to be updated, to be passed to #_build_prop_tuples.

        @return None
        '''

        tuples = self._build_prop_tuples(**props)

        delete_nodes, insert_nodes = tuples['nodes']
        delete_tuples, insert_tuples, where_tuples = tuples['tuples']

        for node_type in delete_nodes.keys():
            for del_uri in delete_nodes[node_type]:
                self.lconn.delete_node(del_uri)

        for node_type in insert_nodes.keys():
            insert_tuples += self._insert_nodes_in_tuples(node_type, insert_nodes[node_type])

        self.lconn.update_node_properties(
            uri,
            delete_props=delete_tuples,
            insert_props=insert_tuples,
            where_props=where_tuples
        )



    def patch(self, insert_props={}, delete_props={}):
        '''Adds or removes properties and mixins in a node.

        @param uid (string) Node UID.
        @param insert_props (dict) Properties to be inserted.
        @param delete_props (dict) Properties to be deleted.

        @return (dict) Message with new node information.
        '''

        #cherrypy.log('Insert props:' + str(insert_props))
        #cherrypy.log('Delete props:' + str(delete_props))

        # Open Fedora transaction
        self.tx_uri = self.lconn.open_transaction()
        self.uri_in_tx = self.uri.replace(lake_rest_api['base_url'], self.tx_uri + '/')

        # Collect properties
        try:
            self.update_node(
                self.temp_uri,
                props = {
                    'insert_props' : insert_props,
                    'delete_props' : delete_props,
                    'init_insert_tuples' : [],
                }
            )
        except:
            self._rollback_tansaction()
            raise

        self._commit_transaction()

        return True



    def convert_req_propnames(self, props):
        '''Converts all property names passed in request as
        namespaced string to fully-qualified URIRefs.'''

        ret = {}
        for p in props.keys():
            fqp = self._build_fquri_from_prefixed(p)
            ret[fqp] = props[p]

        return ret



    ## PRIVATE METHODS ##

    def _tx_uri_to_notx_uri(self, tx_uri):
        '''Converts node URI inside transaction to URI outside of transaction.'''

        return re.sub(r'/tx:[^\/]+/', '/', tx_uri) # FIXME Ugly. Use more reliable methods.



    def _guess_file_ext(self, mimetype):
        '''Guesses file extension from MIME types.

        @param mimetype (string) MIME type, such as 'image/jpeg'

        @return (string) Extetnsion guessed (including leading period)
        '''

        ext = mimetypes.guess_extension(mimetype) or '.bin'
        cherrypy.log.error('Guessing MIME type for {}: {}'.format(mimetype, ext))
        return ext



    def _build_prop_tuples(
            self, insert_props={}, delete_props={},
            init_insert_tuples=[], ignore_broken_rels=True):
        '''Build delete, insert and where tuples suitable for
            #LakeConnector:update_node_properties from a list of insert and delete properties.
            Also builds a list of nodes that need to be deleted and/or inserted to satisfy references.

            @param insert_props (dict, optional) Properties to be inserted.
            @param delete_props (dict, optional) Properties to be deleted.
            @param init_insert_tuples (list, optional) Initial properties coming from default settings,
                already formatted as tuples.
            @param ignore_broken_rels (boolean, optional) If set to True (default), the application throws
                an exception if a realtionship with a CITI object is broken.
                If False, the property is skipped and the process goes forward.
                WARNING: DO NOT SET TO TRUE IN PRODUCTION ENVIRONMENT!

            @return (dict) Dict containing two elements:
                'nodes' is a tuple containing a list of nodes to be deleted and a list of nodes to be created.
                'tuples' is a tuple containing a list of tuples to be added, one of tuples to be removed,
                and one of WHERE conditions.
        '''

        cherrypy.log('Insert props received: {}.'.format(insert_props))
        #cherrypy.log('Self props: {}.'.format(self.props))
        insert_tuples = init_insert_tuples
        delete_tuples, where_tuples = ([],[])
        insert_nodes, delete_nodes = ({},{})

        for prop in self.props:
            prop_name = prop[0]
            #cherrypy.log('Scanning property {}...'.format(prop_name))

            # Delete tuples + nodes
            if prop_name in delete_props:
                if isinstance(delete_props[prop_name], list):
                    # Delete one or more values from property
                    for value in delete_props[prop_name]:
                        if prop_name == nsc['aic'].hasComment:
                            delete_nodes['comments'] = value
                        delete_tuples.append((prop, self._build_rdf_object(value, prop[1])))

                elif delete_props[prop_name] == '':
                    # Delete the whole property
                    delete_tuples.append((prop_name, Variable(prop_name)))
                    where_tuples.append((prop_name, Variable(prop_name)))

            # Insert tuples + nodes
            if prop_name in insert_props:
                cherrypy.log('Adding req. name {} from insert_props {}...'.format(prop_name, insert_props))
                #cherrypy.log('Insert props: {}'.format(insert_props.__class__.__name__))
                for value in insert_props[prop_name]:
                    # Check if property is a relationship
                    if prop_name in self.special_rels.keys():
                        rel_type = self.special_rels[prop_name]
                        ref_uri = self.tsconn.get_node_uri_by_props({
                            (nsc['rdf'].type, URIRef()),
                        })
                        if not ref_uri:
                            if ignore_broken_rels:
                                continue
                            else:
                                raise cherrypy.HTTPError(
                                    '404 Not Found',
                                    'Referenced CITI resource with CITI Pkey {} does not exist. Cannot create relationship.'.format(value)
                                )
                        value = ref_uri
                    elif prop_name == nsc['aic'].hasTag:
                        insert_nodes['tags'] = insert_props[prop_name]
                        #value = lake_rest_api['tags_base_url'] + value
                        continue
                    elif prop_name == nsc['aic'].hasComment:
                        insert_nodes['comments'] = insert_props[prop_name]
                        cherrypy.log('Found comments.')
                        continue
                    cherrypy.log('Value for {}: {}'.format(prop_name, value))
                    insert_tuples.append(
                        (prop_name, self._build_rdf_object(
                            value, prop[1], prop[2] if len(prop) > 2 else None
                        ))
                    )

        return {
            'nodes' : (delete_nodes, insert_nodes),
            'tuples' : (delete_tuples, insert_tuples, where_tuples),
        }


    def _build_rdf_object(self, value, type, datatype=None):
        '''Returns an RDF object from a value and a type.

        Depending on the value of @p type, a literal object, a URI or a variable (?var) is created.

        @param value    (string) Value to be processed.
        @oaram type     (string) One of 'literal', 'uri', 'variable'.
        @oaram datatype (string, optional) Data type for 'literal' type.

        @return (rdflib.URIRef | rdflib.Literal | rdflib.Variable) rdflib object.
        '''

        cherrypy.log('Converting value to RDF {} object: {}'.format(type, value))
        if type == 'uri':
            return URIRef(value)
        elif type == 'variable':
            return Variable(value)
        else:
            return Literal(value, datatype=datatype)


    def _insert_nodes_in_tuples(self, type, props):
        '''Performs additional operations for nodes to be added.

        Override this method in sub-classes.

        @param type (string) Node type name.
        @param props (list) List of dicts of properties (key: property name, value: property value)
            to be added to node. Each dict makes up a distinct node.

        @return (list) Insert tuples for the additional nodes.
        '''

        return []



    def _build_fquri_from_prefixed(self, name):
        '''Build a fully-qualify URI from a namespace prefixed name.

        This method uses the global namespace manager to determine prefixes.

        @param name (string) The namespaced URI (e.g. "aic:Asset")

        @return rdflib.URIRef The fully qualified URI.
        '''

        if not re.match('^[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-]+$', name):
            raise ValueError('\'{}\' is not a valid namespaced URI.'.format(name))

        parts = name.split(':')
        pfx = parts[0]

        if not pfx in nsc.keys():
            raise KeyError('Namespace prefix \'{}\' is not a known namespace prefix.'.format(pfx))

        return URIRef(nsc[pfx] + parts[1])



    def _open_transaction(self):
        '''Opens a transaction in LAKE and sets the #tx_uri property.

        NOTE: It is advisable to use the #temp_uri instead of #uri or #tx_uri where applicable.

        @return None
        '''

        self.tx_uri = self.lconn.open_transaction()



    def _commit_transaction(self):
        '''Commits a transaction and clears transaction URI members.

        @return None
        '''

        if self.lconn.commit_transaction(self.tx_uri):
            self.tx_uri = None
            self.uri_in_tx = None




    def _rollback_transaction(self):
        '''Rolls back a transaction and clears transaction URI members.

        @return None
        '''

        if self.lconn.rollback_transaction(self.tx_uri):
            self.tx_uri = None
            self.uri_in_tx = None




