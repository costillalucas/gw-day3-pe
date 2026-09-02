#!/usr/bin/env bash
# Arranque del ejercicio de PE en una maquina Linux (Codespaces).
#
# NUNCA SE EJECUTO. Se escribio en Windows, donde no hay forma de correrlo:
# esa es la razon de existir del script. Todo lo que afirma sobre conda-forge
# esta verificado contra la API del registro (cogwheel-pe 1.6.0 es noarch y
# lista sus dependencias), pero la resolucion real en linux-64 no se probo.
# Si algo falla, el log que deja ES el entregable: pegalo en report.html.
#
#   bash codespace-setup.sh
#
# Deja todo en setup.log y termina diciendo el reloj.

set -o pipefail
START=$(date +%s)
LOG="setup.log"
exec > >(tee "$LOG") 2>&1

echo "=== arranque: $(date -u +%FT%TZ) ==="
echo "maquina: $(uname -srm)"
echo "nucleos: $(nproc)   RAM: $(free -g 2>/dev/null | awk '/^Mem:/{print $2" GB"}')"
echo

# ---------------------------------------------------------------- 1. conda
# La imagen universal de Codespaces suele traer conda. Si no, miniforge.
if command -v mamba >/dev/null 2>&1; then
    CONDA=mamba
elif command -v conda >/dev/null 2>&1; then
    CONDA=conda
else
    echo "--- no hay conda: instalando miniforge ---"
    curl -fsSL -o /tmp/miniforge.sh \
        "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
    bash /tmp/miniforge.sh -b -p "$HOME/miniforge3"
    # shellcheck source=/dev/null
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
    CONDA=mamba
    command -v mamba >/dev/null 2>&1 || CONDA=conda
fi
echo "gestor: $CONDA ($($CONDA --version 2>&1 | head -1))"
echo

# ------------------------------------------------------------------ 2. env
# La consigna: construi tu propio entorno, no modifiques uno existente.
ENV_NAME=pe
echo "--- creando el entorno '$ENV_NAME' ---"
$CONDA create -y -n "$ENV_NAME" -c conda-forge "python>=3.10"

# El README del dia 3 avisa de dos trampas que cuestan una hora cada una:
#
#   1. cogwheel-pe va desde CONDA-FORGE, no desde un checkout viejo. Un
#      checkout de tres anios tiene un bug en minimize_scalar que devuelve en
#      silencio una forma de onda de referencia basura para GW150914 -- SNR 3.2
#      donde deberia dar 24.8 -- y la etapa incoherente igual imprime un
#      log-likelihood plausible, asi que parece que funciono.
#
#   2. PyMultiNest es una libreria Fortran detras de un wrapper Python, y el
#      wrapper importa bien sin ella. Usar dynesty o nautilus.
#
# cogwheel-pe 1.6.0 ya depende de nautilus-sampler, dynesty, pyarrow, notebook,
# ipympl e ipywidgets, asi que no hace falta el requirements.txt del ejercicio.
echo "--- instalando cogwheel-pe desde conda-forge ---"
$CONDA install -y -n "$ENV_NAME" -c conda-forge cogwheel-pe

RUN="$CONDA run -n $ENV_NAME"

# ---------------------------------------------------------------- 3. clon
if [ ! -d pitp-pe-exercises ]; then
    echo "--- clonando el ejercicio ---"
    git clone https://github.com/jroulet/pitp-pe-exercises.git
fi
echo "commit del ejercicio: $(git -C pitp-pe-exercises rev-parse --short HEAD)"
echo

# -------------------------------------------------- 4. verificar de verdad
# No alcanza con que el install no haya fallado. Lo que hay que comprobar es
# que existan las cosas que la consigna nombra, y que lal cargue de verdad.
echo "--- verificacion ---"
$RUN python - <<'PY'
import importlib, sys
print("python     :", sys.version.split()[0])
for mod in ("lal", "lalsimulation", "cogwheel", "nautilus", "dynesty", "pyarrow"):
    try:
        m = importlib.import_module(mod)
        print(f"{mod:<12}: {getattr(m, '__version__', 'ok')}")
    except Exception as e:
        print(f"{mod:<12}: FALLA -- {type(e).__name__}: {e}")

# las dos cosas que la consigna fija como restriccion
import cogwheel.gw_prior, cogwheel.waveform
prior = "IntrinsicAlignedSpinIASPrior"
print(f"\nprior {prior}:",
      "presente" if hasattr(cogwheel.gw_prior, prior) else "AUSENTE")
aps = getattr(cogwheel.waveform, "APPROXIMANTS", {})
for a in ("IMRPhenomXAS", "IMRPhenomXODE"):
    print(f"approximant {a}:", "presente" if a in aps else "AUSENTE")

# el control del bug del checkout viejo: una forma de onda de referencia sana
# tiene que dar SNR ~24.8 para GW150914, no ~3.2. Aca solo se deja anotado
# que hay que mirarlo cuando corras la celda 23 del notebook.
print("\nrecordatorio: si el ajuste de referencia da SNR ~3, es el bug del")
print("checkout viejo, no un problema de los datos.")
PY

echo
echo "=== fin: $(date -u +%FT%TZ) ==="
echo "reloj: $(( $(date +%s) - START )) s"
echo
echo "siguiente:  $CONDA activate $ENV_NAME"
echo "            jupyter notebook pitp-pe-exercises/2-parameter_estimation/"
