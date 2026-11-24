# Analyse FTView-ME-Projekt HMI190V03_002

- `HMI_flat_tags.csv`: alle Leaf-Tags von `HMI` (UDT_HMI), extrahiert aus `CPX190V06_001.ACD` (acd-tools, `TagInfo.XML`).
- `../tools/apa_decompress.py`: Dekompression der `.apa`-Streams (LZ-Variante, 4-Byte-Länge, 4-Byte-Header, 16-Bit-Flags, Match = Länge `(b0&15)+1`, Offset `b1|(b0>>4)<<8`).
