import cherrypy

from edu.artic.sspad.config import host

conf = {
    'global': {
		'log.access_file': '/var/log/sspad/access.log',
		'log.error_file': '/var/log/sspad/error.log',
		'server.max_request_body_size': host.max_req_size,
		'server.socket_host': host.listen_addr,
		'server.socket_port': host.listen_port,
    }
}

