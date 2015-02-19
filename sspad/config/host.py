## Host-specific settings are imported from config file and parsed here.
import sys
import argparse
import configparser

parser = argparse.ArgumentParser(description = 'SSPAD - Shared Service Provider for the AIC DAMS')
parser.add_argument('-c', '--config', default='/etc/sspad.conf', help='Configuration file path.')
args = parser.parse_args()
#print('Args: {}'.format(args))
config_file = args.config

config = configparser.ConfigParser()
config.read(config_file)

host = {
    'app_env' : config['host']['app_env'],
    'pidfile' : config['host']['pidfile'],
    'listen_addr' : config['host']['listen_addr'],
    'listen_port' : int(config['host']['listen_port']),
    'max_req_size' : int(config['host']['max_req_size']),
}

## This application's path
app_path = sys.argv[0]


