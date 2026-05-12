import multiprocessing as mp
from multiprocessing import Pool
from scoring import ScoringMatrix
from align import smith_waterman, is_gpu_available


def _align_single(args):
    query_seq, ref_seq, scoring_kwargs, use_banded, band_width = args
    
    scoring = ScoringMatrix(**scoring_kwargs)
    
    if use_banded:
        from banded_align import banded_smith_waterman
        result = banded_smith_waterman(query_seq, ref_seq, scoring=scoring, band_width=band_width)
    else:
        result = smith_waterman(query_seq, ref_seq, scoring=scoring)
    
    return result


def batch_align(queries, reference, num_workers=None, use_banded=False, band_width=50, scoring_kwargs=None):
    if scoring_kwargs is None:
        scoring_kwargs = {}
    
    if num_workers is None:
        num_workers = mp.cpu_count() - 1
        if num_workers < 1:
            num_workers = 1
    
    ref_seq = reference.seq if hasattr(reference, 'seq') else reference
    
    tasks = []
    for query in queries:
        query_seq = query.seq if hasattr(query, 'seq') else query
        tasks.append((query_seq, ref_seq, scoring_kwargs, use_banded, band_width))
    
    if num_workers == 1:
        results = []
        for task in tasks:
            results.append(_align_single(task))
        return results
    
    with Pool(processes=num_workers) as pool:
        results = pool.map(_align_single, tasks)
    
    return results


def batch_align_pairs(query_ref_pairs, num_workers=None, use_banded=False, band_width=50, scoring_kwargs=None):
    if scoring_kwargs is None:
        scoring_kwargs = {}
    
    if num_workers is None:
        num_workers = mp.cpu_count() - 1
        if num_workers < 1:
            num_workers = 1
    
    tasks = []
    for query, ref in query_ref_pairs:
        query_seq = query.seq if hasattr(query, 'seq') else query
        ref_seq = ref.seq if hasattr(ref, 'seq') else ref
        tasks.append((query_seq, ref_seq, scoring_kwargs, use_banded, band_width))
    
    if num_workers == 1:
        results = []
        for task in tasks:
            results.append(_align_single(task))
        return results
    
    with Pool(processes=num_workers) as pool:
        results = pool.map(_align_single, tasks)
    
    return results


class AlignmentPipeline:
    def __init__(self, reference, num_workers=None, use_gpu=None, use_banded=False, band_width=50):
        self.reference = reference
        self.num_workers = num_workers
        self.use_gpu = use_gpu if use_gpu is not None else is_gpu_available()
        self.use_banded = use_banded
        self.band_width = band_width
        self.scoring = ScoringMatrix()
    
    def align(self, queries):
        return batch_align(
            queries=queries,
            reference=self.reference,
            num_workers=self.num_workers,
            use_banded=self.use_banded,
            band_width=self.band_width,
            scoring_kwargs={
                'gap_open': self.scoring.gap_open,
                'gap_extend': self.scoring.gap_extend,
                'use_affine': self.scoring.use_affine
            }
        )
    
    def __call__(self, queries):
        return self.align(queries)


def get_optimal_workers():
    return max(1, mp.cpu_count() - 1)
