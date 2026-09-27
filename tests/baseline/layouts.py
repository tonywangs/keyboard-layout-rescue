"""Manually transcribed first two levels; independently verified with libxkbcommon.

Source: xkeyboard-config 2426c5997e9f76a45df2016d1092bff360712e70,
see vendor/xkeyboard-config/COPYING and PROVENANCE.json. No host layout lookup.
"""
REVISION = "2426c5997e9f76a45df2016d1092bff360712e70"
LAYOUTS = ("qwerty", "dvorak", "colemak")
KEY_ROWS = (
    ("TLDE", *(f"AE{i:02}" for i in range(1, 13))),
    (*(f"AD{i:02}" for i in range(1, 13)), "BKSL"),
    tuple(f"AC{i:02}" for i in range(1, 12)),
    tuple(f"AB{i:02}" for i in range(1, 11)),
    ("SPCE",),
)
# Each row contains base then Shift characters in physical key order.
ROWS = {
    "qwerty": (
        ("`1234567890-=", "~!@#$%^&*()_+"),
        ("qwertyuiop[]\\", "QWERTYUIOP{}|"),
        ("asdfghjkl;'", 'ASDFGHJKL:"'),
        ("zxcvbnm,./", "ZXCVBNM<>?"), (" ", " "),
    ),
    "dvorak": (
        ("`1234567890[]", "~!@#$%^&*(){}"),
        ("',.pyfgcrl/=\\", '\"<>PYFGCRL?+|'),
        ("aoeuidhtns-", "AOEUIDHTNS_"),
        (";qjkxbmwvz", ":QJKXBMWVZ"), (" ", " "),
    ),
    "colemak": (
        ("`1234567890-=", "~!@#$%^&*()_+"),
        ("qwfpgjluy;[]\\", "QWFPGJLUY:{}|"),
        ("arstdhneio'", 'ARSTDHNEIO"'),
        ("zxcvbkm,./", "ZXCVBKM<>?"), (" ", " "),
    ),
}


def mapping(layout, geometry="ansi"):
    if layout not in LAYOUTS or geometry not in ("ansi", "iso"):
        raise ValueError("unknown layout or geometry")
    result = {}
    for keys, levels in zip(KEY_ROWS, ROWS[layout]):
        assert len(keys) == len(levels[0]) == len(levels[1])
        for i, key in enumerate(keys):
            result[key] = (levels[0][i], levels[1][i])
    if geometry == "iso":
        result["LSGT"] = ("-", "_") if layout == "colemak" else ("<", ">")
    return result
