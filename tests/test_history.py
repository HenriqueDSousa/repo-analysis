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
		commits = [
			SimpleNamespace(hexsha='a1', committed_datetime=datetime(2020, 1, 1, 12, 0, 0)),
			SimpleNamespace(hexsha='b2', committed_datetime=datetime(2020, 1, 2, 13, 0, 0)),
		]
		fake_repo = FakeRepo(commits)

		with mock.patch.object(miner, 'Repo') as MockRepo:
			MockRepo.return_value = fake_repo
			buf = io.StringIO()
			with mock.patch.object(miner.typer, 'echo', new=lambda msg: print(msg, file=buf)):
				miner.history('/some/local/path')
			out = buf.getvalue()

		self.assertIn('Analyzing commit a1', out)
		self.assertIn('Analyzing commit b2', out)
		self.assertIn('"sha": "a1"', out)
		self.assertIn('"sha": "b2"', out)

	def test_history_output_writes_html(self):
		commits = [SimpleNamespace(hexsha='d4', committed_datetime=datetime(2022, 3, 3, 9, 0, 0))]
		fake_repo = FakeRepo(commits)
		outtmp = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
		outname = outtmp.name
		outtmp.close()
		try:
			captured = []
			with ExitStack() as stack:
				stack.enter_context(mock.patch.object(miner, 'Repo', return_value=fake_repo))
				stack.enter_context(mock.patch.object(miner, 'render_mi_plot_bytes', return_value=b'PNGBYTES'))
				stack.enter_context(mock.patch.object(miner.typer, 'echo', new=lambda msg: captured.append(msg)))

				miner.history('/tmp/somepath', output=outname)

			with open(outname, 'r', encoding='utf-8') as fh:
				content = fh.read()
			self.assertIn('<!doctype html>', content)
			self.assertTrue(any('Historic MI report written to' in c for c in captured))
		finally:
			try:
				os.remove(outname)
			except OSError:
				pass

	def test_history_remote_triggers_clone(self):
		commits = [SimpleNamespace(hexsha='r1', committed_datetime=datetime(2022, 1, 1, 0, 0, 0))]
		fake_repo = FakeRepo(commits)

		# Patch the Repo object so clone_from can be observed and constructor returns fake_repo
		with mock.patch.object(miner, 'Repo', autospec=True) as MockRepo:
			MockRepo.clone_from = mock.Mock()
			MockRepo.return_value = fake_repo
			buf = io.StringIO()
			with mock.patch.object(miner.typer, 'echo', new=lambda msg: print(msg, file=buf)):
				miner.history('https://example.com/repo.git')

		# Ensure clone_from was called
		self.assertTrue(MockRepo.clone_from.called)

	def test_history_invalid_repo_path_reports_error(self):
		# Simulate Repo constructor raising for invalid path
		with mock.patch.object(miner, 'Repo', side_effect=Exception('bad repo')):
			captured = []
			with mock.patch.object(miner.typer, 'echo', new=lambda msg: captured.append(msg)):
				with self.assertRaises(miner.typer.Exit):
					miner.history('/non/existent/path')

		# Confirm error message was echoed
		self.assertTrue(any('Erro ao abrir repositório' in c or 'Erro ao abrir' in c for c in captured))

	def test_history_no_commits_found_graceful(self):
		# Repo that returns no commits
		fake_repo = FakeRepo([])
		with mock.patch.object(miner, 'Repo', return_value=fake_repo):
			captured = []
			with mock.patch.object(miner.typer, 'echo', new=lambda msg: captured.append(msg)):
				with self.assertRaises(miner.typer.Exit):
					miner.history('/some/path')

		self.assertTrue(any('No commits found.' in c for c in captured))


if __name__ == '__main__':
	unittest.main()

