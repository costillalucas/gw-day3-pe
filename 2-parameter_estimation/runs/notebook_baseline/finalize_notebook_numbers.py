"""
Enrich notebook_numbers.json with median standard errors and the
evidence standard error, computed with pe.py's own helper functions, so
the notebook-run numbers and the CLI-run numbers are post-processed
identically. Reuses the already-computed rundir outputs -- no
re-sampling.
"""
import json
import sys
from pathlib import Path

import nautilus
import pandas as pd

HERE = Path(__file__).resolve().parent

sys.path.insert(0, str(HERE.parent.parent))
import pe  # noqa: E402

RUNDIR = HERE / 'pe_runs/IntrinsicAlignedSpinIASPrior/GW0/run_0'

with open(HERE / 'notebook_numbers.json') as f:
    numbers = json.load(f)

samples = pd.read_feather(RUNDIR / 'samples.feather')
pe.add_derived_quantities(samples)

plot_params = numbers['plot_params']
medians_se = pe.median_standard_errors(samples, plot_params)

dummy_kwargs = {'prior': lambda _: 0, 'likelihood': lambda _: 0, 'n_dim': 2}
nsampler = nautilus.Sampler(**dummy_kwargs, filepath=str(RUNDIR / 'checkpoint.hdf5'))
n_eff_nautilus = float(nsampler.n_eff)
lnZ_se = 1.0 / n_eff_nautilus ** 0.5

numbers['medians_standard_error'] = medians_se
numbers['evidence'] = {
    'lnZ': numbers['evidence']['log_ev'],
    'lnZ_standard_error': lnZ_se,
    'n_eff_nautilus': n_eff_nautilus,
}

with open(HERE / 'notebook_numbers.json', 'w') as f:
    json.dump(numbers, f, indent=2, default=str)

print(json.dumps(numbers, indent=2, default=str))
