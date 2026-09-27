import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from keyboard_rescue.cli import atomic_export, main
from keyboard_rescue.core import MAX_INPUT_BYTES

ROOT = Path(__file__).resolve().parents[1]


def cli(*args, data=b'hkuu; w;sug', cwd=ROOT):
    return subprocess.run([sys.executable,'-m','keyboard_rescue','--observed','qwerty','--intended','colemak',*map(str,args)],
                          input=data,capture_output=True,cwd=cwd)


class CLITests(unittest.TestCase):
    def test_stdin_exact_no_added_newline(self):
        result = cli()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,b'hello world')
        self.assertIn(b'Conditional',result.stderr)

    def test_file_crlf_input_unchanged_and_private_output(self):
        with tempfile.TemporaryDirectory() as folder:
            original = Path(folder)/'input.txt'
            original.write_bytes(b'hkuu;\r\nw;sug\t')
            before = original.read_bytes()
            output = Path(folder)/'result.txt'
            result = cli(original,'-o',output)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(output.read_bytes(),b'hello\r\nworld\t')
            self.assertEqual(original.read_bytes(),before)
            self.assertEqual(output.stat().st_mode & 0o777,0o600)
            self.assertEqual(len(list(Path(folder).iterdir())),2)

    def test_invalid_utf8_and_oversized_leave_no_export(self):
        for data in (b'\xff',b'a'*MAX_INPUT_BYTES+b'b', b'\xf0\x9f'):
            with self.subTest(data_length=len(data)), tempfile.TemporaryDirectory() as folder:
                source, output = Path(folder)/'input',Path(folder)/'output'
                source.write_bytes(data)
                result = cli(source,'--format','html','-o',output)
                self.assertEqual(result.returncode,2)
                self.assertFalse(output.exists())
                self.assertEqual(source.read_bytes(),data)
                self.assertEqual(list(Path(folder).iterdir()),[source])
                stdin = cli('--format','json',data=data)
                self.assertEqual(stdin.returncode,2)
                self.assertEqual(stdin.stdout,b'')

    def test_exact_size_limit(self):
        result = cli(data=b'a'*MAX_INPUT_BYTES)
        self.assertEqual(result.returncode,0)
        self.assertEqual(len(result.stdout),MAX_INPUT_BYTES)

    def test_collisions_input_hardlinks_symlinks_and_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'source'
            source.write_bytes(b'hkuu;')
            hardlink,symlink,dangling,directory = [Path(folder)/p for p in ('hard','sym','dangling','dir')]
            os.link(source,hardlink)
            symlink.symlink_to(source)
            dangling.symlink_to(Path(folder)/'absent')
            directory.mkdir()
            for output in (source,hardlink,symlink,dangling,directory):
                result = cli(source,'-o',output)
                self.assertEqual(result.returncode,2,result.stderr)
                self.assertEqual(source.read_bytes(),b'hkuu;')
                self.assertFalse(list(Path(folder).glob('*.partial')))
            self.assertTrue(dangling.is_symlink())
            self.assertFalse(dangling.exists())

    def test_atomic_failures_cleanup(self):
        for failure in (OSError('disk full'),KeyboardInterrupt()):
            for operation in ('fsync','link'):
                with self.subTest(operation=operation), tempfile.TemporaryDirectory() as folder:
                    output = Path(folder)/'report.html'
                    with patch('keyboard_rescue.cli.os.'+operation,side_effect=failure):
                        with self.assertRaises(type(failure)):
                            atomic_export(output,b'complete report')
                    self.assertEqual(list(Path(folder).iterdir()),[])
        # Inject an actual write failure after partial bytes have reached the temp file.
        real_fdopen = os.fdopen
        class FailedWriter:
            def __init__(self,fd,mode): self.stream = real_fdopen(fd,mode)
            def __enter__(self): return self
            def __exit__(self,*args): self.stream.close()
            def write(self,data):
                self.stream.write(data[:3]); self.stream.flush()
                raise OSError('simulated short write / disk full')
        with tempfile.TemporaryDirectory() as folder:
            with patch('keyboard_rescue.cli.os.fdopen',FailedWriter):
                with self.assertRaises(OSError): atomic_export(Path(folder)/'out',b'abcdef')
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_real_sigterm_during_export_cleans_temporary(self):
        # Signal exactly while fsync has the staged file open; no timing race.
        real_fsync = os.fsync
        def interrupted_sync(fd):
            real_fsync(fd)
            os.kill(os.getpid(),signal.SIGTERM)
        with tempfile.TemporaryDirectory() as folder:
            source,output = Path(folder)/'source',Path(folder)/'output'
            source.write_bytes(b'hkuu;')
            with patch('keyboard_rescue.cli.os.fsync',interrupted_sync), contextlib.redirect_stderr(io.StringIO()):
                code = main([str(source),'--observed','qwerty','--intended','colemak','-o',str(output)])
            self.assertEqual(code,130)
            self.assertEqual(list(Path(folder).iterdir()),[source])

    def test_racing_destination_is_preserved(self):
        real_link = os.link
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'output'
            def race(source,destination):
                output.write_bytes(b'concurrent owner')
                real_link(source,destination)
            with patch('keyboard_rescue.cli.os.link',race):
                with self.assertRaises(FileExistsError): atomic_export(output,b'my output')
            self.assertEqual(output.read_bytes(),b'concurrent owner')
            self.assertEqual(list(Path(folder).iterdir()),[output])

    def test_unresolved_is_valid_export_with_exit_three(self):
        result = cli('--format','json',data='🙂hkuu;'.encode())
        self.assertEqual(result.returncode,3)
        report = json.loads(result.stdout)
        self.assertEqual(report['candidates'][0]['text'],'🙂hello')
        self.assertEqual(report['candidates'][0]['diagnostics'][0]['index'],0)
        self.assertIn(b'1 unresolved',result.stderr)

    def test_cli_errors_and_multiple_candidates(self):
        for args in [('--span','oops'),('--span','2:999'),('--intended','dvorak'),('--intended','colemak','--format','json')]:
            result = cli(*args)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertEqual(result.stdout,b'')
        result = cli('--intended','dvorak','--format','json')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['candidates']),2)
