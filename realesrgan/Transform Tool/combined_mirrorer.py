import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps
import fbx  # Asegúrate de tener `fbx` instalado y accesible

selected_folder = None  # Ruta global
def run_dds_to_png_external(status_label):
    if not selected_folder:
        messagebox.showwarning("No folder selected", "Please select a folder first.")
        return

    status_label.config(text="Converting DDS to PNG (externo)...")
    root.update_idletasks()

    # Asumimos que dsspng.py está junto a combined_mirrorer.py.
    dss_script = Path(__file__).with_name("dsspng.py")
    if not dss_script.exists():
        messagebox.showerror("Error", f"No encuentro {dss_script.name} junto a este script.")
        status_label.config(text="DDS->PNG failed")
        return

    out_dir = Path(selected_folder) / "output"
    cmd = [sys.executable, str(dss_script), "--src", selected_folder, "--out", str(out_dir)]
    try:
        completed = subprocess.run(cmd, text=True, check=True)
        # Puedes inspeccionar completed.stdout / completed.stderr si te interesa
        messagebox.showinfo("DDS -> PNG", f"Conversión completada.\nSalida: {out_dir}")
        status_label.config(text=f"DDS->PNG OK: {out_dir}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror(
            "Error",
            f"DDS->PNG falló (código {e.returncode}).\n\nSTDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}"
        )
        status_label.config(text="DDS->PNG failed")

