from collections import OrderedDict

import cherrypy

from sspad.connectors.tstore_connector import TstoreConnector
from sspad.resources.rdf_lexicon import ns_collection as nsc, ns_pfx_sparql

class Search():
    '''@package sspad.modules

    Search module.

    Handles SPARQL queries and metainformation about query terms.

    @author Stefano Cossu <scossu@artic.edu>
    @date 01/13/2015
    '''


    def __init__(self):
        '''Sets up connection to triplestore index endpoint.

        @return None
        '''

        self.tsconn = TstoreConnector()



    @property
    def comp_list(self):
        return {
            'string' : OrderedDict((
                ('contains', 'Contains'),
                ('not_contains', 'Does not contain'),
                ('starts_with', 'Starts with'),
                ('not_starts_with', 'Does not sart with'),
                ('ends_with', 'Ends with'),
                ('not_ends_with', 'Does not end with'),
                ('str_matches', 'Matches exactly'),
            )),
            'number' : OrderedDict((
                ('eq', 'Is Equal To'),
                ('ne', 'Is Not Equal To'),
                ('lt', 'Is Less Than'),
                ('lte', 'Is Less Or Equal To'),
                ('gt', 'Is Greater Than'),
                ('gte', 'Is Greater Or Equal To'),
            )),
            'date' : OrderedDict((
                ('before', 'Before'),
                ('after', 'After'),
                ('date_matches', 'Exactly'),
            )),
            'uri' : OrderedDict((
                ('uri', 'Has URI'),
            )),
        }


    @property
    def comp_expressions(self):
        return {
            'contains' : '{} <{}> ?p .\nFILTER(contains(?p, "{}"))',
            'not_contains' : '{} <{}> ?p .\nFILTER NOT EXISTS{{FILTER(contains(?p, "{}"))}}',
            'starts_with' : '{} <{}> ?p .\nFILTER(strStarts(?p, "{}"))',
            'not_starts_with' : '{} <{}> ?p .\nFILTER NOT EXISTS{{FILTER(strStarts(?p, "{}"))}}',
            'ends_with' : '{} <{}> ?p .\nFILTER(strEnds(?p, "{}"))',
            'not_ends_with' : '{} <{}> ?p .\nFILTER NOT EXISTS{{FILTER(strEnds(?p, "{}"))}}',
            'str_matches' : '{} <{}> ?p .\nFILTER(?p="{}")',
            'eq' : '{} <{}> ?p .\nFILTER(?p="{}")',
            'ne' : '{} <{}> ?p .\nFILTER NOT EXSITS{FILTER(?p="{}")}',
            'lt' : '{} <{}> ?p .\nFILTER(?p<"{}")',
            'lte' : '{} <{}> ?p .\nFILTER(?p<="{}")',
            'gt' : '{} <{}> ?p .\nFILTER(?p>"{}")',
            'gte' : '{} <{}> ?p .\nFILTER(?p>="{}")',
            'before' : '{} <{}> ?p .\nFILTER(?p<"{}"^^xsd:dateTime)',
            'after' : '{} <{}> ?p .\nFILTER(?p>"{}"^^xsd:dateTime)',
            'date_matches' : '{} <{}> ?p .\nFILTER(?p="{}"^^xsd:date)',
            'uri' : '{} <{}> <{}>',
        }



    def get_terms(self, ent=None, subj=None, prop=None):
        '''@sa SearchCtrl::GET()'''

        if ent and subj and prop:
            # Get comparators
            q = '''{}\nSELECT DISTINCT ?dtype WHERE {{
            <{}> rdfs:range ?dtype .
            }}
            '''.format('\n'.join(ns_pfx_sparql.values()), prop)
            dtype = self.tsconn.query(q)[0]['dtype']

            #cherrypy.log('Data type comps: {}'.format(self.comp_list))
            #cherrypy.log('dtype: {}'.format(self.comp_list[dtype]))

            if dtype == str(nsc['xsd'].string) or \
                    dtype == None:
                comp_list = self.comp_list['string']
            elif dtype == str(nsc['xsd'].integer) or \
                    dtype == str(nsc['xsd'].int) or \
                    dtype == str(nsc['xsd'].long):
                comp_list = self.comp_list['number']
            elif dtype == str(nsc['xsd'].date) or \
                    dtype == str(nsc['xsd'].dateTime):
                comp_list = self.comp_list['date']
            else:
                comp_list = self.comp_list['uri']

            return [{
                'label' : comp_list[x],
                'id' : x
                } for x in comp_list]

        elif ent and subj:
            # Get property list
            q = '''{}\nSELECT DISTINCT ?prop ?label WHERE {{
                <{}> lakeschema:hasQuerySubject ?qs .
                ?qs lakeschema:id "{}" .
                ?qs lakeschema:class/rdfs:subClassOf ?qsclass .
                ?pcont lakeschema:hasVProperty ?vprop .
                ?vprop lakeschema:subjClass ?qsclass .
                {{
                    ?vprop lakeschema:property ?prop .
                    ?prop skos:prefLabel ?label .
                }} UNION  {{
                    ?vprop lakeschema:compoundProperty ?cprop .
                    ?cprop lakeschema:property ?prop .
                    ?cprop skos:prefLabel ?label .
                }}

            }}
            ORDER BY ?label
            '''.format('\n'.join(ns_pfx_sparql.values()), ent, subj)
            res = self.tsconn.query(q)

            return [{'label' : x['label'], 'id' : x['prop']}  for x in res]

        elif ent:
            # Get subject list
            q = '''{}\n SELECT DISTINCT ?id ?label WHERE {{
                <{}> lakeschema:hasQuerySubject ?qp .
                ?qp skos:prefLabel ?label .
                ?qp lakeschema:id ?id .
                ?qp lakeschema:order ?o
            }}
            ORDER BY ?o
            '''.format('\n'.join(ns_pfx_sparql.values()), ent)
            res = self.tsconn.query(q)

            return [{'label' : x['label'], 'id' : x['id']}  for x in res]

        else:
            # Get entity list
            q = '''{}\n SELECT DISTINCT ?ent ?label WHERE {{
                ?ent lakeschema:hasQuerySubject ?qs .
                ?ent skos:prefLabel ?label .
            }}
            ORDER BY ?label
            '''.format('\n'.join(ns_pfx_sparql.values()), ent)
            res = self.tsconn.query(q)

            return [{'label' : x['label'], 'id' : x['ent']}  for x in res]




    def query(self, ent, conditions):
        cherrypy.log('Query conditions: {}'.format(conditions))
        pq = '''{}\nSELECT DISTINCT ?sp ?sc ?pp WHERE {{
            <{}> lakeschema:hasQuerySubject ?qs .
            ?qs lakeschema:id "{}" .
            ?qs lakeschema:class ?sc .
            OPTIONAL {{
              ?qs lakeschema:subjectPath ?sp .
            }} OPTIONAL {{
              ?vp lakeschema:property <{}> ;
                lakeschema:path ?pp .
            }} OPTIONAL {{
              ?vp lakeschema:compoundProperty/lakeschema:property <{}> ;
                lakeschema:path ?pp .
            }}
        }}
        '''.format(
            '\n'.join(ns_pfx_sparql.values()),
            ent,
            conditions[0]['subj'],
            conditions[0]['prop'],
            conditions[0]['prop']
        )
        p_res = self.tsconn.query(pq)

        has_sp = True if p_res and 'sp' in p_res[0].keys() else False
        has_pp = True if p_res and 'pp' in p_res[0].keys() else False

        subj_var = '?subj' if has_sp else '?ent'
        prop_cont_var = '?pCont' if has_pp else '?subj'

        q = '''{}\nSELECT DISTINCT ?ent WHERE {{
                ?ent a <{}> .
                {}{}{} .{}
            }}
            '''.format(
                '\n'.join(ns_pfx_sparql.values()),
                ent if has_sp else p_res[0]['sc'],
                (p_res[0]['sp'] + '\n') \
                        if has_sp else '',
                (p_res[0]['pp'] + '\n') \
                        if has_pp else '',
                self.comp_expressions[conditions[0]['comp']].format(
                    prop_cont_var,
                    conditions[0]['prop'],
                    conditions[0]['value']
                ),
                '\nFILTER(?subj=?ent) .' if not has_sp else ''
            )
        cherrypy.log('Query string: {}'.format(q))

        return self.tsconn.query(q)

