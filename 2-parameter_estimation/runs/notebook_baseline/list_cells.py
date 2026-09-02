from pathlib import Path

import nbformat

nb_path = Path(__file__).resolve().parent.parent.parent / "parameter_estimation.ipynb"
nb = nbformat.read(nb_path, as_version=4)
for i, cell in enumerate(nb.cells):
    src = cell.source.strip().replace("\n", " | ")
    print(f"[{i:02d}] ({cell.cell_type}) {src[:110]}")
