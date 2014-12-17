#! /usr/bin/env py.test

import pytest

from sspad.models.annotation import Annotation
from sspad.models.test.test_model import TestModel

class TestAnnotation(TestModel):

    def test_list(self):
        a = Annotation()
        assert not a.list() == None

