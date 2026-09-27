#!/usr/bin/env python3
"""Minimal fresh supervisor so parent benchmark buffers cannot inflate child RSS."""
import json
import os
import subprocess
import sys
import tempfile
import time

with tempfile.TemporaryFile() as errors:
    start = time.perf_counter()
    process = subprocess.Popen(sys.argv[1:],stdout=subprocess.DEVNULL,stderr=errors)
    _,status,usage = os.wait4(process.pid,0)
    elapsed = time.perf_counter()-start
    process.returncode = os.waitstatus_to_exitcode(status)
    errors.seek(0)
    print(json.dumps({'returncode':process.returncode,'wall_seconds':round(elapsed,6),
                      'peak_rss_kib':usage.ru_maxrss,'stderr':errors.read(8192).decode(errors='replace')}))
