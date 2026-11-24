#!/usr/bin/env python3
"""Extract machine alarm messages (all languages) from the FTView ME .apa -> analysis/alarms.json.

Streams in the .apa are stored as chunks: [u32 compressed_len][u32 magic] + LZ data
(len counts from offset 4). A stream may consist of several chunks.
"""
import json, os, re, struct, sys, tempfile
import olefile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG = {"0407": "de-DE", "040c": "fr-FR", "0411": "ja-JP", "0413": "nl-NL", "0415": "pl-PL", "0809": "en-GB", "0c0a": "es-ES"}

def dec_chunks(d):
    i, out = 0, bytearray()
    while i + 8 <= len(d):
        end = min(i + 4 + struct.unpack("<I", d[i:i + 4])[0], len(d))
        j = i + 8
        while j < end - 1:
            fl = d[j] | (d[j + 1] << 8); j += 2
            for b in range(16):
                if j >= end: break
                if fl >> b & 1:
                    b0, b1 = d[j], d[j + 1]; j += 2
                    off = b1 | ((b0 >> 4) << 8)
                    for _ in range((b0 & 15) + 1): out.append(out[-off])
                else:
                    out.append(d[j]); j += 1
        i = end
    return bytes(out)

def main(apa):
    ole = olefile.OleFileIO(apa)
    mal = dec_chunks(ole.openstream(["HMIServer", "M_Alarms", "MachineAlarms.mal"]).read())
    tmp = tempfile.NamedTemporaryFile(delete=False); tmp.write(mal); tmp.close()
    m = olefile.OleFileIO(tmp.name)
    res = {}
    for (n,) in [s for s in m.listdir() if s[0].startswith("ls0000")]:
        b = m.openstream(n).read()
        t = b[b.find("lbl".encode("utf-16le")):].decode("utf-16le", "ignore")
        msgs = []
        for p in re.split(r"(?=lbl[A-Za-z]+|[A-Z]\d\d\.\d\d: )", t):
            x = re.match(r"([A-Z])(\d\d)\.(\d\d): (.*)$", p, re.S)
            if x: msgs.append([x[1], int(x[2]), int(x[3]), x[4].strip()])
        res[LANG[n[-4:]]] = msgs
    os.unlink(tmp.name)
    json.dump(res, open(os.path.join(ROOT, "analysis", "alarms.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print({k: len(v) for k, v in res.items()})

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "HMI190V03_002.apa"))
