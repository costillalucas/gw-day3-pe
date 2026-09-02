# Point 2 — the module and the command-line entry point

You are in a fresh conda environment (`pe`) with `cogwheel-pe` installed from
conda-forge, and `pitp-pe-exercises` cloned beside this file
(`codespace-setup.sh` did both). Read
`pitp-pe-exercises/2-parameter_estimation/` before you touch anything else.

## What "done" means

The same analysis as the notebook's aligned-spin path, reproduced as:

1. a module (`pe.py` or similar) with the analysis pulled out of the
   notebook's cells into functions;
2. a command-line entry point that runs it end to end and prints the numbers
   below;
3. proof that the CLI's numbers match the notebook's, to the tolerance the
   sampler's own stochastic error implies — not to eyeball agreement.

## Order of operations

Run the notebook itself first, start to finish, ALIGNED SPIN ONLY. Do not
skip this: there is nothing to compare the CLI against until it has run
once. Capture these exact quantities as you go — they are the numbers the
CLI has to reproduce:

- `mchirp_guess` — the chirp-mass estimate off the whitened-strain
  f^(-8/3) fit
- `posterior.likelihood.par_dic_0` — the reference waveform the
  likelihood was maximised into
- the medians of the posterior for every parameter in `plot_params`
- `sampler.load_evidence()`

**Watch this while you run it.** If the reference-waveform fit gives an SNR
around 3 instead of around 24.8, that is the `minimize_scalar` bug from an
old `cogwheel` checkout — conda-forge should not have it, but check anyway,
because it fails silently and still prints a plausible log-likelihood.

## Constraints (carried over from the top-level objective)

- **ALIGNED SPIN ONLY**: `IntrinsicAlignedSpinIASPrior` with `IMRPhenomXAS`.
- Do **not** run the precessing "Extra" (the `IMRPhenomXODE` +
  `IntrinsicIASPrior` cells). It is a much larger calculation and belongs
  to tomorrow's `pe.html`, as an off-by-default option with its cost
  stated next to the switch — not to today's task.
- Work only inside this directory. Do not modify any environment other
  than the one `codespace-setup.sh` built.
- No published solution, no looking anything up beyond `cogwheel`'s own
  source and docs.

## What to hand back

- the module and the CLI, committed;
- a short `report2.md` (or a section appended to `report.html`) stating
  the notebook's numbers, the CLI's numbers, and the comparison — if they
  do not match, that is the report, not a bug to hide;
- the wall clock, stated explicitly, for the whole of this point.

Leave point 3 (`pe.html`) alone. It is tomorrow's task.
