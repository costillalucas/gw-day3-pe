"""
Build the self-contained pe.html viewer (point 3) from already-computed
pe.py run outputs. Does NOT invoke cogwheel's sampler or re-run anything
stochastic -- it only reads cli_results*.json (produced earlier by
`python pe.py [--seed N] --out ...`) and the matching samples.feather to
render a corner plot, then inlines everything (base64 PNG, no external
CSS/JS/fonts, no fetch) into one HTML file.
"""
import base64
import io
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

import cogwheel.gw_plotting

HERE = Path(__file__).resolve().parent   # .../2-parameter_estimation/runs
ROOT = HERE.parent                       # .../2-parameter_estimation
OUT_HTML = ROOT / 'pe.html'

sys.path.insert(0, str(ROOT))
import pe as pe_module  # noqa: E402

# (label, path to a pe.py --out json). Add more entries here as more
# events are computed -- each just needs a finished cli_results*.json.
EVENT_JSONS = [('GW0 (seed=0)', HERE / 'cli_run' / 'cli_results.json')]
_seed1 = HERE / 'cli_run' / 'cli_results_seed1.json'
if _seed1.exists():
    EVENT_JSONS.append(('GW1 (seed=1)', _seed1))


def make_corner_png_b64(results, json_path):
    # results['rundir'] is relative to wherever `python pe.py` was run
    # from at the time; the pe_runs/ directory has since been moved to
    # sit next to its cli_results*.json (see runs/cli_run/). Resolve
    # using the "pe_runs/..." suffix relative to json_path's directory,
    # rather than trusting the recorded path verbatim.
    recorded = Path(results['rundir'])
    suffix = Path(*recorded.parts[recorded.parts.index('pe_runs') + 1:])
    rundir = json_path.resolve().parent / 'pe_runs' / suffix
    samples = pd.read_feather(rundir / 'samples.feather')
    pe_module.add_derived_quantities(samples)
    cp = cogwheel.gw_plotting.CornerPlot(
        samples, params=results['plot_params'], tail_probability=1e-4)
    cp.plot(title=f"seed={results['seed']}")
    fig = plt.gcf()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=95, bbox_inches='tight')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def build_event(label, json_path):
    with open(json_path) as f:
        results = json.load(f)
    png_b64 = make_corner_png_b64(results, json_path)
    return {
        'label': label,
        'seed': results['seed'],
        'approximant': results.get('approximant', 'IMRPhenomXAS'),
        'prior_class': results.get('prior_class', 'IntrinsicAlignedSpinIASPrior'),
        'precessing': results.get('precessing', False),
        'mchirp_guess': results['mchirp_guess'],
        'ref_wf_snr': results.get('ref_wf_snr'),
        'plot_params': results['plot_params'],
        'medians': results['medians'],
        'medians_se': results['medians_standard_error'],
        'evidence': results['evidence'],
        'n_samples': results['n_samples'],
        'n_effective': results['n_effective'],
        'sampling_wall_clock_seconds': results['sampling_wall_clock_seconds'],
        'total_wall_clock_seconds': results['total_wall_clock_seconds'],
        'corner_png_b64': png_b64,
    }


