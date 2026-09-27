"""Frozen workload suite v1. Recipes are fixed; hashes checked in workloads.json."""
import hashlib

CASES = {
    'ordinary': ('hkuu; w;sug\r\nA small recovery example.\t'*8, 'ansi'),
    'ambiguity': ('<>-_'*256, 'iso'),
    'unicode': ('🙂é\u0301\u202e\ufeff\x00\t\r\n'*128, 'ansi'),
    'hostile': ('</script><script>globalThis.PWNED=1</script><img src="https://invalid.example/x" onerror="globalThis.PWNED=2">&\u2028'*16, 'iso'),
    'boundary_alternating': ('e '*32768, 'ansi'),
    'boundary_ambiguity': ('<'*65536, 'iso'),
    'boundary_unicode': ('🙂'*16384, 'ansi'),
    # CRLF straddles a naive page boundary; supplementary and combining characters follow.
    'page_edges': ('e'*1999+'\r\n🙂e\u0301'+'<>\x00'*900, 'iso'),
}


def manifest():
    return {name: {'input_bytes':len(text.encode()), 'input_sha256':hashlib.sha256(text.encode()).hexdigest(),
                   'geometry':geometry, 'observed':'qwerty', 'intended':['colemak','dvorak']}
            for name,(text,geometry) in CASES.items()}
