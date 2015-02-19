## Config file for all data source settings.
#
#  This file is under source control. DO NOT PUT ANY HOST-SPECIFIC AND LESS THAN EVER SENSITIVE DATA HERE!
#  All host-dependent settings should be imported from host.conf.

from sspad.config.host import config
#print('Config: {}'.format(config))

uidminter_db = config['uidminter_db']
uidminter_db['conn_string'] = 'host={} port={} user={} password={} dbname={}'.format(
    uidminter_db['host'],
    uidminter_db['port'],
    uidminter_db['username'],
    uidminter_db['password'],
    uidminter_db['db']
)


datagrinder_rest_api = config['datagrinder_rest_api']
datagrinder_rest_api['base_url'] = '{}://{}{}'.format(
    datagrinder_rest_api['proto'],
    datagrinder_rest_api['host'],
    datagrinder_rest_api['root']
)


lake_rest_api = config['lake_rest_api']
lake_rest_api['base_url'] = '{}://{}{}'.format(
    lake_rest_api['proto'],
    lake_rest_api['host'],
    lake_rest_api['root']
)


tstore_rest_api = config['tstore_rest_api']
tstore_rest_api['base_url'] = '{}://{}{}'.format(
    tstore_rest_api['proto'],
    tstore_rest_api['host'],
    tstore_rest_api['root']
)
