import cherrypy

from rdflib import XSD

from sspad.config.datasources import lake_rest_api, datagrinder_rest_api
from sspad.models.asset import Asset
from sspad.resources.rdf_lexicon import ns_collection as nsc


class Text(Asset):
    '''Static Image model class.

    This class runs and manages Text assets.

    @package sspad.models
    '''

    @property
    def pfx(self):
        '''@sa Resource::pfx'''

        return  'TX'



    @property
    def node_type(self):
        '''@sa SspadModel::node_types'''

        return nsc['laketype'].Text



    def _generateMasterFile(self, file, fname):
        '''Generate a master datastream from a source image file.

        @TODO Stub. Just returns the original file.

        @param file (StringIO) Input file.
        @param fname (string) downloaded file name.

        @return (BytesIO) master file.
        '''
        return file.read()



    def _validate_datastream(self, ds, dsname='', rules={}):
        '''Checks that the input file is a valid text file.

        @TODO Stub

        @sa #Resource::_validate_datastream()

        @param ds (BytesIO) Datastream to be validated.
        @param dsname (string, optional) Datastream name. This is just used for logging purposes. TODO eliminate
        @param rules (dict, optional) Additional validation rules. By default, the method only
            checks whether the file is a valid image.
            @TODO Add more rules. So far only 'mimetype' is supported.
        '''

        return {}

