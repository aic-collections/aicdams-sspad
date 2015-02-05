from sspad.controllers.asset_ctrl import AssetCtrl
from sspad.models.text import Text


class TextCtrl(AssetCtrl):
    '''Text Asset class.

    This class runs and manages Text assets.
    '''

    exposed = True

    @property
    def model(self):
        '''@see AssetCtrl::model'''

        return Text
