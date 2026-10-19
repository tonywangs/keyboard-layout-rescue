"""Download public pinned assets into an explicitly chosen external cache."""
import hashlib
import sys
import tarfile
import urllib.request
from pathlib import Path

ASSETS = {
    'model.gguf': ('https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf', '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'),
    'llama.tar.gz': ('https://github.com/ggml-org/llama.cpp/releases/download/b11723/llama-b11723-bin-ubuntu-x64.tar.gz', '8f5652caad0ee6a6473e7eb03a08674f429375554852b83fd7156d550669d069')}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def main():
    root=Path(sys.argv[1]).resolve()
    repo=Path(__file__).resolve().parents[2]
    if root==repo or repo in root.parents:
        raise SystemExit('Choose a cache outside the project repository.')
    root.mkdir(parents=True,exist_ok=True)
    for name,(url,expected) in ASSETS.items():
        target=root/name
        if not target.exists():
            partial=root/(name+'.partial')
            with urllib.request.urlopen(url,timeout=120) as response, partial.open('wb') as f:
                while block:=response.read(1024*1024):
                    f.write(block)
            if sha(partial)!=expected:
                raise SystemExit('Downloaded asset hash mismatch: '+name)
            partial.rename(target)
        if sha(target)!=expected:
            raise SystemExit('Cached asset hash mismatch: '+name)
    if not (root/'llama-b11723').exists():
        with tarfile.open(root/'llama.tar.gz') as archive:
            # Archive bytes are pinned above. Reject path escapes as an additional check.
            for member in archive.getmembers():
                dest=(root/member.name).resolve()
                if root not in dest.parents:
                    raise SystemExit('Archive path escapes cache')
            archive.extractall(root, filter='data')
    print('Verified model and archive in',root)

if __name__=='__main__':
    main()
