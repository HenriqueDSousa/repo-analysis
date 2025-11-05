import os
import typer
import tempfile
import shutil
import subprocess
import json
import io
import base64
import html as html_lib
import math
from datetime import datetime
from git import Repo 
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

app = typer.Typer(help="MI Analysis Miner")

def run_radon(repo_path: str):
    """Run Radon for maintainability & complexity"""
    try:
        result = subprocess.run(
            ["radon", "mi", "-j", repo_path],
            capture_output=True,
            text=True,
            check=False
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return {}
    except Exception as e:
        typer.echo(f"Erro ao rodar Radon: {e}")
        return {}


def classify_radon_rating(score):
    if score['mi'] >= 85:
        return 'A'
    elif score['mi'] >= 70:
        return 'B'
    elif score['mi'] >= 50:
        return 'C'
    elif score['mi'] >= 30:
        return 'D'
    else:
        return 'E'


def compute_average_mi(radon_report: dict):
    """Compute average Maintainability Index across files in radon JSON output.

    Returns None when report is empty.
    """
    if not radon_report:
        return None
    vals = [v.get('mi') for v in radon_report.values() if isinstance(v.get('mi'), (int, float))]
    if not vals:
        return None
    return sum(vals) / len(vals)


def plot_mi_time_series(results: list, path: str):
    """Plot average MI over time and save to `path`.

    Expects `results` to be list of dicts with 'date' and 'avg_mi' keys.
    """
    dates = []
    values = []
    for r in results:
        try:
            d = datetime.fromisoformat(r['date'])
        except Exception:
            # skip unparsable dates
            continue
        mi = r.get('avg_mi')
        if mi is None:
            # Represent missing values as nan to create gaps
            import math
            mi = math.nan
        dates.append(d)
        values.append(mi)

    if not dates:
        raise RuntimeError("No valid date points to plot")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, values, marker='o', linestyle='-')
    ax.set_xlabel('Commit date')
    ax.set_ylabel('Average MI')
    ax.set_title('Maintainability Index over time')
    ax.grid(True, linestyle='--', alpha=0.4)

    # Format dates nicely
    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def render_mi_plot_bytes(results: list) -> bytes:
    """Render the MI time series to PNG bytes and return them."""
    dates = []
    values = []
    for r in results:
        try:
            d = datetime.fromisoformat(r['date'])
        except Exception:
            continue
        mi = r.get('avg_mi')
        if mi is None:
            mi = math.nan
        dates.append(d)
        values.append(mi)

    if not dates:
        raise RuntimeError("No valid date points to plot")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, values, marker='o', linestyle='-')
    ax.set_xlabel('Commit date')
    ax.set_ylabel('Average MI')
    ax.set_title('Maintainability Index over time')
    ax.grid(True, linestyle='--', alpha=0.4)

    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    fig.autofmt_xdate()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_html_report(results: list, params: dict, img_b64: str) -> str:
    """Generate a simple HTML report embedding the plot image and metadata.

    - results: list of result dicts
    - params: dictionary of parameters (repo, branch, max_commits, skip, total_commits)
    - img_b64: base64-encoded PNG image data (without data: prefix)
    """
    pretty_json = html_lib.escape(json.dumps(results, indent=2, ensure_ascii=False))
    meta_rows = []
    for k, v in params.items():
        meta_rows.append(f"<tr><th style=\"text-align:left;padding-right:8px;\">{html_lib.escape(str(k))}</th><td>{html_lib.escape(str(v))}</td></tr>")
    meta_table = "\n".join(meta_rows)

    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Historic MI Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    pre {{ background: #f6f8fa; padding: 12px; border-radius: 6px; overflow: auto; }}
    table {{ border-collapse: collapse; margin-bottom: 12px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 10px; }}
  </style>
</head>
<body>
  <h1>Historic MI Report</h1>
  <h2>Metadata</h2>
  <table>
    {meta_table}
  </table>
  <h2>MI Time Series</h2>
  <img src="data:image/png;base64,{img_b64}" alt="MI time series" style="max-width:100%;height:auto;" />
  <h2>Raw Results (JSON)</h2>
  <pre>{pretty_json}</pre>
</body>
</html>
"""
    return html

# -------------------------
# CLI
# -------------------------
@app.command()
def static(repo: str,
           output: str = None):
    """
    Detecta God Classes e executa análises estáticas adicionais.
    """
    temp_dir = None
    repo_path = repo

    if output:
        typer.echo = lambda msg: print(msg, file=open(output, "a", encoding="utf-8"))

    # Clone if GitHub link
    if repo.startswith("http://") or repo.startswith("https://"):
        typer.echo(f"📥 Clonando repositório {repo} ...")
        temp_dir = tempfile.mkdtemp()
        repo_path = os.path.join(temp_dir, "repo")
        Repo.clone_from(repo, repo_path)

    typer.echo("\n=== 📊 CODE QUALITY (Radon) ===")
    radon_report = run_radon(repo_path)
    for file, score in radon_report.items():
        radon_rating = classify_radon_rating(score)
        if radon_rating == 'A':
            continue 
        rel_path = os.path.relpath(file, repo_path)

        typer.echo(f"- {rel_path}: {round(score['mi'], 2)}, {radon_rating}")

    if temp_dir:
        shutil.rmtree(temp_dir)


@app.command()
def history(repo: str,
            max_commits: int = 50,
            skip: int = 1,
            branch: str = 'HEAD',
            output: str = None):
    """
    Create a historic analysis of MI (Maintainability Index) over repository commits.

    - repo: local path or git URL
    - max_commits: how many recent commits to sample (newest commits)
    - skip: sample every Nth commit (1 = every commit)
    - branch: branch or ref to walk (defaults to HEAD)
    - output: optional output JSON path; prints to stdout if not provided
    """
    temp_dir = None
    repo_path = repo
    # Clone if remote
    if repo.startswith("http://") or repo.startswith("https://"):
        typer.echo(f"📥 Clonando repositório {repo} ...")
        temp_dir = tempfile.mkdtemp()
        repo_path = os.path.join(temp_dir, "repo")
        Repo.clone_from(repo, repo_path)

    repo_obj = Repo(repo_path)

    typer.echo(f"Gathering up to {max_commits} commits from {branch} ...")
    try:
        # Get all commits first
        all_commits = list(repo_obj.iter_commits(branch))
        total_commits = len(all_commits)
        
        # Calculate step size to get evenly spaced commits
        step = max(1, total_commits // max_commits)
        
        # Select evenly spaced commits
        commits = all_commits[::step][:max_commits]
        
    except Exception as e:
        typer.echo(f"Error fetching commits: {e}")
        if temp_dir:
            shutil.rmtree(temp_dir)
        raise typer.Exit(code=1)

    # Walk oldest -> newest for time series
    commits.reverse()

    # Save current HEAD to restore later
    try:
        current_ref = repo_obj.head.commit.hexsha
    except Exception:
        current_ref = None

    results = []
    for idx, commit in enumerate(commits):
        if (idx % skip) != 0:
            continue
        sha = commit.hexsha
        date = commit.committed_datetime.isoformat()
        typer.echo(f"- Analyzing commit {sha} @ {date}")

        # checkout commit
        try:
            repo_obj.git.checkout(sha)
        except Exception as e:
            typer.echo(f"  Error checking out {sha}: {e}")
            continue

        # run radon
        radon_report = run_radon(repo_path)
        avg_mi = compute_average_mi(radon_report)
        entry = {
            'sha': sha,
            'date': date,
            'avg_mi': None if avg_mi is None else round(avg_mi, 2),
            'files': len(radon_report or {}),
        }
        results.append(entry)

    # restore previous HEAD
    if current_ref:
        try:
            repo_obj.git.checkout(current_ref)
        except Exception:
            # if it fails, ignore
            pass

    # output: if output provided, create a single HTML report (plot embedded + metadata)
    if output:
        try:
            # render plot to bytes and base64-encode
            img_bytes = render_mi_plot_bytes(results)
            img_b64 = base64.b64encode(img_bytes).decode('ascii')

            params = {
                'repo': repo,
                'branch': branch,
                'max_commits': max_commits,
                'skip': skip,
                'collected_points': len(results),
            }
            html = generate_html_report(results, params, img_b64)
            with open(output, 'w', encoding='utf-8') as fh:
                fh.write(html)
            typer.echo(f"Historic MI report written to {output}")
        except Exception as e:
            typer.echo(f"Error creating HTML report {output}: {e}")
    else:
        typer.echo(json.dumps(results, indent=2, ensure_ascii=False))

    if temp_dir:
        shutil.rmtree(temp_dir)
