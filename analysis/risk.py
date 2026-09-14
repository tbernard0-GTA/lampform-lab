"""Transparent, configurable risk classes and hard print-test gates."""
import numpy as np
THRESHOLDS = dict(moderate=10., high=20., critical=30.)
MAX_WORSENING_PP = 5.
RISK_WEIGHTS = dict(p95=.30, p99=.25, maximum=.25, critical_fraction=.20)

def classify(value):
    return 'CRITICAL' if value > 30 else 'HIGH' if value >= 20 else 'MODERATE' if value >= 10 else 'LOW'

def enrich_metrics(result, baseline):
    m = result['metrics']; values = result['parent_demand']
    m['high_edges'] = int(np.sum(values > THRESHOLDS['high']))
    m['critical_edges'] = int(np.sum(values > THRESHOLDS['critical']))
    m['critical_fraction'] = float(np.mean(values > THRESHOLDS['critical']))
    m['critical_pct'] = 100 * m['critical_fraction']
    m['top10_mean'] = float(np.sort(values)[-10:].mean())
    base = baseline['metrics']
    # If baseline has no critical edges, use one edge as a denominator floor.
    components = {k: m[k] / max(base[k], 1 / m['edge_count'] if k == 'critical_fraction' else 1e-9)
                  for k in RISK_WEIGHTS}
    m['risk_index'] = float(sum(RISK_WEIGHTS[k] * components[k] for k in RISK_WEIGHTS))
    m['risk_components'] = components

def print_gate(candidate, baseline, manufacturing):
    m = candidate['metrics']; b = baseline['metrics']; v = candidate['validation']
    checks = dict(p95=m['p95'] < b['p95'], critical_edges=m['critical_edges'] < b['critical_edges'],
                  maximum=m['maximum'] <= b['maximum'] + MAX_WORSENING_PP,
                  watertight=v['watertight'], single_body=v['body_count'] == 1,
                  geometry=v['printable_geometry_checks_passed'], bounds=v.get('bounds_valid', True),
                  min_ligament=m['minimum_ligament_width'] >= manufacturing['min_ligament_mm'],
                  aperture_probe=v.get('aperture_probe_passed', False), solver_converged=candidate['solver']['success'])
    reasons = [key for key, ok in checks.items() if not ok]
    return dict(passed=not reasons, checks=checks, reasons=reasons,
                status='PASS' if not reasons else 'TRADE-OFF' if m['p95'] < b['p95'] else 'REJECTED')
