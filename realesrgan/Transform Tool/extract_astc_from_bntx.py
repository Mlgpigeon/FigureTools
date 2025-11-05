import struct, sys, os

# CONFIGURACIÓN
OFFSET_START = 0x0000FF10      # Inicio real de datos ASTC tras "BRTD"
BLOCK_W, BLOCK_H, BLOCK_D = 6, 6, 1
WIDTH, HEIGHT, DEPTH = 512, 1024, 1


def main(path):
    with open(path, "rb") as f:
        data = f.read()

    tex_data = data[OFFSET_START:]
    print(f"[*] Extrayendo {len(tex_data)} bytes desde offset 0x{OFFSET_START:X}")

    # Cabecera ASTC estándar de 16 bytes
    header = struct.pack(
        "<4s3B9B",
        b"\x13\xAB\xA1\x5C",
        BLOCK_W, BLOCK_H, BLOCK_D,
        WIDTH & 0xFF, (WIDTH >> 8) & 0xFF, (WIDTH >> 16) & 0xFF,
        HEIGHT & 0xFF, (HEIGHT >> 8) & 0xFF, (HEIGHT >> 16) & 0xFF,
        DEPTH & 0xFF, (DEPTH >> 8) & 0xFF, (DEPTH >> 16) & 0xFF
    )

    out_path = path.replace(".bntx", f"_{WIDTH}x{HEIGHT}_final.astc")
    with open(out_path, "wb") as f:
        f.write(header + tex_data)

    print(f"[+] ASTC válido creado: {out_path}")
    print("Ahora decodifícalo con:")
    print(f'  astcenc -ds "{out_path}" "{out_path.replace(".astc", ".png")}"')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python extract_astc_from_bntx.py <archivo.bntx>")
        sys.exit(1)
    main(sys.argv[1])
