import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageOps
import fbx

def convert_dae_to_fbx(dae_filename, fbx_filename):
    # Create an SDK manager
    sdk_manager = fbx.FbxManager.Create()
    
    # Create an IO settings object
    ios = fbx.FbxIOSettings.Create(sdk_manager, fbx.IOSROOT)
    sdk_manager.SetIOSettings(ios)
    
    # Create an importer using the SDK manager
    importer = fbx.FbxImporter.Create(sdk_manager, "")
    
    # Use the importer to load the DAE file
    if not importer.Initialize(dae_filename, -1, sdk_manager.GetIOSettings()):
        print(f"Failed to initialize importer for {dae_filename}")
        return

    # Create a new scene so that it can be populated by the imported file
    scene = fbx.FbxScene.Create(sdk_manager, "MyScene")
    
    # Import the contents of the file into the scene
    importer.Import(scene)
    
    # The file is imported, so get rid of the importer
    importer.Destroy()
    
    # Create an exporter
    exporter = fbx.FbxExporter.Create(sdk_manager, "")
    
    # Initialize the exporter
    if not exporter.Initialize(fbx_filename, -1, sdk_manager.GetIOSettings()):
        print(f"Failed to initialize exporter for {fbx_filename}")
        return
    
    # Export the scene to an FBX file
    exporter.Export(scene)
    
    # Clean up
    exporter.Destroy()
    sdk_manager.Destroy()

def mirror_image(image_path, output_path):
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
        new_image.save(output_path)

def mirror_image_double(image_path, output_path):
    with Image.open(image_path) as img:
        width, height = img.size

        # Mirror the image
        mirrored_img = ImageOps.mirror(img)

        # Create a new image with double the width
        new_image = Image.new('RGB', (width * 2, height))
        new_image.paste(img, (0, 0))
        new_image.paste(mirrored_img, (width, 0))

        # Save the modified image
        new_image.save(output_path)

def process_directory(directory):
    trans_dir = os.path.join(directory, 'trans')
    os.makedirs(trans_dir, exist_ok=True)
    
    for file in os.listdir(directory):
        full_path = os.path.join(directory, file)
        if file.endswith(".dae"):
            fbx_path = os.path.join(trans_dir, file.replace('.dae', '.fbx'))
            convert_dae_to_fbx(full_path, fbx_path)
            print(f"Converted '{full_path}' to '{fbx_path}'")
        elif file.endswith(".png"):
            mirrored_path = os.path.join(trans_dir, file.replace('.png', '_mirrored2.png'))
            mirrored_double_path = os.path.join(trans_dir, file.replace('.png', '_mirrored.png'))
            mirror_image(full_path, mirrored_path)
            mirror_image_double(full_path, mirrored_double_path)
            print(f"Mirrored: {file}")

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
