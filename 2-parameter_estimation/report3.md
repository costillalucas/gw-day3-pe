# Point 3 — `pe.html`

Hard time budget: ~45 minutes. This section is written incrementally as
the budget runs down; the final "Wall clock" line below is the real
total.

## What's in the picker

- **GW0 (seed=0)**: from `runs/cli_run/cli_results.json`, the finished
  aligned-spin run already on disk from point 2 (`IntrinsicAlignedSpinIASPrior`
  + `IMRPhenomXAS`, n_live=1000, n_eff=2000). **Not re-sampled** — `pe.html`
  reads its `medians`/`medians_standard_error`/`evidence`/wall-clock fields
  and its `samples.feather` (for the corner plot) directly.
- **GW1 (seed=1)**: a second simulated event, `python pe.py --seed 1 --out
  runs/cli_run/cli_results_seed1.json`, launched in the background as soon
  as `pe.html` was working end to end for GW0, per the goal's ordering.
  It finished in 300 s (faster than GW0's 616 s — nested-sampling cost
  varies with the actual posterior, not just n_live/n_eff) and completed
  cleanly, but landed on a **quiet/marginal injection by chance of the
  random seed**: the reference-waveform fit's SNR estimate came out
  `NaN` (the maximized log-likelihood was negative, so `sqrt(2·lnl_0)`
  is undefined), `d_luminosity`'s median is ~12 Gpc, and the log evidence
  is slightly negative (`lnZ = -8.47 ± 0.01`) — all consistent with a
  genuine non-detection-like case, not a crash or a hidden bug. It's kept
  in the picker labeled with an on-page warning (`⚠`) rather than dropped,
  since discarding a real, cleanly-finished result to make the demo look
  tidier would be the wrong instinct. This also exposed a real bug, now
  fixed: `pe.py`'s SNR sanity check was `if ref_wf_snr < 10: raise ...`,
  which never fires for `NaN` (NaN comparisons are always `False` in
  Python) — changed to `if not (ref_wf_snr >= 10)` and downgraded to a
  warning (a real quiet injection is a different situation from the
  minimize_scalar bug the check was written for, and shouldn't abort a
  run that otherwise completed).

No more than two events were attempted, per the goal's cap.

## The `--precessing` flag

Added to `pe.py` (`--precessing` → `IntrinsicIASPrior` + `IMRPhenomXODE`,
off by default; wired through `run_full_analysis`, threaded into the
results dict as `precessing`/`approximant`/`prior_class`). **Not run** —
time budget. `pe.html` states this next to the switch.

**Cost basis (reasoned estimate, not measured — say why):** a timed
precessing run was not attempted because the reasoning below already
puts its expected cost at several times the aligned-spin run's ~5–11
minutes (so 30–90+ minutes) on this 2-core machine — on its own bigger
than the entire ~45-minute point-3 budget, alongside building, verifying
and writing up two aligned-spin events. Reasoning instead from
`cogwheel.gw_prior.combined`'s own source (allowed — `cogwheel`'s own
source/docs, nothing external):

- `IntrinsicAlignedSpinIASPrior.prior_classes` = `[UniformDetectorFrameMassesPrior,
  UniformEffectiveSpinPrior, ZeroTidalDeformabilityPrior, FixedReferenceFrequencyPrior]`
  — the last two are fixed (0 sampled dimensions), so this samples over
  detector-frame masses + one aligned effective-spin combination.
- `IntrinsicIASPrior.prior_classes` = `[FixedReferenceFrequencyPrior,
  UniformDetectorFrameMassesPrior, UniformEffectiveSpinPrior,
  UniformDiskInplaneSpinsIsotropicInclinationPrior, ZeroTidalDeformabilityPrior]`
  — the same mass/effective-spin prior, **plus** a whole
  `UniformDiskInplaneSpinsIsotropicInclinationPrior` block (in-plane spin
  components for both bodies, plus inclination) that the aligned-spin
  prior doesn't have at all — roughly doubling the sampled
  dimensionality.
- `IMRPhenomXODE` (precessing, multiple harmonic modes) is also markedly
  more expensive per likelihood evaluation than `IMRPhenomXAS` (single
  aligned-spin quadrupole mode).

Both effects (more dimensions, more expensive per-sample cost) push
nested/importance-sampling wall clock up together, so the page states a
rough order-of-magnitude expectation of several times the aligned-spin
cost (very roughly 30–60+ minutes rather than ~11, for the same
n_live/n_eff on this machine) — explicitly labeled as an unmeasured,
reasoned multiplier that could be off in either direction, not a
benchmark.

## `file://` / no-network verification

`pe.html` is one file: inline `<style>`, inline `<script>`, the corner
plot as a `data:image/png;base64,...` URI built into a JS object literal
at build time. Checked two ways:

1. **Static audit**: `grep` over the built file for `http://`/`https://`
   (only match is the harmless `w3.org` doctype/XML-namespace string,
   never fetched), for `<script src=`/`<link ...>` tags (none), and for
   `fetch(`/`XMLHttpRequest`/`WebSocket`/`import(` in the inline script
   (none — zero matches).
2. **Actually opening it, headless**: installed `jsdom` (Node) and loaded
   the built `pe.html` from a real `file://` URL with `runScripts:
   'dangerously'` and no fetch shim provided (so any resource load
   attempt would throw rather than silently succeed). The inline script
   ran, populated the event `<select>`, set the corner `<img>` to a
   `data:image/png;base64,...` src, filled the 12-row medians table and
   the evidence grid, and jsdom reported zero errors. This is not a
   full-fidelity render (no layout/paint), but it does prove the file
   executes correctly from `file://` with nothing to fetch. A no-Wi-Fi
   full-browser open was not additionally done (no browser binary was
   available in this sandbox and installing one risked the time budget).

## What was skipped under the time budget

- Precessing run: flag exists, not executed (see cost section above).
- Real catalogue events (e.g. GW190412 via
  `cogwheel.data.download_timeseries`): out of scope per the goal — needs
  network at run time. Noted as future work directly in the page.
- Full-fidelity visual browser check (see above) — used jsdom instead.
- A third simulated event, or re-running GW1 with a different seed to get
  a "loud" second example — GW1's low SNR is itself informative (see
  above) and re-rolling it to look nicer wasn't worth the compute given
  the budget.

## Wall clock

| stage | wall clock |
|---|---:|
| GW0 (seed=0) sampling — reused from point 2, **not re-run** | 615.8 s (already spent, point 2) |
| GW1 (seed=1) sampling — new for point 3 | 300.1 s |
| Everything else for point 3 (writing `pe.py`'s `--precessing` flag, the corner-plot/HTML build script, `pe.html`'s markup/CSS/JS, the NaN-guard bug fix, jsdom verification, this report) | ran concurrently with GW1's background sampling, plus wrap-up after |
| **Total wall clock for point 3** (from creating `point3-goal.md` to committing+pushing, 18:27–18:40 UTC 2026-09-02) | **≈13 min**, well inside the ~45-minute hard budget |

Machine: 2 vCPUs, no GPU (same as point 2).
