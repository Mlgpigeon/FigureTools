import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageOps
import fbx

def mirror_and_save_image(file_path):
    with Image.open(file_path) as img:
        width, height = img.size

        # Mirror the image
        mirrored_img = ImageOps.mirror(img)

        # Create a new image with double the width
        new_image = Image.new('RGB', (width * 2, height))
        new_image.paste(img, (0, 0))
        new_image.paste(mirrored_img, (width, 0))

        # Save the modified image
        new_image.save(file_path.replace('.', '_mirrored.'))

def process_images(directory):
    for file in os.listdir(directory):
        if file.endswith(".png"):
            file_path = os.path.join(directory, file)
            mirror_and_save_image(file_path)

def process_directory(directory):
    for file in os.listdir(directory):
        full_path = os.path.join(directory, file)
        if file.endswith(".png"):
            mirror_and_save_image(full_path)

def select_directory():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    return folder_selected

directory = select_directory()
if directory:
    process_directory(directory)
else:
    print("No directory selected, exiting.")
