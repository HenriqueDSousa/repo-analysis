import io
import os
import tempfile
import shutil
import unittest
from contextlib import redirect_stdout
from unittest import mock

import miner.miner as miner


class TestStaticCommand(unittest.TestCase):
    def setUp(self):
        self._orig_echo = miner.typer.echo

    def tearDown(self):
        miner.typer.echo = self._orig_echo

    def test_static_local_repo_prints_radon_output(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            module_path = os.path.join(repo_dir, "module.py")
            fake_report = {module_path: {"mi": 90.123}}
            buf = io.StringIO()
            with mock.patch.object(miner, 'run_radon', return_value=fake_report):
                with redirect_stdout(buf):
                    miner.static(repo_dir)

            output = buf.getvalue()

            self.assertIn('CODE QUALITY (Radon)', output)
            self.assertIn('- module.py: 90.12, A', output)
            
    def test_static_remote_repo_clones_and_cleans_tempdir(self):
        remote = 'https://github.com/example/repo.git'
        temp_dir = tempfile.mkdtemp()
        try:
            with mock.patch.object(miner, 'tempfile') as mock_tempfile, \
                    mock.patch.object(miner.Repo, 'clone_from') as mock_clone, \
                    mock.patch.object(miner, 'run_radon', return_value={}) as mock_run_radon, \
                    mock.patch.object(miner, 'shutil') as mock_shutil:
                mock_tempfile.mkdtemp.return_value = temp_dir

                miner.static(remote)

                expected_clone_path = os.path.join(temp_dir, 'repo')
                mock_clone.assert_called_once_with(remote, expected_clone_path)
                mock_shutil.rmtree.assert_called_once_with(temp_dir)
        finally:
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)

    def test_static_output_to_file_writes(self):
        # create a temporary repository directory and a dummy file inside it
        with tempfile.TemporaryDirectory() as repo_dir:
            pkg_path = os.path.join(repo_dir, "pkg.py")
            with open(pkg_path, "w", encoding="utf-8") as f:
                f.write("# testing\n")
            report = {pkg_path: {"mi": 55.0}}
            with tempfile.NamedTemporaryFile(delete=False, mode="w+", encoding="utf-8") as outfh:
                outname = outfh.name
            try:
                with mock.patch.object(miner, "run_radon", return_value=report):
                    miner.static(repo_dir, output=outname)

                with open(outname, "r", encoding="utf-8") as fh:
                    content = fh.read()
                self.assertIn("CODE QUALITY (Radon)", content)
                self.assertIn("- pkg.py: 55.0, C", content)
            finally:
                if os.path.exists(outname):
                    os.remove(outname)

    def test_static_handles_empty_radon_report(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            with mock.patch.object(miner, 'run_radon', return_value={}):
                with mock.patch.object(miner, 'classify_radon_rating') as mock_classify:
                    buf = io.StringIO()
                    with mock.patch('sys.stdout', buf):
                        miner.static(repo_dir)

                    output = buf.getvalue()

        self.assertIn('CODE QUALITY (Radon)', output)
        self.assertNotIn('- ', output)
        mock_classify.assert_not_called()

    def test_static_does_not_cleanup_local_repo(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            with mock.patch.object(miner, 'run_radon', return_value={}):
                with mock.patch.object(miner, 'shutil') as mock_shutil:
                    buf = io.StringIO()
                    with mock.patch('sys.stdout', buf):
                        miner.static(repo_dir)

                    output = buf.getvalue()

                    self.assertIn('CODE QUALITY (Radon)', output)
                    mock_shutil.rmtree.assert_not_called()


if __name__ == '__main__':
    unittest.main()
