import struct
def dec(d):
    n=struct.unpack('<I',d[:4])[0]; i=8; out=bytearray()
    while i<len(d)-1 and len(out)<n:
        fl=d[i]|(d[i+1]<<8); i+=2
        for b in range(16):
            if len(out)>=n or i>=len(d): break
            if fl>>b&1:
                b0,b1=d[i],d[i+1]; i+=2
                ln=(b0&15)+1; off=b1|((b0>>4)<<8)
                if off==0 or off>len(out): raise ValueError('bad')
                for _ in range(ln): out.append(out[-off])
            else: out.append(d[i]); i+=1
    return bytes(out[:n]),n
