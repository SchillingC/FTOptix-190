"""Extract all HMIServer/Images/* from the .apa as PNG (multi-chunk LZ)."""
import io, os, struct, sys
import olefile
from PIL import Image

def dec_chunks(d):
    i = 0; out = bytearray()
    while i + 8 <= len(d):
        clen = struct.unpack('<I', d[i:i+4])[0]
        end = min(i + 4 + clen, len(d)); j = i + 8
        while j < end - 1:
            fl = d[j] | (d[j+1] << 8); j += 2
            for b in range(16):
                if j >= end: break
                if fl >> b & 1:
                    b0, b1 = d[j], d[j+1]; j += 2
                    ln = (b0 & 15) + 1; off = b1 | ((b0 >> 4) << 8)
                    for _ in range(ln): out.append(out[-off])
                else:
                    out.append(d[j]); j += 1
        i = end
    return bytes(out)

def main(apa, outdir, skip=()):
    os.makedirs(outdir, exist_ok=True)
    o = olefile.OleFileIO(apa)
    for p in o.listdir():
        if p[:2] != ['HMIServer', 'Images']: continue
        name = os.path.splitext(p[-1])[0]
        if name in skip: continue
        d = o.openstream(p).read()
        k = d.find(b'\x89PNG')
        try:
            raw = d[k:] if 0 <= k < 16 else dec_chunks(d)
        except Exception as ex:
            print('FAIL', name, 'decompress', ex); continue
        try:
            im = Image.open(io.BytesIO(raw)).convert('RGBA')
        except Exception as ex:
            print('FAIL', name, ex); continue
        im.save(os.path.join(outdir, name + '.png'))
        print(name, im.size)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], tuple(sys.argv[3:]))
