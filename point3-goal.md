# Point 3 — `pe.html`

**Environment, concretely (same gotchas as point 2):** `conda activate pe`
does not work in this shell — use `conda run -n pe python ...` for
everything. `conda run -n pe python --version` must print below 3.13.

**Time budget: about 45 minutes, hard.** You are being launched with less
than an hour left in the session. Ship something that works over
priority-ordering everything the spec could support. If you are running
short, stop adding events and write what is left undone rather than leaving
`pe.html` half-built.

## What "done" means

`pe.html`, self-contained, opens from a `file://` URL with **no network and
no server** — no CDN script, no external stylesheet, no remote font, no
fetch. It is a viewer over events already run through `pe.py` (point 2's
module), not something that runs `cogwheel` itself: a browser cannot run
`cogwheel`, and the objective's own file-URL constraint only closes one way
— precompute, then view. Check the no-network constraint by actually
opening it that way, don't assume it.

Pick an event from a dropdown (or equivalent) and see, embedded (data URI,
nothing loaded off disk at view time):

- its corner plot,
- the parameter medians (with uncertainty, same convention as
  `point2/report2.md`),
- the log evidence,
- which prior/approximant it ran under, and the wall clock it cost.

## Where to start — do not re-run what already exists

`point2/runs/cli_run/cli_results.json` (`seed=0`, produced by `python pe.py`)
is a complete finished run sitting on disk already. Use it as event 1
without re-invoking the sampler. If time allows after `pe.html` works end to
end for that one event, run `python pe.py --seed 1 --out
runs/cli_run/cli_results_seed1.json` for a second simulated event and add it
to the picker. Do not attempt more than two unless you finish everything
else with time to spare.

Real catalogue events (`cogwheel.data.download_timeseries`, notebook's last
cell, e.g. GW190412) are out of scope for today — needs network access at
run time, which is a separate, longer effort. Note it as future work in the
page rather than attempting it.

## The precessing option, closed out

`objective.txt` asked for this and point 2 deliberately deferred it here:
add a `--precessing` flag to `pe.py` (`IntrinsicIASPrior` +
`IMRPhenomXODE`), **off by default**. You do not have to run it — the
constraint is that it exists and that `pe.html` states its cost next to the
switch. If you have real numbers (e.g. from a quick, deliberately short
test run), use those; if not, say clearly that the cost shown is an
estimate reasoned from the aligned-spin run's own cost (more free
parameters, same sampler) rather than measured, and say why you did not
measure it (time budget).

## Constraints (carried over from the top-level objective and point 2)

- ALIGNED SPIN is what actually ran; precessing is offered, not executed.
- Work only inside this directory; do not modify any environment other
  than `pe`.
- No published solution, no looking anything up beyond `cogwheel`'s own
  source and docs.

## What to hand back

- `pe.html`, committed, verified to open from `file://` with network
  disabled (say how you checked);
- `pe.py` with the `--precessing` flag added;
- a short `report3.md`: which events are in the picker, the precessing
  cost statement and its basis, what you skipped under the time budget,
  and the wall clock for the whole of point 3.
