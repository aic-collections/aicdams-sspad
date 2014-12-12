from sspad.config.datasources import lake_rest_api
from sspad.controllers.sspad_controller import SspadController
from sspad.models.tag_cat import TagCat


class TagCatCtrl(SspadController):
    '''Tag Category Controller class.

    Handles operations with LAKE tag categories.

    @package sspad.controllers
    '''


    exposed = True


    @property
    def model(self):
        '''@sa SspadController::model'''

        return TagCat



    def GET(self, label=None):
        '''Get a category URI from a label or a list of categories.

        @param label (string, optional) Category label. If empty (default),
            a list of all categoies is returned; otherwise, a single category URI is returned.

        @return (string | list) Category URI or list of categories.
        '''

        return self.model().get_uri(label) \
                if label \
                else self.model().list()


    def POST(self, label):
        '''Create a tag category with a given label.

        @param label (string) Category label.

        @return (string) New category URI.
        '''

        return self.model().create(label)

