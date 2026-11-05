"""Run the full data pipeline from the raw file to the modeling dataset.

    datathon-dataset.xlsx -> clean_data.py -> data_clean.csv
                          -> make_may1.py  -> data_may1.csv (+ late_applicants_by_year.csv)
                          -> make_days.py  -> data_may1_days.csv

Each script runs with the project folder as the working directory, so inputs and outputs use
the default paths in the scripts (all in the project folder).

Usage (from anywhere):
    python data_cleaning/run_all.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
STEPS = ["clean_data.py", "make_may1.py", "make_days.py"]


def main():
    for script in STEPS:
        print(f"=== {script}", flush=True)
        subprocess.run([sys.executable, str(HERE / script)], cwd=PROJECT, check=True)


if __name__ == "__main__":
    main()
