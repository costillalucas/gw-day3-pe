"""
Build a sub-notebook containing only the notebook's ALIGNED-SPIN cells
(same source, same order, nothing edited), execute it end to end, and
dump the quantities point2-goal.md asks us to capture.

This does NOT run the precessing "Extra" cells (posterior_xode,
sampler_xode, samples_xode, multi_corner_plot, etc.) -- only
`sampler.load_evidence()` is pulled in from among the cells that live
after the "## Extra" heading, since it only touches the aligned-spin
`sampler` object.
"""
import json
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

# Run this script with its own directory as cwd (so `pe_runs/` lands next
# to it, matching the rundir paths recorded in notebook_numbers.json).
SRC_NB = str(Path(__file__).resolve().parent.parent.parent / "parameter_estimation.ipynb")
OUT_NB = "aligned_spin_executed.ipynb"
OUT_JSON = "notebook_numbers.json"

# Aligned-spin-path cell indices, in the order they appear in the notebook.
ALIGNED_CELL_INDICES = [
    1,   # imports
    3,   # _generate_injection_dic / get_event_data definitions + event_data = get_event_data()
    5,   # xlim + specgram
    7,   # t_merger_guess = 1.6
    10,  # whitened_td = event_data.get_whitened_td()
    11,  # multi-detector whitened plot
    12,  # single-detector whitened plot
    14,  # lal.MTSUN_SI
    16,  # zero-crossing picks (example solution)
    18,  # periods/times/frequencies
    20,  # linear fit of f^(-8/3) vs t
    21,  # mchirp_guess
    23,  # posterior = Posterior.from_event(...)
    25,  # posterior.likelihood.par_dic_0
    27,  # plot_whitened_wf of the reference fit
    29,  # sampler = cogwheel.sampling.Nautilus(posterior); run_kwargs
    30,  # %%time; rundir = sampler.get_rundir(...); sampler.run(rundir)
    32,  # samples = pd.read_feather(...)
    33,  # list(samples)
    35,  # add_derived_quantities definition
    36,  # plot_params
    38,  # corner_plot for the aligned-spin run
    52,  # sampler.load_evidence()  (aligned-spin sampler only)
]

CAPTURE_SOURCE = r"""
# --- point 2: capture the notebook's numbers for later comparison ---
import json
import numpy as np

def _weighted_median(values, weights):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    cdf = np.cumsum(weights) - 0.5 * weights
    cdf /= np.sum(weights)
    return float(np.interp(0.5, cdf, values))

_weights = samples['weights'].to_numpy() if 'weights' in samples else np.ones(len(samples))

_medians = {p: _weighted_median(samples[p], _weights) for p in plot_params}

_evidence = sampler.load_evidence()

_par_dic_0 = {k: (float(v) if not isinstance(v, str) else v)
              for k, v in posterior.likelihood.par_dic_0.items()}

# Sanity check against the known minimize_scalar bug: lnl_0 ~ SNR^2 / 2
# for a good reference-waveform fit. A healthy fit should show SNR ~ 24.8;
# the buggy old cogwheel checkout silently produces SNR ~ 3 instead.
_lnl_0 = posterior.likelihood.lnlike(posterior.likelihood.par_dic_0)
_ref_wf_snr = float(np.sqrt(2 * _lnl_0))
print(f"Reference-waveform fit SNR estimate: {_ref_wf_snr:.2f} "
      f"(expect ~24.8; ~3 would mean the minimize_scalar bug is present)")
if _ref_wf_snr < 10:
    raise RuntimeError(
        f"Reference-waveform SNR is {_ref_wf_snr:.2f}, suspiciously low -- "
        "looks like the known minimize_scalar bug. Aborting."
    )

_notebook_numbers = {
    'mchirp_guess': float(mchirp_guess),
    'ref_wf_snr': _ref_wf_snr,
    'par_dic_0': _par_dic_0,
    'plot_params': list(plot_params),
    'medians': _medians,
    'evidence': {'lnZ': float(_evidence[0]), 'lnZ_err': float(_evidence[1])}
                if isinstance(_evidence, tuple) else _evidence,
    'n_samples': int(len(samples)),
    'n_eff_effective': float(np.sum(_weights) ** 2 / np.sum(_weights ** 2)),
}

with open("notebook_numbers.json", "w") as f:
    json.dump(_notebook_numbers, f, indent=2, default=str)

print(json.dumps(_notebook_numbers, indent=2, default=str))
"""


# Environment fix, not a notebook edit for its own sake: the notebook's
# `get_event_data` does `asd_funcs = list(cogwheel.data.ASDS)`, assuming
# ASDS has exactly one entry per detector (3, for 'HLV'). The conda-forge
# cogwheel installed here (1.6.0) ships per-detector O3/O4 variants, so
# ASDS has 5 keys and `EventData.gaussian_noise` raises
# "Lengths of `detector_names` and `asd_funcs` should match." We pin one
# ASD per detector (O3, the only observing run common to H, L and V) --
# confirmed against cogwheel.data's own docstring/source, nothing looked
# up externally.
_BROKEN_ASD_LINE = "asd_funcs = list(cogwheel.data.ASDS)"
_FIXED_ASD_LINE = (
    "asd_funcs = ['asd_H_O3', 'asd_L_O3', 'asd_V_O3']  "
    "# pinned: see build_and_run_notebook.py"
)


def main():
    full_nb = nbformat.read(SRC_NB, as_version=4)
    cells = [full_nb.cells[i] for i in ALIGNED_CELL_INDICES]

    for cell in cells:
        if _BROKEN_ASD_LINE in cell.source:
            cell.source = cell.source.replace(_BROKEN_ASD_LINE, _FIXED_ASD_LINE)

    capture_cell = nbformat.v4.new_code_cell(source=CAPTURE_SOURCE)
    cells.append(capture_cell)

    sub_nb = nbformat.v4.new_notebook(cells=cells, metadata=full_nb.metadata)

    client = NotebookClient(
        sub_nb,
        kernel_name="python3",
        timeout=-1,
        allow_errors=False,
    )

    t0 = time.time()
    client.execute(cwd=".")
    wall_clock = time.time() - t0

    nbformat.write(sub_nb, OUT_NB)

    with open("notebook_wall_clock_seconds.txt", "w") as f:
        f.write(f"{wall_clock:.2f}\n")

    print(f"\nExecuted notebook wall clock: {wall_clock:.2f} s")


if __name__ == "__main__":
    main()
