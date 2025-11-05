# dsspng.py
import os
import sys
import struct
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from PIL import Image, ImageOps
import math

# =======================
#  CONFIGURACIÓN
# =======================

# Si la Debug Console de VSCode no pilla tu PATH nuevo, descomenta y pon tu carpeta:
# os.environ["PATH"] = os.environ.get("PATH", "") + r";C:\Users\luism\Documents\LibreriasPath"

# Efecto "mirror" después de convertir (como tu script original).
DO_MIRROR = False

# Reconstruir canal Z en normales BC5 (más correcto):
RECONSTRUCT_BC5_NORMALS = True

# Heurística: considerar archivos normal map si el nombre contiene alguno de estos tokens
NORMAL_NAME_HINTS = ("_nrm", "_norm", "normal", "_nrml")

# Forzar sobrescritura si ya existe (texconv usa -y; aquí decidimos si saltar pasos de postproceso)
OVERWRITE_EXISTING = True

TEXCONV_EXE = Path(__file__).resolve().parent / "dependencies" / "texconv.exe"

# =======================
#  UTILIDADES DDS
# =======================

def detect_dds_format(dds_path: Path):
    """
    Lee cabecera DDS para detectar FourCC (DXT1/3/5, ATI1/ATI2, DX10...).
    Devuelve dict con {valid, fourCC, dx10(bool)}.
    """
    with open(dds_path, "rb") as f:
        data = f.read(148)  # 128 header + 20 DX10 opcional
    if data[:4] != b"DDS ":
        return {"valid": False}

    header = data[4:128]
    # DDS_PIXELFORMAT empieza en offset 72 del header (28 + 44)
    ddpf_off = 72
    pf = header[ddpf_off:ddpf_off+32]
    if len(pf) < 32:
        return {"valid": False}

    # pf_size, pf_flags, fourCC, rgbBitCount, rmask, gmask, bmask, amask
    fourCC = pf[8:12]
    fourCC_str = fourCC.decode("ascii", errors="ignore")
    info = {"valid": True, "fourCC": fourCC_str, "dx10": (fourCC_str == "DX10")}
    return info


def is_bc4(info: dict) -> bool:
    return info.get("valid") and info.get("fourCC") in ("ATI1", "BC4 ")


def is_bc5(info: dict) -> bool:
    return info.get("valid") and info.get("fourCC") in ("ATI2", "BC5 ")


def looks_like_normal_map(path: Path) -> bool:
    name = path.stem.lower()
    return any(h in name for h in NORMAL_NAME_HINTS)


# =======================
#  CONVERSIÓN TEXCONV
# =======================

def convert_with_texconv(dds_path: Path, out_png: Path, info: dict):
    """
    Llama a texconv para convertir DDS -> PNG.
    - BC4: fuerza R8_UNORM (grises).
    - BC5: fuerza RGBA y swizzle r,g,1,1 (si no vamos a reconstruir Z).
           Si reconstruimos Z, igualmente pedimos RGBA para tener R y G.
    - Otros: deja que texconv escoja (saldrá RGBA o RGB según corresponda).
    """
    out_dir = out_png.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [str(TEXCONV_EXE), "-ft", "png", "-y", "-o", str(out_dir)]

    if is_bc4(info):
        # A una textura BC4 (un canal): escala de grises 8-bit correcta
        cmd += ["-f", "R8_UNORM"]
    elif is_bc5(info):
        # PNG no acepta 2 canales RG. Pedimos RGBA y luego reconstruimos Z si toca.
        cmd += ["-f", "R8G8B8A8_UNORM"]
        if not RECONSTRUCT_BC5_NORMALS or not looks_like_normal_map(dds_path):
            # Si no vamos a reconstruir, al menos rellena B/A para visualizar sin error
            cmd += ["--swizzle", "r,g,1,1"]

    cmd += [str(dds_path)]
    subprocess.run(cmd, check=True, shell=False)

    # texconv genera <nombre>.png en out_dir; renombramos si hace falta
    generated = out_dir / (dds_path.stem + ".png")
    if generated.exists() and generated != out_png:
        # mover/renombrar a la ruta relativa preservando subcarpetas
        if out_png.exists() and not OVERWRITE_EXISTING:
            # mantener el existente
            pass
        else:
            # aseguramos carpeta
            out_png.parent.mkdir(parents=True, exist_ok=True)
            generated.replace(out_png)


# =======================
#  POSTPROCESO
# =======================
def looks_like_lightmap(path: Path) -> bool:
    return "_lym" in path.stem.lower()

def visualize_lightmap(png_path: Path):
    with Image.open(png_path) as img:
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        r, g, b, a = img.split()
        # R->Rojo, G->Verde (descarta B y A)
        out = Image.merge("RGB", (r, g, Image.new("L", img.size, 0)))
        out.save(png_path)

