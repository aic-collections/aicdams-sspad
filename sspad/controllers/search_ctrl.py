import json

from sspad.controllers.sspad_controller import SspadController
from sspad.modules.search import Search

class SearchCtrl(SspadController):
    '''@package sspad.controllers

    Search controller.

    Retrieves search terms and performs queries on LAKE index.

    @author Stefano Cossu <scossu@artic.edu>
    @date 01/13/2015
    '''

    exposed = True

    @property
    def model(self):
        '''@sa SspadCtrl::model()'''

        return None



    def GET(self, result, ent=None, subj=None, prop=None, conditions=[]):
        '''GET method.

        Gets terms for building queries or performs query
            with the given terms.

        @param result (string) What to query.
            If the value is 'terms', the follow combination of parameters is allowed:
            @p ent, @p subj, @prop: null - returns list of entities
            @p ent: not null; @p subj, @prop: null - returns list of subjects
            @p ent, @p subj: not null; prop: null - returns list of properties
            @p ent, @p subj, @p prop: not null - returns list of comparators
            If the value is 'items', performs a query using the other parameters,
                all of which must be non-null.
        @param ent (string) The entity type to retrieve the subject list for
            when @p result is 'terms', or the type of entities to return when
            @p result is 'items'.
        @param subj (string) The subject to retrieve the property list for
            when @p result is 'terms'.
        @param prop (string) The property to retrieve the comparator list for
            when @p result is 'terms'.
        @param conditions (list): One or more condition lines to perform
            the query. when @p result is 'items'. Each condition line is a
            dict where keys are: subj, prop, comp, value. All of them
            must be non-null except for value (when a null value is searched).
        '''

        if result == 'terms':
            return Search().get_terms(ent, subj, prop)
        elif result == 'items':
            return Search().query(ent, json.loads(conditions))
        else:
            raise cherrypy.HTTPError(
                '400 Bad Request',
                'Search for \'{}\' is not supported.'.format(result)
            )



