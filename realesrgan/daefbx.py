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

def process_directory(directory):
    for file in os.listdir(directory):
        full_path = os.path.join(directory, file)
        if file.endswith(".dae"):
            fbx_path = full_path.replace('.dae', '.fbx')
            convert_dae_to_fbx(full_path, fbx_path)
            print(f"Converted '{full_path}' to '{fbx_path}'")

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