from sspad.controllers.asset_ctrl import AssetCtrl
from sspad.models.static_image import StaticImage


class StaticImage(AssetCtrl):
	'''Static Image class.

	This class runs and manages Image actions.
	'''

	exposed = True

	@property
	def model(self):
		'''@see AssetCtrl::model'''

		return StaticImage
