import psycopg2
from sspad.config.datasources import uidminter_db

## UidminterConnector class.
#
#  Handles generation of persistent UIDs via uidminter service.
class UidminterConnector:

	config = uidminter_db

	## Generates a new persistent UID.
	#
	# @param UidminterConnector self Object pointer.
	# @param pfx (string) 2-letter prefix to use for the UID. Depends on the node type.
	# @param mid (string) Second prefix for certain node types.
	def mintUid(self, pfx, mid):
		try:
			session = psycopg2.connect(uidminter_db['conn_string'])
			cur = session.cursor()
		except:
			raise RuntimeError("Could not connect to PostgreSQL database.")

		cur.callproc('mintuid', (pfx, mid))
		new_uid = cur.fetchone()[0]
		#print('New UID: ', new_uid)

		session.commit()
		cur.close()
		session.close()

		return new_uid
	
