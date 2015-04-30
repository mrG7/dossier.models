from __future__ import absolute_import, division, print_function

import argparse
import multiprocessing
import sys

from gensim import models

from dossier.fc import FeatureCollectionChunk
from dossier.store import Store
from dossier.models.etl import Ads, Scrapy, add_sip_to_fc
import kvlayer
import yakonfig


def batch_progress(cids_and_fcs, add, limit=5, batch_size=100):
    def status(*args, **kwargs):
        kwargs['end'] = ''
        args = list(args)
        args[0] = '\033[2K\r' + args[0]
        print(*args, **kwargs)
        sys.stdout.flush()

    batch = []
    for i, (cid, fc) in enumerate(cids_and_fcs, 1):
        if fc is None:
            continue
        if not any(cid == cid2 for cid2, _ in batch):
            # Since we can restart the scanner, we may end up regenerating
            # FCs for the same key in the same batch. This results in
            # undefined behavior in kvlayer.
            batch.append((cid, fc))

        if len(batch) >= batch_size:
            add(batch)
            batch = []
        if i % 100 == 0:
            status('%d of %s done'
                   % (i, 'all' if limit is None else str(limit)))
    if len(batch) > 0:
        add(batch)


class App(yakonfig.cmd.ArgParseCmd):
    def __init__(self, *args, **kwargs):
        yakonfig.cmd.ArgParseCmd.__init__(self, *args, **kwargs)
        self._store = None
        self._chunk = None
        self.tfidf = None

    @property
    def store(self):
        if self._store is None:
            feature_indexes = None
            try:
                conf = yakonfig.get_global_config('dossier.store')
                feature_indexes = conf['feature_indexes']
            except KeyError:
                pass
            self._store = Store(kvlayer.client(),
                                feature_indexes=feature_indexes)
        return self._store

    def done(self):
        if self._chunk is not None:
            self._chunk.flush()

    def get_output_accumulator(self, output_path=None):
        if output_path is not None:
            self._chunk = FeatureCollectionChunk(path=output_path, mode='wb')
        def add(cids_and_fcs):
            if self.tfidf is not None:
                for _, fc in cids_and_fcs:
                    add_sip_to_fc(fc, self.tfidf)
            if output_path is not None:
                for _, fc in cids_and_fcs:
                    self._chunk.add(fc)
            else:
                self.store.put(cids_and_fcs)
        return add

    def args_etl_ads(self, p):
        p.add_argument('--host', default='localhost')
        p.add_argument('--port', default=9090, type=int)
        p.add_argument('--table-prefix', default='')
        p.add_argument('--limit', default=5, type=int)
        p.add_argument('--batch-size', default=1000, type=int)
        p.add_argument('--start', default=None, type=str)
        p.add_argument('--stop', default=None, type=str)
        p.add_argument('-p', '--processes',
                       default=multiprocessing.cpu_count(), type=int)
        p.add_argument('-o', '--output', default=None)
        p.add_argument('--tfidf', default=None, type=str,
                       help='Path to TF-IDF background model. Can be '
                            'generated with the `dossier.etl tfidf` script.')

    def do_etl_ads(self, args):
        if args.tfidf is not None:
            self.tfidf = models.TfidfModel.load(args.tfidf_model_path)

        pool = multiprocessing.Pool(processes=args.processes)
        etl = Ads(args.host, args.port, table_prefix=args.table_prefix)
        gen = etl.cids_and_fcs(args.start, args.stop, limit=args.limit or None,
                               pool=pool)
        self.etl(args, etl, gen)

    def args_etl_scrapy(self, p):
        p.add_argument('-p', '--processes',
                       default=multiprocessing.cpu_count(), type=int)
        p.add_argument('--batch-size', default=1000, type=int)
        p.add_argument('--limit', default=5, type=int)
        p.add_argument('-o', '--output', default=None)
        p.add_argument('--tfidf', default=None, type=str,
                       help='Path to TF-IDF background model. Can be '
                            'generated with the `dossier.etl tfidf` script.')
        p.add_argument('input',
                       help='Scrapy data. Only supports CSV format currently.')

    def do_etl_scrapy(self, args):
        if args.tfidf is not None:
            self.tfidf = models.TfidfModel.load(args.tfidf_model_path)

        pool = multiprocessing.Pool(processes=args.processes)
        etl = Scrapy(open(args.input))
        gen = etl.cids_and_fcs(limit=args.limit or None, pool=pool)
        self.etl(args, etl, gen)

    def etl(self, args, etl, gen):
        add = self.get_output_accumulator(args.output)
        try:
            batch_progress(gen, add, limit=args.limit or None,
                           batch_size=args.batch_size)
        finally:
            self.done()


def main():
    p = argparse.ArgumentParser(
        description='Utilities for generating FCs from artifacts.')
    app = App()
    app.add_arguments(p)
    args = yakonfig.parse_args(p, [kvlayer, yakonfig])
    app.main(args)


if __name__ == '__main__':
    main()