def _find_quickbms():
    base = Path(__file__).resolve().parent / "quickbms"
    candidates = [
        base / "quickbms.exe",           # Windows
        base / "quickbms_4gb_files.exe", # Windows 4GB
        base / "quickbms",               # Linux/macOS
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

def _get_switch_bntx_script():
    return Path(__file__).resolve().parent / "quickbms" / "scripts" / "Switch_BNTX.bms"

def run_switch_bntx(status_label):
    if not selected_folder:
        messagebox.showwarning("No folder selected", "Please select a folder first.")
        return

    qbms = _find_quickbms()
    if qbms is None:
        messagebox.showerror("Error", "No encuentro quickbms en ./quickbms")
        return

    script = _get_switch_bntx_script()
    if not script.exists():
        messagebox.showerror("Error", "No encuentro ./quickbms/scripts/Switch_BNTX.bms")
        return

    input_dir = Path(selected_folder)
    out_dir = input_dir / "textures"
    out_dir.mkdir(parents=True, exist_ok=True)

    status_label.config(text="Extrayendo BNTX (Scarlet/Violet)…")
    root.update_idletasks()

    cmd = [str(qbms), str(script), str(input_dir), str(out_dir)]
    try:
        completed = subprocess.run(cmd,  text=True, check=True)

        # --- NUEVO: aplanar estructura ---
        status_label.config(text="Aplanando textures/…")
        root.update_idletasks()
        moved, collisions, deleted_dirs = flatten_dds_in_textures(out_dir)

        messagebox.showinfo(
            "Switch_BNTX",
            f"Extracción completada.\n"
            f"Aplanado: movidos {moved} .dds (colisiones renombradas: {collisions}).\n"
            f"Carpetas eliminadas: {deleted_dirs}\n"
            f"Salida: {out_dir}"
        )
        status_label.config(text=f"Switch_BNTX: OK → {out_dir} | movidos {moved}, colisiones {collisions}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror(
            "Error",
            f"Falló la extracción (código {e.returncode}).\n\nSTDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}"
        )
        status_label.config(text="Switch_BNTX: ERROR")


def flatten_dds_in_textures(textures_dir: Path):
    """
    Mueve todos los .dds desde subcarpetas de `textures_dir` a la raíz `textures_dir`.
    Si existe un archivo con el mismo nombre, crea nombre__N.dds.
    Luego intenta borrar las subcarpetas vacías.
    Devuelve (moved_count, collision_count, deleted_dirs).
    """
    textures_dir = Path(textures_dir).resolve()
    moved = 0
    collisions = 0

    # Mover todos los .dds que NO estén ya en la raíz
    for dds_path in textures_dir.rglob("*.dds"):
        if dds_path.parent == textures_dir:
            continue  # ya está en la raíz
        target = textures_dir / dds_path.name
        if target.exists():
            stem, suffix = target.stem, target.suffix
            i = 1
            while True:
                candidate = textures_dir / f"{stem}__{i}{suffix}"
                if not candidate.exists():
                    target = candidate
                    collisions += 1
                    break
                i += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dds_path), str(target))
        moved += 1

    # Borrar directorios vacíos (bottom-up)
    deleted_dirs = 0
    # Ordenar por profundidad inversa para intentar borrar de abajo hacia arriba
    dirs = sorted(
        (p for p in textures_dir.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True
    )
    for d in dirs:
        try:
            d.rmdir()
            deleted_dirs += 1
        except OSError:
            # No está vacío (o permisos), lo dejamos
            pass

    return moved, collisions, deleted_dirs
# ---------- FUNCIONES DE MIRROR ----------
def mirror_method_1(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            left_half = img.crop((0, 0, width // 2, height))
            right_half = img.crop((width // 2, 0, width, height))
            left_half_mirrored = ImageOps.mirror(left_half)
            right_half_mirrored = ImageOps.mirror(right_half)
            new_image = Image.new('RGB', (width * 2, height))
            new_image.paste(left_half_mirrored, (0, 0))
            new_image.paste(left_half, (width // 2, 0))
            new_image.paste(right_half, (width, 0))
            new_image.paste(right_half_mirrored, (width + width // 2, 0))
            output_path = image_path.replace('.', '_mirrored_method1.')
            new_image.save(output_path)
    except Exception as e:
        raise Exception(f"Method 1 failed: {e}")

def mirror_method_2(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            mirrored_img = ImageOps.mirror(img)
            new_image = Image.new('RGB', (width * 2, height))
            new_image.paste(img, (0, 0))
            new_image.paste(mirrored_img, (width, 0))
            output_path = image_path.replace('.', '_mirrored_method2.')
            new_image.save(output_path)
    except Exception as e:
        raise Exception(f"Method 2 failed: {e}")

def is_image_file(filename):
    return any(filename.lower().endswith(ext) for ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'})

def delete_mirrored_images(status_label):
    if not selected_folder:
        messagebox.showwarning("No folder selected", "Please select a folder first.")
        return

    deleted = 0
    for filename in os.listdir(selected_folder):
        if '_mirrored_method1' in filename or '_mirrored_method2' in filename:
            file_path = os.path.join(selected_folder, filename)
            try:
                os.remove(file_path)
                deleted += 1
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
    messagebox.showinfo("Delete Complete", f"Deleted {deleted} mirrored images.")
    status_label.config(text=f"Deleted {deleted} mirrored images")

def process_images(directory, status_label):
    processed = 0
    failed = 0
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if (not os.path.isfile(file_path)
                or not is_image_file(filename)
                or '_mirrored_method1' in filename
                or '_mirrored_method2' in filename):
            continue
        try:
            mirror_method_1(file_path)
            mirror_method_2(file_path)
            processed += 1
        except Exception as e:
            print(f"Error: {e}")
            failed += 1
    messagebox.showinfo("Done", f"Processed: {processed} images\nFailed: {failed}")
    status_label.config(text=f"Processed: {processed}, Failed: {failed}")

# ---------- FUNCIONES DAE to FBX ----------
def convert_dae_to_fbx(dae_filename, fbx_filename):
    sdk_manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(sdk_manager, fbx.IOSROOT)
    sdk_manager.SetIOSettings(ios)

    importer = fbx.FbxImporter.Create(sdk_manager, "")
    if not importer.Initialize(dae_filename, -1, sdk_manager.GetIOSettings()):
        print(f"Failed to import {dae_filename}")
        return
    scene = fbx.FbxScene.Create(sdk_manager, "MyScene")
    importer.Import(scene)
    importer.Destroy()

    exporter = fbx.FbxExporter.Create(sdk_manager, "")
    if not exporter.Initialize(fbx_filename, -1, sdk_manager.GetIOSettings()):
        print(f"Failed to export {fbx_filename}")
        return
    exporter.Export(scene)
    exporter.Destroy()
    sdk_manager.Destroy()

def process_dae_files(directory, status_label):
    processed = 0
    for file in os.listdir(directory):
        if file.lower().endswith(".dae"):
            full_path = os.path.join(directory, file)
            fbx_path = full_path.replace('.dae', '.fbx')
            try:
                convert_dae_to_fbx(full_path, fbx_path)
                processed += 1
            except Exception as e:
                print(f"Failed: {e}")
    messagebox.showinfo("Done", f"Converted {processed} .dae files to .fbx")
    status_label.config(text=f"DAE to FBX: {processed} converted")

# ---------- FUNCIONES GENERALES ----------
def select_folder(folder_label):
    global selected_folder
    folder = filedialog.askdirectory(title="Select folder with images and/or .dae files")
    if folder:
        selected_folder = folder
        folder_label.config(text=f"Folder: {folder}")
    else:
        folder_label.config(text="No folder selected")

def run_mirror(status_label):
    if selected_folder:
        status_label.config(text="Processing images...")
        root.update_idletasks()
        process_images(selected_folder, status_label)
    else:
        messagebox.showwarning("No folder selected", "Please select a folder first.")

def run_dae_to_fbx(status_label):
    if selected_folder:
        status_label.config(text="Converting DAE to FBX...")
        root.update_idletasks()
        process_dae_files(selected_folder, status_label)
    else:
        messagebox.showwarning("No folder selected", "Please select a folder first.")

# ---------- GUI ----------
root = tk.Tk()
root.title("Image Mirrorer and DAE to FBX Converter")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

tk.Label(frame, text="Select a folder to process:", font=("Arial", 14)).pack(pady=10)

folder_label = tk.Label(frame, text="No folder selected", font=("Arial", 10))
folder_label.pack()

select_button = tk.Button(frame, text="Select Folder", font=("Arial", 12),
                          command=lambda: select_folder(folder_label))
select_button.pack(pady=(10, 5))

mirror_button = tk.Button(frame, text="Mirror", font=("Arial", 12),
                          command=lambda: run_mirror(status_label))
mirror_button.pack(pady=5)

delete_button = tk.Button(frame, text="Delete Mirror", font=("Arial", 12),
                          command=lambda: delete_mirrored_images(status_label))
delete_button.pack(pady=5)

dae_to_fbx_button = tk.Button(frame, text="Dae to FBX", font=("Arial", 12),
                              command=lambda: run_dae_to_fbx(status_label))
dae_to_fbx_button.pack(pady=5)

switch_bntx_button = tk.Button(
    frame, text="Switch_BNTX", font=("Arial", 12),
    command=lambda: run_switch_bntx(status_label)
)
switch_bntx_button.pack(pady=5)


dds_png_button_ext = tk.Button(
    frame, text="DDS to PNG", font=("Arial", 12),
    command=lambda: run_dds_to_png_external(status_label)
)
dds_png_button_ext.pack(pady=5)

status_label = tk.Label(frame, text="Idle", font=("Arial", 10))
status_label.pack(pady=(10, 0))

root.mainloop()
