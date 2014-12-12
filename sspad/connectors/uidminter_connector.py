import cherrypy
import psycopg2
from sspad.config.datasources import uidminter_db

class UidminterConnector:
    '''UidminterConnector class.

    Handles generation of persistent UIDs via uidminter service.
    '''

    @property
    def conf(self):
        '''UIDMinter host configuration.

        @return dict
        '''

        return uidminter_db



    def mint_uid(self, pfx, mid):
        '''Generates a new persistent UID.

        @param UidminterConnector self Object pointer.
        @param pfx (string) 2-letter prefix to use for the UID. Depends on the node type.
        @param mid (string) Second prefix for certain node types.

        @return (string) New UID.
        '''

        try:
            session = psycopg2.connect(uidminter_db['conn_string'])
            cur = session.cursor()
        except:
            raise RuntimeError("Could not connect to PostgreSQL database.")

        #cherrypy.log('Minting UID with prefix {} and mid {}'.format(pfx, mid))
        cur.callproc('mintuid', (pfx, mid))
        new_uid = cur.fetchone()[0]
        #print('New UID: ', new_uid)

        session.commit()
        cur.close()
        session.close()

        return new_uid

