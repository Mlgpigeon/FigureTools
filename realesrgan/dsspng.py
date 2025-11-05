import os
import subprocess
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageOps

def mirror_image(image_path):
    with Image.open(image_path) as img:
        width, height = img.size

        # Crop the left and right halves
        left_half = img.crop((0, 0, width // 2, height))
        right_half = img.crop((width // 2, 0, width, height))

        # Mirror the halves
        left_half_mirrored = ImageOps.mirror(left_half)
        right_half_mirrored = ImageOps.mirror(right_half)

        # Create a new image with double the width
        new_image = Image.new('RGB', (width * 2, height))
        new_image.paste(left_half, (0, 0))
        new_image.paste(right_half_mirrored, (width // 2, 0))
        new_image.paste(right_half, (width, 0))
        new_image.paste(left_half_mirrored, (width + width // 2, 0))

        # Save the modified image
        new_image.save(image_path)

def convert_dds_to_png(source_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".dds"):
                dds_path = os.path.join(root, file)
                png_path = os.path.join(output_dir, os.path.splitext(file)[0] + '.png')

                # Convert using ImageMagick
                command = f"magick convert \"{dds_path}\" \"{png_path}\""
                try:
                    subprocess.run(command, check=True, shell=True)
                    #mirror_image(png_path)
                     # print(f"Converted and mirrored: {dds_path} to {png_path}")
                except subprocess.CalledProcessError as e:
                    print(f"Failed to convert {dds_path}: {e}")

def select_directory():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    return folder_selected

source_directory = select_directory()
if source_directory:
    output_directory = os.path.join(source_directory, "output")
    convert_dds_to_png(source_directory, output_directory)
else:
    print("No directory selected, exiting.")
