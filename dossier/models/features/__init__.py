'''
Feature extraction
==================
``dossier.models.features`` provides some convenience functions for
feature extraction.

.. This software is released under an MIT/X11 open source license.
   Copyright 2012-2015 Diffeo, Inc.

.. autofunction:: noun_phrases
'''
from __future__ import absolute_import
from dossier.models.features.basic import emails, image_urls, phones, a_urls
from dossier.models.features.basic import host_names, path_dirs
from dossier.models.features.sip import noun_phrases, sip_noun_phrases
from dossier.models.features.stopwords import stopwords
from dossier.models.features.names import entity_names

from dossier.extraction import usernames

__all__ = [
    'emails', 'image_urls', 'a_urls', 'phones',
    'noun_phrases', 'sip_noun_phrases',
    'entity_names',
    'stopwords', 'host_names', 'path_dirs', 'usernames'
]
