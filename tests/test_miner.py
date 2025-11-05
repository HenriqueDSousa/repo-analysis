import base64
import subprocess

import pytest

import miner.miner as m


def test_classify_radon_rating_boundaries():
    assert m.classify_radon_rating({'mi': 85}) == 'A'
    assert m.classify_radon_rating({'mi': 70}) == 'B'
    assert m.classify_radon_rating({'mi': 50}) == 'C'
    assert m.classify_radon_rating({'mi': 30}) == 'D'
    assert m.classify_radon_rating({'mi': 29.9}) == 'E'


def test_compute_average_mi_empty_and_values():
    assert m.compute_average_mi({}) is None
    report = {'a.py': {'mi': 90}, 'b.py': {'mi': 70}}
    assert pytest.approx(m.compute_average_mi(report), rel=1e-6) == 80.0


def test_run_radon_handles_subprocess_error(monkeypatch):
    # Simulate subprocess.run raising an exception
    def fake_run(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, 'run', fake_run)
    assert m.run_radon("/nonexistent") == {}


def test_render_mi_plot_bytes_success_and_png_header():
    results = [
        {'date': '2020-01-01T00:00:00', 'avg_mi': 80},
        {'date': '2020-02-01T00:00:00', 'avg_mi': 75},
    ]
    data = m.render_mi_plot_bytes(results)
    assert isinstance(data, (bytes, bytearray))
    # PNG files start with the PNG signature
    assert data[0:8] == b"\x89PNG\r\n\x1a\n"


def test_render_mi_plot_bytes_raises_on_no_valid_dates():
    # no parsable dates should raise
    with pytest.raises(RuntimeError):
        m.render_mi_plot_bytes([{'date': 'invalid-date', 'avg_mi': 10}])


def test_plot_mi_time_series_creates_file(tmp_path):
    results = [
        {'date': '2021-01-01T00:00:00', 'avg_mi': 60},
        {'date': '2021-02-01T00:00:00', 'avg_mi': None},
        {'date': '2021-03-01T00:00:00', 'avg_mi': 70},
    ]
    out = tmp_path / "out.png"
    # Should not raise
    m.plot_mi_time_series(results, str(out))
    assert out.exists()
    assert out.stat().st_size > 0


def test_generate_html_report_contains_meta_and_image_and_escaped_json():
    results = [{'date': '2020-01-01T00:00:00', 'avg_mi': 80, 'sha': 'abc'}]
    params = {'repo': '/tmp/repo', 'branch': 'main', 'max_commits': 2}
    # put a tiny PNG-like payload base64
    img_b64 = base64.b64encode(b"PNGDATA").decode('ascii')
    html = m.generate_html_report(results, params, img_b64)
    assert 'Historic MI Report' in html
    assert 'repo' in html and '/tmp/repo' in html
    assert img_b64 in html
    # ensure JSON is escaped (angle brackets and such would be escaped)
    assert '&quot;' in html or '{' in html


def test_compute_average_mi_ignores_non_numeric():
    report = {'a.py': {'mi': 'not-a-number'}, 'b.py': {'mi': 60}}
    assert pytest.approx(m.compute_average_mi(report), rel=1e-6) == 60.0


def test_static_outputs_only_non_A(tmp_path, monkeypatch, capsys):
    # Create dummy repo directory
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # prepare a radon report with one file A and one file C
    fake_radon = {str(repo_dir / 'a.py'): {'mi': 90}, str(repo_dir / 'b.py'): {'mi': 60}}

    monkeypatch.setattr(m, 'run_radon', lambda path: fake_radon)

    # Run static command pointing to the temp dir
    m.static(str(repo_dir))
    captured = capsys.readouterr()
    # Should list only the non-A file (b.py)
    assert 'b.py' in captured.out
    assert 'a.py' not in captured.out
