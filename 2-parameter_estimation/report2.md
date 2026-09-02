# Point 2 — module, CLI, and comparison

Aligned-spin path only (`IntrinsicAlignedSpinIASPrior` + `IMRPhenomXAS`),
as required. The precessing "Extra" section was not run.

## Environment note (a real bug, not the one being watched for)

The notebook's `get_event_data` does

```python
asd_funcs = list(cogwheel.data.ASDS)
```

assuming `ASDS` has exactly one entry per detector. The conda-forge
`cogwheel-pe 1.6.0` installed here ships per-detector O3/O4 variants
(`asd_H_O3`, `asd_H_O4`, `asd_L_O3`, `asd_L_O4`, `asd_V_O3` — 5 keys, no
`asd_V_O4`), so `EventData.gaussian_noise` raised

```
ValueError: Lengths of `detector_names` and `asd_funcs` should match.
```

Fixed (per `cogwheel.data`'s own docstring/source, nothing looked up
externally) by pinning one ASD per detector, in `detector_names` order:
`['asd_H_O3', 'asd_L_O3', 'asd_V_O3']` — O3 is the only observing run
with an ASD for all three detectors. Both the notebook run and `pe.py`
use this same fix, so it does not bias the notebook-vs-CLI comparison;
it does mean the injected noise realization (and hence the numbers
below) differs from whatever the exercise's original author saw. See
`runs/notebook_baseline/build_and_run_notebook.py` and `pe.py::get_event_data`.

This was checked to not be the `minimize_scalar` bug the task warned
about: the reference-waveform fit SNR estimate (`sqrt(2 * lnlike(par_dic_0))`)
came out at **18.7**, nowhere near the ~3 the bug produces. It also isn't
exactly the "~24.8" the task doc quotes, which is expected given the ASD
substitution above changes the noise realization.

## What was compared

Per `point2-goal.md`: `mchirp_guess`, `posterior.likelihood.par_dic_0`,
the medians of `plot_params`, and `sampler.load_evidence()`. Two
independent end-to-end runs were done — the notebook (cells extracted
verbatim into `runs/notebook_baseline/build_and_run_notebook.py`,
excluding the precessing cells) and the CLI (`python pe.py`) — both
with `seed=0`, `n_live=1000`, `n_eff=2000`.

`mchirp_guess` and `par_dic_0` are **deterministic** given the seed (no
randomness downstream of the injection and the zero-crossing fit), so
they're compared to floating-point equality. The posterior medians and
the evidence come out of an independent Nautilus nested-sampling run
each time, so they're **stochastic**; those are compared to the
tolerance the sampler's own Monte-Carlo error implies, not by eye:

- Each parameter's weighted-median standard error is estimated as
  `SE(median) ≈ 1.2533 · std / sqrt(n_eff)` (the usual large-sample
  normal approximation), using nautilus's own effective sample size.
- The evidence's standard error is estimated as `SE(lnZ) ≈ 1/sqrt(n_eff)`
  (`Nautilus.load_evidence()` returns only `{'log_ev': ...}`, no
  uncertainty, so this is derived from `nautilus.Sampler.n_eff` per the
  standard self-normalized-importance-sampling approximation).
- Two independent estimates agree "within tolerance" if
  `|diff| ≤ 3 · sqrt(SE_notebook² + SE_cli²)`.

See `pe.py::median_standard_errors` / `evidence_standard_error` and
`runs/compare.py`.

## Results

### `mchirp_guess`

| | value |
|---|---|
| notebook | 21.23844134253563 |
| CLI | 21.23844134253563 |
| verdict | **MATCH** (exact) |

### `par_dic_0` (reference waveform)

All 18 entries matched exactly between notebook and CLI:

| param | value |
|---|---|
| d_luminosity | 758.2524954654299 |
| dec | -0.37951463616181685 |
| f_ref | 100.0 |
| iota | 2.141592653589793 |
| l1, l2 | 0.0, 0.0 |
| m1 | 161.1374687779071 |
| m2 | 11.027163055520557 |
| phi_ref | -1.03093296596305 |
| psi | 0.0 |
| ra | 2.1204851620291834 |
| s1x_n, s1y_n, s2x_n, s2y_n | 0.0 |
| s1z | 0.989398162125946 |
| s2z | 0.989398162125946 |
| t_geocenter | 1.542723663874643 |

