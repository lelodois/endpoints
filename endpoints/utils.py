# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import mimetypes
import sys


class ByteString(bytes):
    def __new__(cls, val, encoding=""):
        if not encoding:
            encoding = sys.getdefaultencoding()

        if isinstance(val, unicode):
            val = val.encode(encoding)

        #instance = super(ByteString, cls).__new__(cls, val)
        instance = bytes(val)
        #instance.encoding = encoding
        return instance


class Path(str):
    def __new__(cls, s):
        s = os.path.abspath(os.path.expanduser(str(s)))
        return super(Path, cls).__new__(cls, s)


class MimeType(object):
    """This is just a thin wrapper around Python's built-in MIME Type stuff

    https://docs.python.org/2/library/mimetypes.html
    """

    @classmethod
    def find_type(cls, val):
        """return the mimetype from the given string value

        if value is a path, then the extension will be found, if val is an extension then
        that will be used to find the mimetype
        """
        mt = ""
        index = val.rfind(".")
        if index == -1:
            val = "fake.{}".format(val)
        elif index == 0:
            val = "fake{}".format(val)

        mt = mimetypes.guess_type(val)[0]
        if mt is None:
            mt = ""

        return mt


class AcceptHeader(object):
    """
    wraps the Accept header to allow easier versioning

    provides methods to return the accept media types in the correct order
    """
    def __init__(self, header):
        self.header = header
        self.media_types = []

        if header:
            accepts = header.split(',')
            for accept in accepts:
                accept = accept.strip()
                a = accept.split(';')

                # first item is the media type:
                media_type = self._split_media_type(a[0])

                # all other items should be in key=val so let's add them to a dict:
                params = {}
                q = 1.0 # default according to spec
                for p in a[1:]:
                    pk, pv = p.strip().split('=')
                    if pk == 'q':
                        q = float(pv)
                    else:
                        params[pk] = pv

                #pout.v(media_type, q, params)
                self.media_types.append((media_type, q, params, accept))

    def _split_media_type(self, media_type):
        """return type, subtype from media type: type/subtype"""
        media_type_bits = media_type.split('/')
        return media_type_bits

    def _sort(self, a, b):
        '''
        sort the headers according to rfc 2616 so when __iter__ is called, the accept media types are
        in order from most preferred to least preferred
        '''
        ret = 0

        # first we check q, higher values win:
        if a[1] != b[1]:
            ret = cmp(a[1], b[1])
        else:
            found = False
            for i in xrange(2):
                ai = a[0][i]
                bi = b[0][i]
                if ai == '*':
                    if bi != '*':
                        ret = -1
                        found = True
                        break
                    else:
                        # both *, more verbose params win
                        ret = cmp(len(a[2]), len(b[2]))
                        found = True
                        break
                elif bi == '*':
                    ret = 1
                    found = True
                    break

            if not found:
                ret = cmp(len(a[2]), len(b[2]))

        return ret

    def __iter__(self):
        sorted_media_types = sorted(self.media_types, self._sort, reverse=True)
        for x in sorted_media_types:
            yield x

    def filter(self, media_type, **params):
        """
        iterate all the accept media types that match media_type

        media_type -- string -- the media type to filter by
        **params -- dict -- further filter by key: val

        return -- generator -- yields all matching media type info things
        """
        mtype, msubtype = self._split_media_type(media_type)
        for x in self.__iter__():
            # all the params have to match to make the media type valid
            matched = True
            for k, v in params.items():
                if x[2].get(k, None) != v:
                    matched = False
                    break

            if matched:
                if x[0][0] == '*':
                    if x[0][1] == '*':
                        yield x

                    elif x[0][1] == msubtype:
                        yield x

                elif mtype == '*':
                    if msubtype == '*':
                        yield x

                    elif x[0][1] == msubtype:
                        yield x

                elif x[0][0] == mtype:
                    if msubtype == '*':
                        yield x

                    elif x[0][1] == '*':
                        yield x

                    elif x[0][1] == msubtype:
                        yield x

