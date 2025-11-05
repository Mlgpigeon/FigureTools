import struct, sys, os

# Datos exactos conocidos
BLOCK_W, BLOCK_H, BLOCK_D = 8, 8, 1     # prueba 6x6 si 8x8 no da color
WIDTH, HEIGHT, DEPTH = 512, 1024, 1

def main(path):
    with open(path, "rb") as f:
        data = f.read()

    # Cabecera ASTC 16 bytes (4 + 3 + 9)
    header = struct.pack(
        "<4s3B9B",
        b"\x13\xAB\xA1\x5C",          # Magic
        BLOCK_W, BLOCK_H, BLOCK_D,   # Tamaño de bloque
        WIDTH & 0xFF, (WIDTH >> 8) & 0xFF, (WIDTH >> 16) & 0xFF,
        HEIGHT & 0xFF, (HEIGHT >> 8) & 0xFF, (HEIGHT >> 16) & 0xFF,
        DEPTH & 0xFF, (DEPTH >> 8) & 0xFF, (DEPTH >> 16) & 0xFF
    )

    out_path = path.replace(".astc", f"_{WIDTH}x{HEIGHT}_header.astc")
    with open(out_path, "wb") as f:
        f.write(header + data)

    print(f"[+] Header injected → {out_path}")
    print(f"Now decode it with:")
    print(f'  astcenc -ds "{out_path}" "{out_path.replace(".astc", ".png")}"')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_astc_header.py <file.astc>")
        sys.exit(1)
    main(sys.argv[1])
