"""Check documentation anchors and prospective-plan consistency, without experiments.

Run from any working directory with Python 3.10+. Uses only the standard library.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def pointer(document, path):
    value = document
    for segment in path.strip('/').split('/'):
        segment = segment.replace('~1', '/').replace('~0', '~')
        value = value[int(segment)] if isinstance(value, list) else value[segment]
    return value


def main():
    refs = json.loads((HERE / 'source_refs.json').read_text(encoding='utf-8'))
    cache = {}
    for item in refs['source_values']:
        source = item['path']
        if source not in cache:
            cache[source] = json.loads((ROOT / source).read_text(encoding='utf-8'))
        actual = pointer(cache[source], item['pointer'])
        expected = item['expected']
        if isinstance(expected, float):
            assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10), item['id']
        else:
            assert actual == expected, item['id']
    values = {item['id']: item['expected'] for item in refs['source_values']}
    derived = {
        'advice_mean_improvement_percent': 100 * (values['audit_rossmann_mean'] - values['audit_advice_mean']) / values['audit_rossmann_mean'],
        'episode_mean_change': values['audit_episode_sensitivity_mean'] - values['audit_rossmann_mean'],
        'meta_vs_weekday_point_improvement_percent': 100 * (values['benchmark_weekday_frozen'] - values['benchmark_meta_frozen']) / values['benchmark_weekday_frozen'],
    }
    for item in refs['derived_quantities']:
        if 'row_filter' in item:
            with (ROOT / item['path']).open(encoding='utf-8', newline='') as handle:
                rows = [row for row in csv.DictReader(handle) if all(row[key] == value for key, value in item['row_filter'].items())]
            assert len(rows) == 1, item['id']
            actual = float(rows[0][item['field']])
        else:
            actual = derived[item['id']]
        assert math.isclose(actual, item['expected'], rel_tol=1e-10, abs_tol=1e-10), item['id']
    links = 0
    for source in [HERE / 'README.md', HERE / 'playbook_vi.md', ROOT / 'docs/stress_test_plan.md']:
        for uri in re.findall(r'\]\(([^)]+)\)', source.read_text(encoding='utf-8')):
            if not re.match(r'https?://', uri):
                assert (source.parent / uri.split('#')[0]).resolve().exists(), (source, uri)
                links += 1
    plan = json.loads((ROOT / 'experiments/stress_tests/plan.json').read_text(encoding='utf-8'))
    assert plan['status'] == 'PLANNED_NOT_EXECUTED'
    assert not plan['runner_available']
    assert set(plan['models']) == {'hql', 'meta_hql', 'fql', 'mimic_ql'}
    ids = [test['id'] for test in plan['tests']]
    assert len(ids) == len(set(ids))
    assert all(test['status'] == 'PLANNED' for test in plan['tests'])
    splits = [set(plan['seed_strategy'][key]) for key in ['calibration', 'validation', 'locked_test', 'reserve_confirmation']]
    assert all(not a.intersection(b) for i, a in enumerate(splits) for b in splits[i+1:])
    assert not plan['video_contract']['subtitles']
    assert not plan['video_contract']['voice']
    assert not plan['video_contract']['screen_recording']
    for path in plan['source_contracts']:
        assert (ROOT / path).is_file(), path
    print(json.dumps({'documentation_checks': 'passed', 'source_values_checked': len(refs['source_values']), 'derived_quantities_checked': len(refs['derived_quantities']), 'local_links_checked': links, 'planned_test_ids': len(ids), 'stress_tests_executed': 0}, indent=2))


if __name__ == '__main__':
    main()
