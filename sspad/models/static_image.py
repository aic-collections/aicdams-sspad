import cherrypy

from wand import image

from sspad.config.datasources import lake_rest_api, datagrinder_rest_api
from sspad.models.asset import Asset
from sspad.resources.rdf_lexicon import ns_collection


class StaticImage(Asset):
	'''Static Image model class.

	This class runs and manages Image actions.

	@package sspad.models
	'''

	@property
	def pfx(self):
		'''@sa Resource::pfx'''

		return  'SI'



	@property
	def node_type(self):
		return ns_collection['aic'].StillImage



	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'citi_imgdbank_pkey',
			#'view_info',
		)



	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['aic'].citiImgDBankUid, 'literal', 'string'),
			#(ns_collection['aic'].viewInfo, 'literal'),
		)



	def _generateMasterFile(self, file, fname):
		'''Generate a master datastream from a source image file.

		@param file (StringIO) Input file.
		@param fname (string) downloaded file name.

		@return (BytesIO) master file.
		'''
		# @TODO put these values in constants
		ret = cherrypy.request.app.config['connectors']['dgconn'].resizeImageFromData(file, fname, 4096, 4096)
		return ret



	def _validate_datastream(self, ds, dsname='', rules={}):
		'''Checks that the input file is a valid image.

		@sa #Resource::_validate_datastream()

		@param ds (BytesIO) Datastream to be validated.
		@param dsname (string, optional) Datastream name. This is just used for logging purposes. TODO eliminate
		@param rules (dict, optional) Additional validation rules. By default, the method only
			checks whether the file is a valid image.
			@TODO Add more rules. So far only 'mimetype' is supported.
		'''

		ds.seek(0)
		cherrypy.log('Validating ds: ' + dsname + ' of type: ' + str(ds))
		with image.Image(file=ds) as img:
			format = img.format
			mimetype = img.mimetype
			size = img.size
			cherrypy.log(' Image format: ' + format + ' MIME type: ' + mimetype + ' size: ' + str(size))

		ds.seek(0)

		if 'mimetype' in rules:
			if mimetype != rules['mimetype']:
				raise TypeError('MIME type of uploaded image does not match the expected one.')
		return {'format': format, 'size': size, 'mimetype': mimetype}

