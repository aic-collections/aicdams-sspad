import cherrypy

from wand import image

from sspad.config.datasources import lake_rest_api, datagrinder_rest_api
from sspad.modules.asset import Asset
from sspad.resources.rdf_lexicon import ns_collection


## Static Image class.
#
#  This class runs and manages Image actions.
class StaticImage(Asset):

	exposed = True


	## @sa Resource#pfx
	pfx = 'SI'


	## @sa Resource#node_type
	node_type = ns_collection['aic'].StillImage


	@property
	def prop_req_names(self):
		return super().prop_req_names + (
			'citi_imgdbank_pkey',
			#'view_info',
		)


	@property
	def prop_lake_names(self):
		return super().prop_lake_names + (
			(ns_collection['aic'].citiImgDBankUid, 'literal'),
			#(ns_collection['aic'].viewInfo, 'literal'),
		)


	## Generate a master datastream from a source image file.
	#
	#  @param file (StringIO) Input file.
	#  @param fname (string) downloaded file name.
	def _generateMasterFile(self, file, fname):
		# @TODO put these values in constants
		ret = self.dgconn.resizeImageFromData(file, fname, 4096, 4096)
		return ret


	## Checks that the input file is a valid image.
	#
	#  @sa #Resource._validate_datastream
	#  @TODO more rules. So far only 'mimetype' is supported.
	def _validate_datastream(self, ds, dsname='', rules={}):

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
