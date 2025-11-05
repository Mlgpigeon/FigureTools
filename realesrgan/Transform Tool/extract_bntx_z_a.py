import struct, os, sys, io

def find_pattern(data: bytes, pattern: bytes):
    i = data.find(pattern)
    return i if i != -1 else None

def read_u32(data, off):
    return struct.unpack_from("<I", data, off)[0]

def read_u16(data, off):
    return struct.unpack_from("<H", data, off)[0]

def dump_astc(data, out_path):
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"[+] ASTC dump saved: {out_path}")

def main(path):
    with open(path, "rb") as f:
        buf = f.read()

    print(f"[*] Reading {path} ({len(buf)} bytes)")

    off_bntx = find_pattern(buf, b"BNTX")
    off_brt = find_pattern(buf, b"BRTD") or find_pattern(buf, b"BRTI")
    if off_brt is None:
        print("[-] Could not find BRTD/BRTI marker.")
        return

    # read some metadata around the BRTD block
    possible_sizes = []
    for i in range(off_brt, min(len(buf), off_brt + 0x200)):
        w = read_u32(buf, i)
        h = read_u32(buf, i + 4)
        if 4 <= w <= 8192 and 4 <= h <= 8192 and (w % 2 == 0) and (h % 2 == 0):
            possible_sizes.append((i - off_brt, w, h))
    if possible_sizes:
        print("[?] Possible WxH values:", possible_sizes[:3])
        _, width, height = possible_sizes[0]
    else:
        width, height = 1024, 1024  # fallback
        print("[!] Could not auto-detect size, guessing 1024x1024")

    # crude search for texture block: large region near end of file
    # often the TEXDATA starts after last "BRTD" header (~4–8 KB after marker)
    start_data = off_brt + 0x1000
    # align to 0x40
    start_data = (start_data + 0x3F) & ~0x3F
    tex_data = buf[start_data:]
    print(f"[*] Extracted {len(tex_data)} bytes of raw texture data at 0x{start_data:X}")

    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    out_astc = os.path.join(out_dir, os.path.basename(path).replace(".bntx", ".astc"))
    dump_astc(tex_data, out_astc)

    print("\nNow decode it with ASTCENC:")
    print(f"  astcenc -d {out_astc} {out_astc.replace('.astc', '.png')} 6x6\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_bntx_za.py <file.bntx>")
        sys.exit(1)
    main(sys.argv[1])
