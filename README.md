# MI Analyzer

## Install 

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Overview

This small tool collects Maintainability Index (MI) metrics (via Radon) and provides two CLI commands:

- `mi-analysis static <repo>`: run a quick static MI check over a repo and print files with low MI ratings.
- `mi-analysis history <repo>`: sample repository commits and produce a time series of average MI; outputs JSON to stdout or an HTML report with an embedded plot when `--output` is provided.

## Commands

- static
	- Usage: `mi-analysis static <repo> [--output OUTPUT]`
	- Runs `radon mi -j` on the provided repository (local path or git URL). If a remote URL is provided, the repo will be cloned to a temporary folder.
	- Prints each file's MI and a rating (A..E). Files rated `A` are skipped by default.
	- `--output` (optional): path to append plain textual output (the code uses a simple `typer.echo` override so output is written as plain text).

- history
	- Usage: `mi-analysis history <repo> [--max-commits INT] [--skip INT] [--branch STR] [--output OUTPUT]`
	- Samples up to `--max-commits` commits (default 50), selecting evenly-spaced commits across the branch (defaults to `HEAD`).
	- `--skip` will sample every Nth commit while iterating (default 1).
	- For each sampled commit the tool checks out that commit, runs Radon, and computes the average MI across files. The result is a JSON time series printed to stdout by default.
	- If `--output` is provided, the command writes a single HTML report containing an embedded PNG plot of the MI time series and metadata (repo, branch, collected points, etc.).

## Examples

Quick static analysis and write plain output to a file:

```bash
mi-analysis static https://github.com/pallets/flask.git --output static_output.txt
```

Create a historic MI HTML report (samples commits and writes an HTML file with an embedded plot):

```bash
mi-analysis history https://github.com/pallets/flask.git --max-commits 100 --skip 1 --branch main --output mi_history.html
```

Or print the JSON time series to stdout:

```bash
mi-analysis history https://github.com/pallets/flask.git --max-commits 30
```

Notes and requirements

- The `history` command is the one that generates an HTML report when `--output` is given. The `static` command writes plain text to `--output` if provided.
- Dependencies required (see `setup.py`): `typer`, `radon`, `GitPython`, and `matplotlib`.
- `radon` must be available in the same environment where you run the CLI since the tool invokes the `radon` CLI (`radon mi -j`).
- When analyzing remote repositories the tool clones the repo to a temporary folder and removes it when finished.

Troubleshooting

- If Radon returns no data, the tool will skip reporting average MI values and continue; ensure `radon` can analyze the repository language and files present.
- When the `history` command cannot parse commit dates or render the plot, it will skip those points or raise an error indicating no valid date points to plot.

License / Credits

This project is a small demonstrator for maintainability analysis and historic MI plotting.
