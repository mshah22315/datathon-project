"""Run the full data pipeline from the raw file to the modeling dataset.

    datathon-dataset.xlsx -> clean_data.py -> data_clean.csv
                          -> make_asof.py  -> data_asof_0501.csv (+ late_applicants_0501.csv)

make_asof.py runs with its default cutoff (May 1). Extra arguments are passed to make_asof.py,
e.g. a different cutoff or the dated output.

Each script runs with the project folder as the working directory, so inputs and outputs use
the default paths in the scripts (all in the project folder).

Usage (from anywhere):
    python data_cleaning/run_all.py
    python data_cleaning/run_all.py --cutoff 03-01 --save-dated
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
STEPS = ["clean_data.py", "make_asof.py"]


def main():
    for script in STEPS:
        extra = sys.argv[1:] if script == "make_asof.py" else []
        print(f"=== {script} {' '.join(extra)}".rstrip(), flush=True)
        subprocess.run([sys.executable, str(HERE / script), *extra], cwd=PROJECT, check=True)


if __name__ == "__main__":
    main()
