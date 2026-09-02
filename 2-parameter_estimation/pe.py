"""
pe.py -- aligned-spin parameter-estimation pipeline, extracted from
``parameter_estimation.ipynb``'s notebook cells into reusable functions,
plus a command-line entry point (`python pe.py`) that runs the same
analysis end to end and prints the numbers the notebook produces.

ALIGNED SPIN ONLY: this module implements the ``IntrinsicAlignedSpinIASPrior``
+ ``IMRPhenomXAS`` path only. The notebook's precessing "Extra" section
(``IMRPhenomXODE`` + ``IntrinsicIASPrior``) is intentionally not
reproduced here -- it is a much larger calculation left for tomorrow's
``pe.html``.

Every default below (seed, t_merger_guess, the zero-crossing picks,
n_live/n_eff, plot_params) is copied verbatim from the notebook's own
"Example solution" cells, so that running this module reproduces the
same deterministic inputs the notebook used. The one part that is *not*
reproducible bit-for-bit is the Nautilus nested-sampling run itself: it
is stochastic, so the CLI's posterior medians and evidence are expected
to agree with the notebook's only up to the sampler's own Monte-Carlo
error -- see `median_standard_errors` and `compare_evidence` below.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import cogwheel.cosmology
import cogwheel.data
import cogwheel.gw_prior
import cogwheel.gw_utils
import cogwheel.posterior
import cogwheel.sampling

# --- Defaults, copied from the notebook's "Example solution" cells ---
DEFAULT_SEED = 0
DEFAULT_T_MERGER_GUESS = 1.6
DEFAULT_I_DET = 0
DEFAULT_ASCENDING_ZERO_CROSSINGS = (
    1.513, 1.53, 1.545, 1.555, 1.565, 1.573, 1.581, 1.588, 1.594,
)
DEFAULT_APPROXIMANT = 'IMRPhenomXAS'
DEFAULT_PRIOR_CLASS = 'IntrinsicAlignedSpinIASPrior'
DEFAULT_F_REF = 100.0
DEFAULT_N_LIVE = 1000
DEFAULT_N_EFF = 2000
DEFAULT_RUNDIR_PARENT = 'pe_runs'

PLOT_PARAMS = [
    'm1',
    'm2',
    's1z',
    's2z',
    'd_luminosity',
    'ra',
    'dec',
    'phi_ref',
    'psi',
    'iota',
    't_geocenter',
    'lnl',
]


# --------------------------------------------------------------------------
# Event simulation (notebook cell: `_generate_injection_dic` / `get_event_data`)
# --------------------------------------------------------------------------

def generate_injection_dic(seed):
    """Draw one random injection (secret truth) from the auxiliary prior."""
    aux_prior = cogwheel.gw_prior.IASPrior(
        f_ref=100.0,
        mchirp_range=(10, 50),
        detector_pair='HL',
        tgps=0,
        ref_det_name='H',
        f_avg=100.0,
        d_hat_max=100.0,
        dt0=10,
    )
    return dict(
        aux_prior.generate_random_samples(1, seed=seed).loc[0, aux_prior.standard_params])


def get_event_data(seed=DEFAULT_SEED):
    """Return an ``EventData`` with a secret injection in Gaussian noise."""
    injection_dic = generate_injection_dic(seed)
    # NOTE: the notebook does `asd_funcs = list(cogwheel.data.ASDS)`, which
    # assumed ASDS has exactly one entry per detector. The installed
    # conda-forge cogwheel (1.6.0) ships per-detector O3/O4 variants, so
    # ASDS has 5 keys and `len(detector_names) != len(asd_funcs)` raises.
    # We pin one ASD per detector, in `detector_names` ('HLV') order,
    # using O3 -- the only observing run with an ASD for all of H, L, V.
    asd_funcs = ['asd_H_O3', 'asd_L_O3', 'asd_V_O3']
    eventname = f'GW{seed}'
    event_data = cogwheel.data.EventData.gaussian_noise(
        eventname, duration=128.0, detector_names='HLV', fmax=512.0,
        asd_funcs=asd_funcs, tgps=0.0, seed=seed)
    event_data.inject_signal(par_dic=injection_dic, approximant='IMRPhenomXODE')
    return event_data


# --------------------------------------------------------------------------
# Chirp-mass guess from the whitened-strain f^(-8/3) fit
# --------------------------------------------------------------------------

def estimate_mchirp_guess(event_data, i_det=DEFAULT_I_DET,
                           ascending_zero_crossings=DEFAULT_ASCENDING_ZERO_CROSSINGS):
    """
    Chirp-mass estimate off the whitened-strain f^(-8/3) fit, using the
    same by-eye zero-crossing picks as the notebook's example solution.
    """
    import lal  # local import: only needed for MTSUN_SI

    # Touch get_whitened_td for parity with the notebook (also exercises
    # the same code path the by-eye zero-crossing picks were made from).
    event_data.get_whitened_td()

    periods = np.diff(ascending_zero_crossings)
    times = np.add(ascending_zero_crossings[:-1], ascending_zero_crossings[1:]) / 2
    frequencies = 1 / periods

    y = frequencies ** (-8 / 3)
    x = times
    slope, _const = np.polyfit(x, y, deg=1)

    # slope == (8*np.pi)**(8/3) / 5 * (lal.MTSUN_SI * mchirp)**(5/3)
    mchirp_guess = (-slope / (8 * np.pi) ** (8 / 3) * 5) ** (3 / 5) / lal.MTSUN_SI
    return float(mchirp_guess)


# --------------------------------------------------------------------------
# Reference-waveform fit (likelihood maximization)
# --------------------------------------------------------------------------

def find_reference_waveform(event_data, mchirp_guess, t_merger_guess=DEFAULT_T_MERGER_GUESS,
                             approximant=DEFAULT_APPROXIMANT, prior_class=DEFAULT_PRIOR_CLASS,
                             f_ref=DEFAULT_F_REF):
    """Fast likelihood maximization to find the reference waveform."""
    return cogwheel.posterior.Posterior.from_event(
        event_data,
        mchirp_guess,
        approximant,
        prior_class,
        ref_wf_finder_kwargs={
            'f_ref': f_ref,
            'time_range': (t_merger_guess - 0.1, t_merger_guess + 0.1),
        }
    )


def reference_waveform_snr(posterior):
    """
    sqrt(2 * lnlike(par_dic_0)) as a proxy for the reference-fit SNR.

    Sanity check against the known ``minimize_scalar`` bug in old
    ``cogwheel`` checkouts: a healthy fit gives SNR ~ 24.8; the buggy
    one silently gives SNR ~ 3 while still printing a plausible
    log-likelihood.
    """
    lnl_0 = posterior.likelihood.lnlike(posterior.likelihood.par_dic_0)
    return float(np.sqrt(2 * lnl_0))


# --------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------

def run_sampler(posterior, rundir_parent=DEFAULT_RUNDIR_PARENT,
                 n_live=DEFAULT_N_LIVE, n_eff=DEFAULT_N_EFF):
    """Run Nautilus nested sampling on ``posterior``. Returns (sampler, rundir, elapsed_s)."""
    sampler = cogwheel.sampling.Nautilus(posterior)
    sampler.run_kwargs['n_live'] = n_live
    sampler.run_kwargs['n_eff'] = n_eff

    rundir = sampler.get_rundir(parentdir=rundir_parent)
    t0 = time.time()
    sampler.run(rundir)
    elapsed = time.time() - t0
    return sampler, rundir, elapsed


def load_samples(rundir):
    """Load ``samples.feather`` from ``rundir`` and add derived quantities."""
    samples = pd.read_feather(Path(rundir) / 'samples.feather')
    add_derived_quantities(samples)
    return samples


def add_derived_quantities(samples):
    """
    Add columns inplace to a dataframe of samples.

    Includes redshift, mtot, m1_source, m2_source, mtot_source, chieff, q.
    """
    samples['redshift'] = cogwheel.cosmology.z_of_d_luminosity(samples['d_luminosity'])

    samples['mtot'] = samples['m1'] + samples['m2']

    for mass_key in 'm1', 'm2', 'mtot':
        samples[f'{mass_key}_source'] = samples[mass_key] / (1 + samples['redshift'])

    samples['chieff'] = cogwheel.gw_utils.chieff(**samples[['m1', 'm2', 's1z', 's2z']])

    samples['q'] = samples['m2'] / samples['m1']


# --------------------------------------------------------------------------
# Weighted-sample statistics (nautilus samples carry a 'weights' column)
# --------------------------------------------------------------------------

def _weights_of(samples):
    return samples['weights'].to_numpy() if 'weights' in samples else np.ones(len(samples))


def weighted_median(values, weights):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    cdf = np.cumsum(weights) - 0.5 * weights
    cdf /= np.sum(weights)
    return float(np.interp(0.5, cdf, values))


def weighted_std(values, weights):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    avg = np.average(values, weights=weights)
    var = np.average((values - avg) ** 2, weights=weights)
    return float(np.sqrt(var))


def effective_sample_size(weights):
    weights = np.asarray(weights, dtype=float)
    return float(np.sum(weights) ** 2 / np.sum(weights ** 2))


def evidence_standard_error(sampler):
    """
    Approximate Monte-Carlo standard error of the nested-sampling log
    evidence.

    Nautilus/cogwheel do not report a log-Z uncertainty directly
    (``Nautilus.load_evidence()`` returns only ``{'log_ev': ...}``).
    The evidence is a self-normalized-importance-sampling-style
    estimate, for which the standard approximation is

        SE(lnZ) ~= 1 / sqrt(n_eff)

    (relative error of Z ~ 1/sqrt(n_eff) for large n_eff), using
    nautilus's own effective-sample-size estimate
    (``sampler.sampler.n_eff``, a property of the underlying
    ``nautilus.Sampler``). This is what "the tolerance the sampler's
    own stochastic error implies" means for the evidence comparison.
    """
    n_eff = float(sampler.sampler.n_eff)
    return 1.0 / np.sqrt(n_eff), n_eff


def compute_medians(samples, plot_params=PLOT_PARAMS):
    weights = _weights_of(samples)
    return {p: weighted_median(samples[p], weights) for p in plot_params}


def median_standard_errors(samples, plot_params=PLOT_PARAMS):
    """
    Approximate Monte-Carlo standard error of each weighted median, via
    the large-sample normal approximation

        SE(median) ~= 1.2533 * std / sqrt(n_eff)

    (1.2533 = sqrt(pi/2), the usual factor relating the SE of the sample
    median to the SE of the mean for an approximately normal marginal).
    This is what lets the CLI-vs-notebook comparison be judged "to the
    tolerance the sampler's stochastic error implies" instead of by eye.
    """
    weights = _weights_of(samples)
    n_eff = effective_sample_size(weights)
    return {
        p: float(1.2533 * weighted_std(samples[p], weights) / np.sqrt(n_eff))
        for p in plot_params
    }


# --------------------------------------------------------------------------
# End-to-end pipeline
# --------------------------------------------------------------------------

def run_full_analysis(seed=DEFAULT_SEED, n_live=DEFAULT_N_LIVE, n_eff=DEFAULT_N_EFF,
                       rundir_parent=DEFAULT_RUNDIR_PARENT, plot_params=PLOT_PARAMS,
                       verbose=True):
    """
    Run the full aligned-spin analysis end to end and return a results dict
    with every quantity point2-goal.md asks the CLI to reproduce.
    """
    t_start = time.time()

    def log(msg):
        if verbose:
            print(msg, flush=True)

    log(f'[1/5] Simulating event (seed={seed})...')
    event_data = get_event_data(seed=seed)

    log('[2/5] Estimating mchirp_guess from the whitened-strain f^(-8/3) fit...')
    mchirp_guess = estimate_mchirp_guess(event_data)
    log(f'      mchirp_guess = {mchirp_guess}')

    log('[3/5] Finding reference waveform (likelihood maximization)...')
    posterior = find_reference_waveform(event_data, mchirp_guess)
    ref_wf_snr = reference_waveform_snr(posterior)
    log(f'      reference-waveform fit SNR estimate: {ref_wf_snr:.2f} '
        f'(expect ~24.8; ~3 would mean the minimize_scalar bug is present)')
    if ref_wf_snr < 10:
        raise RuntimeError(
            f'Reference-waveform SNR is {ref_wf_snr:.2f}, suspiciously low -- '
            'looks like the known minimize_scalar bug. Aborting.'
        )
    par_dic_0 = {k: (float(v) if not isinstance(v, str) else v)
                 for k, v in posterior.likelihood.par_dic_0.items()}

    log(f'[4/5] Sampling the posterior (Nautilus, n_live={n_live}, n_eff={n_eff})...')
    sampler, rundir, sampling_elapsed = run_sampler(
        posterior, rundir_parent=rundir_parent, n_live=n_live, n_eff=n_eff)
    log(f'      sampling wall clock: {sampling_elapsed:.1f} s (rundir={rundir})')

    log('[5/5] Loading samples and computing summary statistics...')
    samples = load_samples(rundir)
    medians = compute_medians(samples, plot_params)
    medians_se = median_standard_errors(samples, plot_params)
    evidence = sampler.load_evidence()
    lnZ = float(evidence['log_ev'])
    lnZ_se, n_eff_nautilus = evidence_standard_error(sampler)

    total_elapsed = time.time() - t_start

    results = {
        'seed': seed,
        'mchirp_guess': mchirp_guess,
        'ref_wf_snr': ref_wf_snr,
        'par_dic_0': par_dic_0,
        'plot_params': list(plot_params),
        'medians': medians,
        'medians_standard_error': medians_se,
        'evidence': {'lnZ': lnZ, 'lnZ_standard_error': lnZ_se,
                     'n_eff_nautilus': n_eff_nautilus},
        'n_samples': int(len(samples)),
        'n_effective': effective_sample_size(_weights_of(samples)),
        'rundir': str(rundir),
        'sampling_wall_clock_seconds': sampling_elapsed,
        'total_wall_clock_seconds': total_elapsed,
    }
    return results


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print_results(results):
    print('\n=== Aligned-spin parameter estimation: results ===')
    print(f"mchirp_guess = {results['mchirp_guess']}")
    print(f"reference-waveform fit SNR = {results['ref_wf_snr']:.3f}")
    print('\npar_dic_0 (reference waveform):')
    for k, v in results['par_dic_0'].items():
        print(f'  {k} = {v}')
    print('\nposterior medians (+/- Monte-Carlo standard error of the median):')
    for p in results['plot_params']:
        print(f"  {p} = {results['medians'][p]:.6g} "
              f"+/- {results['medians_standard_error'][p]:.3g}")
    print(f"\nlog evidence: lnZ = {results['evidence']['lnZ']:.4f} "
          f"+/- {results['evidence']['lnZ_standard_error']:.4f} "
          f"(n_eff_nautilus = {results['evidence']['n_eff_nautilus']:.1f})")
    print(f"n_samples = {results['n_samples']}, "
          f"n_effective = {results['n_effective']:.1f}")
    print(f"\nsampling wall clock: {results['sampling_wall_clock_seconds']:.1f} s")
    print(f"total wall clock:    {results['total_wall_clock_seconds']:.1f} s")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Run the aligned-spin (IntrinsicAlignedSpinIASPrior + '
                     'IMRPhenomXAS) cogwheel parameter-estimation analysis '
                     'end to end, reproducing the notebook\'s numbers.')
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED,
                         help='Injection/noise seed (default: %(default)s).')
    parser.add_argument('--n-live', type=int, default=DEFAULT_N_LIVE,
                         help='Nautilus n_live (default: %(default)s).')
    parser.add_argument('--n-eff', type=int, default=DEFAULT_N_EFF,
                         help='Nautilus n_eff (default: %(default)s).')
    parser.add_argument('--rundir-parent', default=DEFAULT_RUNDIR_PARENT,
                         help='Parent directory for the sampler rundir '
                              '(default: %(default)s).')
    parser.add_argument('--out', default=None,
                         help='Optional path to dump the results as JSON.')
    args = parser.parse_args(argv)

    results = run_full_analysis(
        seed=args.seed, n_live=args.n_live, n_eff=args.n_eff,
        rundir_parent=args.rundir_parent)

    _print_results(results)

    if args.out:
        with open(args.out, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f'\nWrote results to {args.out}')

    return results


if __name__ == '__main__':
    main()