def main():
    events = [build_event(label, p) for label, p in EVENT_JSONS]
    events_json = json.dumps(events)

    html = HTML_TEMPLATE.replace('__EVENTS_JSON__', events_json)
    OUT_HTML.write_text(html, encoding='utf-8')
    print(f'Wrote {OUT_HTML} ({OUT_HTML.stat().st_size / 1e6:.2f} MB), '
          f'{len(events)} event(s): {[e["label"] for e in events]}')


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>pe.html &mdash; cogwheel PE viewer</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #ffffff; --fg: #1a1a1a; --muted: #666; --card: #f4f4f6;
    --border: #ddd; --accent: #2b5fad;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #1a1a1a; --fg: #eee; --muted: #aaa; --card: #262626; --border: #3a3a3a; --accent: #7ab0ff; }
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--fg); margin: 0; padding: 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.45;
  }
  .wrap { max-width: 980px; margin: 0 auto; }
  h1 { font-size: 1.4rem; margin-bottom: 4px; }
  .subtitle { color: var(--muted); font-size: 0.9rem; margin-bottom: 20px; }
  select {
    font-size: 1rem; padding: 6px 10px; border-radius: 6px;
    border: 1px solid var(--border); background: var(--card); color: var(--fg);
  }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px 20px; margin: 16px 0;
  }
  .card h2 { margin-top: 0; font-size: 1.05rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px 20px; }
  .stat .label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em; }
  .stat .value { font-size: 1.05rem; font-variant-numeric: tabular-nums; }
  table { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
  th, td { text-align: left; padding: 4px 10px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 600; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  img.corner { max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 6px; }
  .note { font-size: 0.88rem; color: var(--muted); }
  .badge {
    display: inline-block; font-size: 0.75rem; padding: 2px 8px; border-radius: 999px;
    background: var(--accent); color: white; margin-left: 6px; vertical-align: middle;
  }
  .badge.off { background: var(--muted); }
  code { background: var(--card); padding: 1px 5px; border-radius: 4px; font-size: 0.9em; }
  footer { color: var(--muted); font-size: 0.8rem; margin-top: 28px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>cogwheel parameter-estimation viewer</h1>
  <div class="subtitle">
    Static viewer over events already run through <code>pe.py</code> (point 2's aligned-spin module).
    Everything on this page &mdash; corner plot included &mdash; is embedded at build time; nothing is
    loaded off disk or over the network when you open this file.
  </div>

  <label for="eventSelect"><strong>Event:</strong></label>
  <select id="eventSelect"></select>

  <div class="card">
    <h2>Run metadata</h2>
    <div class="grid" id="metaGrid"></div>
    <p class="note" id="eventNote"></p>
  </div>

  <div class="card">
    <h2>Corner plot</h2>
    <img class="corner" id="cornerImg" alt="corner plot">
  </div>

  <div class="card">
    <h2>Posterior medians</h2>
    <table>
      <thead><tr><th>parameter</th><th class="num">median</th><th class="num">&plusmn; standard error</th></tr></thead>
      <tbody id="mediansBody"></tbody>
    </table>
    <p class="note">
      Standard error of each weighted median from the Nautilus run's own effective sample size
      (SE(median) &asymp; 1.2533&middot;std/&radic;n_eff), same convention as <code>point2/report2.md</code>
      &mdash; not eyeballed.
    </p>
  </div>

  <div class="card">
    <h2>Log evidence</h2>
    <div class="grid" id="evidenceGrid"></div>
  </div>

  <div class="card">
    <h2>Precessing option <span class="badge off">off by default &middot; not run</span></h2>
    <p><code>pe.py --precessing</code> switches to <code>IntrinsicIASPrior</code> +
       <code>IMRPhenomXODE</code> (generic spins, higher harmonics) in place of the aligned-spin
       default. It exists and is wired through the same pipeline, but has not been executed for
       any event on this page &mdash; every number above is aligned-spin
       (<code>IntrinsicAlignedSpinIASPrior</code> + <code>IMRPhenomXAS</code>).</p>
    <p><strong>Cost: reasoned estimate, not measured</strong> (time budget for point 3 did not
       allow a timed run). Basis, from <code>cogwheel.gw_prior.combined</code>'s own source:
       the aligned-spin prior (<code>IntrinsicAlignedSpinIASPrior</code>) samples over detector-frame
       masses + one aligned effective-spin combination (a handful of dimensions, marginalizing
       extrinsic parameters analytically). The precessing prior
       (<code>IntrinsicIASPrior</code>) adds a whole
       <code>UniformDiskInplaneSpinsIsotropicInclinationPrior</code> block on top of that same
       mass/effective-spin prior &mdash; in-plane spin components for both bodies plus inclination
       &mdash; roughly doubling the sampled dimensionality. On top of that,
       <code>IMRPhenomXODE</code> itself is markedly more expensive per likelihood call than
       <code>IMRPhenomXAS</code> (it combines multiple harmonic modes and precession dynamics
       instead of one aligned-spin quadrupole mode). Nested/importance sampling cost grows with
       both the dimensionality and the per-call cost, so a rough order-of-magnitude expectation is
       several times the aligned-spin wall clock shown above for the same n_live/n_eff &mdash;
       plausibly 30&ndash;60+ minutes rather than ~11 on this 2-core machine, but that multiplier
       is not measured and could be off in either direction.</p>
  </div>

  <div class="card">
    <h2>Known gaps / future work</h2>
    <ul>
      <li><strong>Real catalogue events</strong> (e.g. GW190412 via
        <code>cogwheel.data.download_timeseries</code>) are out of scope for this page: it needs
        network access at run time to fetch strain data, which conflicts with this page's own
        file:// / no-network constraint at the point of <em>running</em> the analysis (viewing a
        precomputed result would be fine, but none has been computed yet). Deferred, not
        attempted.</li>
      <li><strong>Precessing run</strong> above: flag exists, not executed, cost is a reasoned
        estimate (see above).</li>
      <li id="skippedEventNote"></li>
    </ul>
  </div>

  <footer>
    Generated by <code>runs/build_pe_html.py</code> from <code>pe.py</code> run outputs. See
    <code>report3.md</code> for how this file's no-network/file:// behavior was verified.
  </footer>
</div>

<script>
const EVENTS = __EVENTS_JSON__;

function fmt(x, digits) {
  if (x === null || x === undefined) return '&mdash;';
  if (typeof x === 'number' && Number.isNaN(x)) return 'NaN (see note)';
  if (typeof x !== 'number') return String(x);
  return x.toLocaleString(undefined, {maximumFractionDigits: digits ?? 4, minimumFractionDigits: 0});
}

function render(ev) {
  document.getElementById('cornerImg').src = 'data:image/png;base64,' + ev.corner_png_b64;

  const lowSnr = !(ev.ref_wf_snr >= 10); // true for NaN too
  const snrLabel = 'Reference-wf SNR' + (lowSnr ? ' &#9888;' : '');
  const meta = [
    ['Approximant', ev.approximant],
    ['Prior class', ev.prior_class],
    ['Precessing?', ev.precessing ? 'yes' : 'no (aligned spin)'],
    ['mchirp_guess', fmt(ev.mchirp_guess, 3)],
    [snrLabel, fmt(ev.ref_wf_snr, 2)],
    ['n_samples', fmt(ev.n_samples, 0)],
    ['n_effective', fmt(ev.n_effective, 1)],
    ['Sampling wall clock', fmt(ev.sampling_wall_clock_seconds, 1) + ' s'],
    ['Total wall clock', fmt(ev.total_wall_clock_seconds, 1) + ' s'],
  ];
  document.getElementById('metaGrid').innerHTML = meta.map(([label, value]) =>
    `<div class="stat"><div class="label">${label}</div><div class="value">${value}</div></div>`
  ).join('');

  const noteEl = document.getElementById('eventNote');
  noteEl.innerHTML = lowSnr
    ? '&#9888; This event\'s reference-waveform fit did not find a confident match ' +
      '(SNR estimate ' + fmt(ev.ref_wf_snr, 2) + ', expected ~20&ndash;25 for a loud ' +
      'injection). This means the injection landed quiet/far/marginal by chance of the ' +
      'random seed &mdash; a real outcome, not hidden or discarded. The posterior below ' +
      '(wide, weakly-informative) and the near-zero/negative log evidence are consistent ' +
      'with that: a genuine non-detection-like case, not a pipeline bug. See report3.md.'
    : '';

  document.getElementById('mediansBody').innerHTML = ev.plot_params.map(p =>
    `<tr><td>${p}</td><td class="num">${fmt(ev.medians[p], 4)}</td><td class="num">${fmt(ev.medians_se[p], 3)}</td></tr>`
  ).join('');

  const e = ev.evidence;
  const evGrid = [
    ['ln Z', fmt(e.lnZ, 4)],
    ['&plusmn; standard error', fmt(e.lnZ_standard_error, 4)],
    ['n_eff (nautilus)', fmt(e.n_eff_nautilus, 1)],
  ];
  document.getElementById('evidenceGrid').innerHTML = evGrid.map(([label, value]) =>
    `<div class="stat"><div class="label">${label}</div><div class="value">${value}</div></div>`
  ).join('');
}

const select = document.getElementById('eventSelect');
EVENTS.forEach((ev, i) => {
  const opt = document.createElement('option');
  opt.value = i;
  opt.textContent = ev.label;
  select.appendChild(opt);
});
select.addEventListener('change', () => render(EVENTS[select.value]));
render(EVENTS[0]);

document.getElementById('skippedEventNote').textContent = EVENTS.length < 2
  ? 'A second simulated event (seed=1) was attempted but did not finish inside the point-3 time budget; only seed=0 is in the picker.'
  : 'Two simulated events (seed=0, seed=1) are in the picker (seed=1 turned out low-SNR/marginal -- see its note above when selected); a third was not attempted (time budget).';
</script>
</body>
</html>
"""

if __name__ == '__main__':
    main()
