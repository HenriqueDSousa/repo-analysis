import io
import os
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock
from contextlib import ExitStack

import miner.miner as miner


class FakeRepo:
	def __init__(self, commits):
		self._commits = commits
		self.git = mock.Mock()

	def iter_commits(self, branch):
		return self._commits


class TestHistoryCommand(unittest.TestCase):
	def test_history_local_no_output_prints_json(self):
		# Arrange
		commits = [
			SimpleNamespace(hexsha='a1', committed_datetime=datetime(2020, 1, 1, 12, 0, 0)),
			SimpleNamespace(hexsha='b2', committed_datetime=datetime(2020, 1, 2, 13, 0, 0)),
		]
		fake_repo = FakeRepo(commits)
		buf = io.StringIO()

		# Act
		with mock.patch.object(miner, 'Repo', return_value=fake_repo):
			with mock.patch.object(miner.typer, 'echo', new=lambda msg: print(msg, file=buf)):
				miner.history('/some/local/path')
		out = buf.getvalue()

		# Assert
		self.assertIn('Analyzing commit a1', out)
		self.assertIn('Analyzing commit b2', out)
		self.assertIn('"sha": "a1"', out)
		self.assertIn('"sha": "b2"', out)

	def test_history_output_writes_html(self):
		# Arrange
		commits = [SimpleNamespace(hexsha='d4', committed_datetime=datetime(2022, 3, 3, 9, 0, 0))]
		fake_repo = FakeRepo(commits)
		with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as outtmp:
			outname = outtmp.name
		captured = []
		patches = [
			mock.patch.object(miner, 'Repo', return_value=fake_repo),
			mock.patch.object(miner, 'render_mi_plot_bytes', return_value=b'PNGBYTES'),
			mock.patch.object(miner.typer, 'echo', new=lambda msg: captured.append(msg)),
		]

		# Act
		with ExitStack() as stack:
			for p in patches:
				stack.enter_context(p)
			miner.history('/tmp/somepath', output=outname)
			with open(outname, 'r', encoding='utf-8') as fh:
				content = fh.read()

		# Assert
		self.assertIn('<!doctype html>', content)
		self.assertTrue(any('Historic MI report written to' in c for c in captured))
		os.remove(outname)
		
	def test_history_remote_triggers_clone(self):
		# Arrange
		commits = [SimpleNamespace(hexsha='r1', committed_datetime=datetime(2022, 1, 1, 0, 0, 0))]
		fake_repo = FakeRepo(commits)
		buf = io.StringIO()

		# Act
		with mock.patch.object(miner, 'Repo', autospec=True) as MockRepo:
			MockRepo.clone_from = mock.Mock()
			MockRepo.return_value = fake_repo
			with mock.patch.object(miner.typer, 'echo', new=lambda msg: print(msg, file=buf)):
				miner.history('https://example.com/repo.git')

			# Assert
			self.assertTrue(MockRepo.clone_from.called)

	def test_history_invalid_repo_path_reports_error(self):
		# Arrange
		captured = []

		# Act
		with mock.patch.object(miner, 'Repo', side_effect=Exception('bad repo')):
			with mock.patch.object(miner.typer, 'echo', new=lambda msg: captured.append(msg)):
				with self.assertRaises(miner.typer.Exit):
					miner.history('/non/existent/path')

		# Assert
		self.assertTrue(any('Erro ao abrir repositório' in c or 'Erro ao abrir' in c for c in captured))

	def test_history_no_commits_found_graceful(self):
		# Arrange
		fake_repo = FakeRepo([])
		captured = []

		# Act
		with mock.patch.object(miner, 'Repo', return_value=fake_repo):
			with mock.patch.object(miner.typer, 'echo', new=lambda msg: captured.append(msg)):
				with self.assertRaises(miner.typer.Exit):
					miner.history('/some/path')

		# Assert
		self.assertTrue(any('No commits found.' in c for c in captured))


if __name__ == '__main__':
	unittest.main()

