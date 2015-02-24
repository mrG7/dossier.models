from __future__ import absolute_import, division, print_function

import base64
import re

import dossier.web as web


class Folders(web.Folders):
    def subtopics(self, folder_id, subfolder_id, ann_id=None):
        '''Yields an unordered generator of subtopics in a subfolder.

        Each item of the generator is a 4-tuple of ``content_id``,
        ``subtopic_id``, ``subtopic_type`` and ``data``. Subtopic type
        is one of the following Unicode strings: ``text``, ``image``
        or ``manual``. The type of ``data`` is dependent on the
        subtopic type. For ``image``, ``data`` is a ``(unicode, str)``,
        where the first element is the URL and the second element is
        the binary image data. For all other types, ``data`` is a
        ``unicode`` string.

        :param str folder_id: Folder id
        :param str subfolder_id: Subfolder id
        :param str ann_id: Username
        :rtype: generator of
                ``(content_id, subtopic_id, subtopic_type, data)``
        '''
        # This code will be changed soon. In essence, it implements the
        # convention established in SortingDesk for storing subtopic data.
        # Currently, subtopic data is stored in the FC that the data (i.e.,
        # image or snippet) came from. This is bad because it causes pretty
        # severe race conditions.
        #
        # Our current plan is to put each subtopic datum in its own FC. It will
        # require this code to make more FC fetches, but we should be able to
        # do it with one `store.get_many` call.
        items = self.grouped_items(folder_id, subfolder_id, ann_id=ann_id)
        fcs = {cid: fc for cid, fc in self.store.get_many(items.keys())}
        for cid, subids in items.iteritems():
            fc = fcs[cid]
            for subid in subids:
                try:
                    data = typed_subtopic_data(fc, subid)
                except KeyError:
                    # We have a dangling label folks!
                    continue
                yield cid, subid, subtopic_type(subid), data


def typed_subtopic_data(fc, subid):
    '''Returns typed subtopic data from an FC.'''
    # I don't think this code will change after we fix the data race bug. ---AG
    ty = subtopic_type(subid)
    data = fc[subid]
    assert isinstance(data, unicode)
    if ty == 'image':
        img = re.sub('^data:image/[a-zA-Z]+;base64,', '', fc[subid + '|data'])
        img = base64.b64decode(img.decode('utf-8'))
        return data, img
    elif ty in ('text', 'manual'):
        return data
    raise ValueError('unrecognized subtopic type "%s"' % ty)


def subtopic_type(subid):
    return subid.split('|')[1]