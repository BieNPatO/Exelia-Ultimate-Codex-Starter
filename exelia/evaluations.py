"""Honest, locally recorded agent run evidence; never invent token/cost metrics."""
from __future__ import annotations
import json
import math
from pathlib import Path
from .common import ROOT, save, utc, valid_task


def path(root):
    return root / '.exelia' / 'evals' / 'runs.jsonl'


def record(root: Path = ROOT, *, task: str, agent: str, model: str, outcome: str,
           duration: float | None = None, tokens: int | None = None, cost: float | None = None,
           evidence: str = ''):
    valid_task(task)
    if outcome not in ('pass', 'fail', 'blocked'):
        raise ValueError('Outcome must be pass/fail/blocked')
    if not all([agent.strip(), model.strip(), evidence.strip()]):
        raise ValueError('Agent, model and actual evidence are required.')
    for val in (duration, tokens, cost):
        if val is not None and (not math.isfinite(val) or val < 0):
            raise ValueError('Metrics must be nonnegative and finite.')
    result = {'timestamp': utc(), 'task': task, 'agent': agent, 'model': model, 'outcome': outcome,
              'seconds': duration, 'tokens': tokens, 'usd': cost, 'evidence': evidence.strip()}
    file = path(root)
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(result, ensure_ascii=False) + '\n')
    return result


def summary(root: Path = ROOT):
    file = path(root)
    rows = [json.loads(line) for line in file.read_text(encoding='utf-8').splitlines() if line.strip()] if file.exists() else []
    groups = {}
    for row in rows:
        key = (row['agent'], row['model'])
        item = groups.setdefault(key, {'agent': key[0], 'model': key[1], 'runs': 0, 'passed': 0,
                                       'failed': 0, 'blocked': 0, 'duration_measured': 0,
                                       'seconds_total': 0, 'token_measured': 0, 'tokens_total': 0,
                                       'cost_measured': 0, 'usd_total': 0})
        item['runs'] += 1
        item[{'pass':'passed','fail':'failed','blocked':'blocked'}[row['outcome']]] += 1
        for name, count_key, total_key in [('seconds','duration_measured','seconds_total'),
                                            ('tokens','token_measured','tokens_total'), ('usd','cost_measured','usd_total')]:
            if row.get(name) is not None:
                item[count_key] += 1
                item[total_key] += row[name]
    return {'total_runs': len(rows), 'by_agent_model': list(groups.values()),
            'note': 'Only user-recorded measurements. Missing metrics are not inferred. Samples are not randomized benchmarks.'}
