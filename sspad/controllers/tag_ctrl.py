from sspad.controllers.sspad_controller import SspadController
from sspad.models.tag import Tag
from sspad.models.tag_cat import TagCat


class TagCtrl(SspadController):
    '''Tag Controller class.

    Handles operations with LAKE tags.

    @package sspad.controllers
    '''


    exposed = True


    @property
    def model(self):
        '''@sa SspadController::model'''

        return Tag



    def GET(self, cat_label=None, label=None):
        '''Get a tag or list of tags.

        @param cat_label (string, optional) Category label. If empty (default),
            a list of all tags is returned. Otherwise, a list of all tags for the
            category bearing that label is returned.
            This parameter is mandatory if label is not emppty.
        @param label (string, optional) Tag label. If empty (default), a list
            of tag is returned. Otherwise, the URI of a tag with the given label
            is returned.

        @return (string | list) List of tags URI, their labels and category URIs or a single tag URI.
        '''

        if label:
            cat_uri = TagCat().get_uri(cat_label)
            return self.model().get_uri(label, cat_label)
        else:
            return self.model().list(cat_label)



    def POST(self, cat, label):
        '''Create a tag with a given label under a category with the given label.

        @param cat (string) Category label.
        @param label (string) Tag label.

        @return (string) New category URI.
        '''

        return self.model().create(cat, label)