**verdict: MATCH (exact)**

### Posterior medians (`plot_params`)

| param | notebook median | notebook SE | CLI median | CLI SE | \|diff\| | z (σ) | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| m1 | 157.265 | 0.054 | 157.357 | 0.055 | 0.0925 | 1.20 | MATCH |
| m2 | 10.0116 | 0.0070 | 10.0115 | 0.0069 | 9.2e-05 | 0.01 | MATCH |
| s1z | 0.988392 | 0.0001 | 0.98842 | 0.0001 | 2.8e-05 | 0.20 | MATCH |
| s2z | 0.054290 | 0.0077 | 0.059349 | 0.0076 | 0.00506 | 0.47 | MATCH |
| d_luminosity | 1004.03 | 2.57 | 1007.04 | 2.57 | 3.01 | 0.84 | MATCH |
| ra | 2.13661 | 0.00066 | 2.13559 | 0.00065 | 0.00102 | 1.11 | MATCH |
| dec | -0.396802 | 0.00087 | -0.396246 | 0.00086 | 0.00056 | 0.45 | MATCH |
| phi_ref | 3.16547 | 0.0250 | 3.13608 | 0.0248 | 0.0294 | 0.83 | MATCH |
| psi | 1.57199 | 0.0125 | 1.56564 | 0.0123 | 0.00635 | 0.36 | MATCH |
| iota | 2.55982 | 0.0038 | 2.56177 | 0.0038 | 0.00195 | 0.36 | MATCH |
| t_geocenter | 1.544237 | 2.6e-05 | 1.544290 | 2.6e-05 | 5.7e-05 | 1.56 | MATCH |
| lnl | 202.884 | 0.032 | 202.923 | 0.031 | 0.0387 | 0.88 | MATCH |

**verdict: 12/12 within 3σ (max z = 1.56, on `t_geocenter`) — MATCH**

### Log evidence

| | lnZ | SE | n_eff (nautilus) |
|---|---:|---:|---:|
| notebook | 156.3139 | 0.0110 | 8271 |
| CLI | 156.3293 | 0.0109 | 8374 |

`|diff| = 0.0154`, combined SE = 0.0155, **z = 1.00 → MATCH** (threshold z ≤ 3).

## Wall clock

| stage | wall clock |
|---|---:|
| Notebook run (aligned-spin cells, Nautilus n_live=1000/n_eff=2000) | 730.4 s (12.2 min) |
| CLI run — sampling only | 615.8 s (10.3 min) |
| CLI run — total (`python pe.py`, event sim through summary stats) | 646.1 s (10.8 min) |
| **Sum of the two independent sampler runs** | **1376.5 s (22.9 min)** |
| **Total wall clock for the whole of point 2** (reading the notebook, diagnosing and fixing the ASD-count mismatch, writing `pe.py`, running both, comparing, writing this report) | **≈ 33 min** (17:26–17:59 UTC, 2026-09-02) |

Machine: 2 vCPUs (`nproc` = 2), no GPU. Both sampler runs used all 2 cores.

## Files

- `pe.py` — the module + CLI (`python pe.py [--seed] [--n-live] [--n-eff] [--out results.json]`).
- `runs/notebook_baseline/` — the notebook's aligned-spin cells extracted
  into a sub-notebook and executed (`build_and_run_notebook.py`,
  `aligned_spin_executed.ipynb`), plus `notebook_numbers.json` (the
  captured numbers) and `finalize_notebook_numbers.py` (adds the
  standard-error fields using `pe.py`'s own helpers).
- `runs/cli_run/` — `cli_run.log` and `cli_results.json` from `python pe.py --out cli_results.json`.
- `runs/compare.py` / `runs/comparison.md` — the comparison above, generated programmatically.
- `runs/notebook_baseline/pe_runs/`, `runs/cli_run/pe_runs/` (gitignored,
  kept locally) — the two Nautilus rundirs (checkpoints, feather samples).
