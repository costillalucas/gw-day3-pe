"""
Compare the notebook's captured numbers against the CLI's, judging the
stochastic quantities (posterior medians, evidence) to the tolerance
the sampler's own Monte-Carlo error implies, and the deterministic
quantities (mchirp_guess, par_dic_0) to floating-point equality.

Usage: conda run -n pe python compare.py
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

with open(HERE / 'notebook_baseline' / 'notebook_numbers.json') as f:
    nb = json.load(f)

with open(HERE / 'cli_run' / 'cli_results.json') as f:
    cli = json.load(f)

Z = 3.0  # match threshold, in combined standard errors

lines = []


def emit(s=''):
    lines.append(s)
    print(s)


emit('# Point 2: notebook vs CLI numerical comparison\n')

# --- Deterministic quantities: mchirp_guess ---
emit('## mchirp_guess (deterministic: same seed, same zero-crossing fit)\n')
d = abs(nb['mchirp_guess'] - cli['mchirp_guess'])
emit(f"notebook: {nb['mchirp_guess']!r}")
emit(f"CLI:      {cli['mchirp_guess']!r}")
emit(f"abs diff: {d:.3e}  -> {'MATCH (exact/float-precision)' if d < 1e-9 else 'MISMATCH'}\n")

# --- Deterministic quantities: par_dic_0 ---
emit('## par_dic_0 (deterministic reference waveform)\n')
emit(f"{'param':<14}{'notebook':>18}{'CLI':>18}{'abs diff':>14}  verdict")
all_par_match = True
for k in nb['par_dic_0']:
    v_nb = nb['par_dic_0'][k]
    v_cli = cli['par_dic_0'][k]
    diff = abs(v_nb - v_cli)
    ok = diff < 1e-6 * max(1.0, abs(v_nb))
    all_par_match &= ok
    emit(f"{k:<14}{v_nb:>18.6g}{v_cli:>18.6g}{diff:>14.3e}  {'MATCH' if ok else 'MISMATCH'}")
emit(f"\n=> par_dic_0 overall: {'MATCH' if all_par_match else 'MISMATCH'}\n")

# --- Stochastic quantities: posterior medians ---
emit('## posterior medians (stochastic: independent Nautilus runs)\n')
emit(f"{'param':<14}{'nb median':>14}{'nb SE':>10}{'cli median':>14}{'cli SE':>10}"
     f"{'|diff|':>12}{'z':>8}  verdict")
n_match = 0
n_total = 0
for p in nb['plot_params']:
    m_nb, se_nb = nb['medians'][p], nb['medians_standard_error'][p]
    m_cli, se_cli = cli['medians'][p], cli['medians_standard_error'][p]
    diff = abs(m_nb - m_cli)
    combined_se = math.sqrt(se_nb ** 2 + se_cli ** 2)
    z = diff / combined_se if combined_se > 0 else float('inf')
    ok = z <= Z
    n_total += 1
    n_match += int(ok)
    emit(f"{p:<14}{m_nb:>14.6g}{se_nb:>10.2g}{m_cli:>14.6g}{se_cli:>10.2g}"
         f"{diff:>12.3g}{z:>8.2f}  {'MATCH' if ok else 'MISMATCH'}")
emit(f"\n=> medians within {Z} sigma: {n_match}/{n_total}\n")

# --- Stochastic quantities: evidence ---
emit('## log evidence (stochastic: independent nested-sampling runs)\n')
lnZ_nb, se_nb = nb['evidence']['lnZ'], nb['evidence']['lnZ_standard_error']
lnZ_cli, se_cli = cli['evidence']['lnZ'], cli['evidence']['lnZ_standard_error']
diff = abs(lnZ_nb - lnZ_cli)
combined_se = math.sqrt(se_nb ** 2 + se_cli ** 2)
z = diff / combined_se
emit(f"notebook: lnZ = {lnZ_nb:.4f} +/- {se_nb:.4f}  (n_eff={nb['evidence']['n_eff_nautilus']:.0f})")
emit(f"CLI:      lnZ = {lnZ_cli:.4f} +/- {se_cli:.4f}  (n_eff={cli['evidence']['n_eff_nautilus']:.0f})")
emit(f"|diff| = {diff:.4f}, combined SE = {combined_se:.4f}, z = {z:.2f}"
     f"  -> {'MATCH' if z <= Z else 'MISMATCH'} (threshold z <= {Z})\n")

with open(HERE / 'comparison.md', 'w') as f:
    f.write('\n'.join(lines) + '\n')
