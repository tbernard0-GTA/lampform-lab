WEIGHTS = dict(p95=.35, maximum=.25, std=.15, material=.15, open_area=.10)


def score(metrics, baseline, weights=None):
    w = {**WEIGHTS, **(weights or {})}
    components = dict(p95=metrics['p95'] / max(baseline['p95'], 1e-9),
                      maximum=metrics['maximum'] / max(baseline['maximum'], 1e-9),
                      std=metrics['std'] / max(baseline['std'], 1e-9),
                      material=metrics['material_area_proxy'] / baseline['material_area_proxy'],
                      open_area=1 + max(0., (baseline['open_area'] - metrics['open_area']) / baseline['open_area']))
    value = sum(w[k] * components[k] for k in w)
    improvement = {key: 100 * (baseline[key] - metrics[key]) / max(abs(baseline[key]), 1e-9)
                   for key in ['p95', 'maximum', 'std', 'material_area_proxy']}
    return dict(value=value, components=components, weights=w, improvement_vs_original=improvement)