def reconstruct_normal_z_from_xy(png_path: Path):
    """
    Lee un PNG (esperado RGBA) donde R,G son normales XY en UNORM [0..255],
    reconstruye Z = sqrt(max(0, 1 - x^2 - y^2)) y guarda de nuevo con B=Z y A=255.
    """
    with Image.open(png_path) as img:
        # Asegurar RGBA
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        px = img.load()
        w, h = img.size

        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                # mapear a [-1, 1]
                nx = (r / 255.0) * 2.0 - 1.0
                ny = (g / 255.0) * 2.0 - 1.0
                nz_sq = 1.0 - nx * nx - ny * ny
                if nz_sq < 0.0:
                    nz = 0.0  # clamp si por redondeo sale negativo
                else:
                    nz = math.sqrt(nz_sq)
                # re-mapear a [0,255]
                bz = int(round((nz * 0.5 + 0.5) * 255.0))
                px[x, y] = (r, g, bz, 255)

        img.save(png_path)


def mirror_image(image_path: Path):
    with Image.open(image_path) as img:
        width, height = img.size
        if width % 2 != 0:
            img = img.crop((0, 0, width - 1, height))
            width -= 1
        left_half = img.crop((0, 0, width // 2, height))
        right_half = img.crop((width // 2, 0, width, height))
        left_half_mirrored = ImageOps.mirror(left_half)
        right_half_mirrored = ImageOps.mirror(right_half)

        new_image = Image.new('RGB', (width * 2, height))
        new_image.paste(left_half, (0, 0))
        new_image.paste(right_half_mirrored, (width // 2, 0))
        new_image.paste(right_half, (width, 0))
        new_image.paste(left_half_mirrored, (width + width // 2, 0))
        new_image.save(image_path)


# =======================
#  ORQUESTA
# =======================

def convert_dds_to_png(source_dir: Path, output_dir: Path, do_mirror=False):
    converted = 0
    failed = 0
    gray_bc4 = 0
    bc5_rgba = 0
    bc5_reconstructed = 0

    for root, _, files in os.walk(source_dir):
        root_p = Path(root)
        for file in files:
            if not file.lower().endswith(".dds"):
                continue

            dds_path = root_p / file
            rel = dds_path.relative_to(source_dir)
            out_png = output_dir / rel.with_suffix(".png")

            try:
                info = detect_dds_format(dds_path)

                convert_with_texconv(dds_path, out_png, info)

                if looks_like_lightmap(dds_path):
                    visualize_lightmap(out_png)
                # Postproceso BC5 (normales): reconstruir Z
                if RECONSTRUCT_BC5_NORMALS and is_bc5(info) and looks_like_normal_map(dds_path):
                    reconstruct_normal_z_from_xy(out_png)
                    bc5_reconstructed += 1
                elif is_bc5(info):
                    bc5_rgba += 1

                if is_bc4(info):
                    gray_bc4 += 1

                if do_mirror:
                    mirror_image(out_png)

                converted += 1

            except subprocess.CalledProcessError as e:
                print(f"[FAIL] {dds_path} -> {out_png}\n  Cmd error: {e}")
                failed += 1
            except Exception as e:
                print(f"[FAIL] {dds_path} -> {out_png}\n  {type(e).__name__}: {e}")
                failed += 1

    print("\n--- RESUMEN ---")
    print(f"Convertidos:          {converted}")
    print(f"Fallidos:             {failed}")
    print(f"BC4 a grises:         {gray_bc4}")
    print(f"BC5 RGBA (sin Z):     {bc5_rgba}")
    print(f"BC5 con Z reconstru.: {bc5_reconstructed}")
    if failed == 0:
        print("OK. Deberías tener todas las texturas convertidas en 'output'.")


# =======================
#  UI selección carpeta
# =======================

def select_directory():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    return Path(folder_selected) if folder_selected else None


# --- CLI para uso externo ---
if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Convertir DDS a PNG (vía texconv) con opciones de mirroring.")
    parser.add_argument("--src", required=True, help="Carpeta de entrada con .dds")
    parser.add_argument("--out", default="", help="Carpeta de salida (por defecto: <src>/output)")
    parser.add_argument("--no-mirror", action="store_true", help="Desactiva el mirroring")
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(args.out) if args.out else src / "output"

    # Si tienes una constante DO_MIRROR en el módulo, úsala como valor por defecto
    try:
        do_mirror_default = DO_MIRROR  # si existe
    except NameError:
        do_mirror_default = True       # o el valor por defecto que uses

    do_mirror = not args.no_mirror if args.no_mirror else do_mirror_default

    # Ejecuta
    convert_dds_to_png(src, out, do_mirror=do_mirror)

