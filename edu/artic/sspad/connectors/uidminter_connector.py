import psycopg2
from edu.artic.sspad.config.datasources import uidminter_db

class UidminterConnector:
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
	
