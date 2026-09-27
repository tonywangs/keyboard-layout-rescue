#!/usr/bin/env python3
"""Exercise the offline installer and documented use cases away from the checkout."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='keyboard-rescue-installed-') as folder:
        work = Path(folder)
        prefix = work / 'isolated installation with spaces'
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/install.py'),str(prefix)],check=True,cwd=work)
        executable = prefix / 'bin/keyboard-rescue'
        python = prefix / 'bin/python'
        site = Path(subprocess.check_output([str(python),'-I','-c','import sysconfig; print(sysconfig.get_path("purelib"))'],text=True).strip())
        # This hook runs in the installed interpreter and makes socket operations fail.
        # It also proves that the hook was loaded for every tested invocation.
        audit = work/'audit.txt'
        (site/'rescue_offline_guard.py').write_text(
            'import sys\nfrom pathlib import Path\n'
            f'with Path({str(audit)!r}).open("a") as f: f.write("loaded\\n")\n'
            'def offline(event, args):\n'
            '    if event.startswith("socket."): raise RuntimeError("network forbidden in offline verification")\n'
            'sys.addaudithook(offline)\n')
        (site/'rescue_offline_guard.pth').write_text('import rescue_offline_guard\n')
        env = {**os.environ, 'PYTHONPATH':str(ROOT), 'PIP_NO_INDEX':'1'}
        def run(*args, data=b'', code=0):
            result = subprocess.run([str(executable),*map(str,args)],cwd=work,env=env,input=data,capture_output=True)
            assert result.returncode==code,(args,result.returncode,result.stderr)
            return result
        base = ['--observed','qwerty','--intended','colemak']
        assert run(*base,data=b'hkuu; w;sug').stdout == b'hello world'
        (work/'wrong.txt').write_bytes(b'hkuu; w;sug\r\n')
        run('wrong.txt',*base,'-o','recovered.txt')
        assert (work/'recovered.txt').read_bytes()==b'hello world\r\n'
        assert (work/'wrong.txt').read_bytes()==b'hkuu; w;sug\r\n'
        run('wrong.txt',*base,'--intended','dvorak','--format','html','-o','comparison.html')
        assert b'Keyboard Layout Rescue' in (work/'comparison.html').read_bytes()
        result = run(*base,'--span','11:22','--format','json',data=b'Keep this: hkuu; w;sug.')
        assert json.loads(result.stdout)['candidates'][0]['text']=='Keep this: hello world.'
        result = run('--observed','qwerty','--intended','dvorak','--geometry','iso','--format','json',data=b'<>',code=3)
        assert json.loads(result.stdout)['candidates'][0]['unresolved_characters']==2
        run('wrong.txt',*base,'-o','wrong.txt',code=2)
        assert (work/'wrong.txt').read_bytes()==b'hkuu; w;sug\r\n'
        assert len(audit.read_text().splitlines())==6, 'network audit hook did not run in every CLI'
        # A deliberate socket operation proves the offline hook is active.
        denial = subprocess.run([str(python),'-I','-c','import socket; socket.socket()'],capture_output=True)
        assert denial.returncode != 0 and b'network forbidden' in denial.stderr
        duplicate = subprocess.run([sys.executable,'-I',str(ROOT/'scripts/install.py'),str(prefix)],capture_output=True)
        assert duplicate.returncode==2
        assert executable.exists()
        print('Installed CLI: 6 offline scenarios passed in a fresh venv, outside checkout; socket audit guard verified.')


if __name__ == '__main__':
    main()
