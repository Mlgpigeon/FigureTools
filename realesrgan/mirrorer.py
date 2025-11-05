import os
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
        new_image.paste(left_half_mirrored, (0, 0))
        new_image.paste(left_half, (width // 2, 0))
        new_image.paste(right_half, (width, 0))
        new_image.paste(right_half_mirrored, (width + width // 2, 0))

        # Save the modified image
        new_image.save(image_path.replace('.', '_mirrored2.'))

def process_images(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            try:
                mirror_image(file_path)
                print(f"Mirrored: {filename}")
            except Exception as e:
                print(f"Failed to mirror {filename}: {e}")

def select_directory():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    return folder_selected

source_directory = select_directory()
if source_directory:
    process_images(source_directory)
else:
    print("No directory selected, exiting.")
