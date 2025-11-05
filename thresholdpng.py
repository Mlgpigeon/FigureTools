from PIL import Image
import os
import numpy as np
import subprocess
from .realesrgan.methods import process_anime_upscale, process_regular_upscale,process_anime_upscale_x2, process_regular_upscale_x2

def threshold_alpha(image, threshold=0):
    """
    Apply threshold to alpha channel, similar to GIMP's threshold alpha
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
        
    img_array = np.array(image)
    alpha = img_array[:, :, 3]
    img_array[:, :, 3] = np.where(alpha > threshold, 255, 0)
        
    return Image.fromarray(img_array, 'RGBA')

def process_images(folder_path, options):
    """
    Process images in the selected folder based on chosen options
    
    Args:
        folder_path (str): Path to the folder containing images
        options (dict): Dictionary containing processing options
            - regular_upscale (bool): Whether to apply regular upscaling
            - anime_upscale (bool): Whether to apply anime upscaling
    """
    if not folder_path:
        print("No folder selected")
        return
        
    # Get list of files
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg'))]
    
    # First process alpha channels for PNG files
    for filename in files:
        if filename.lower().endswith('.png'):
            filepath = os.path.join(folder_path, filename)
            
            try:
                with Image.open(filepath) as img:
                    processed = threshold_alpha(img, threshold=0)
                    processed.save(filepath, 'PNG', optimize=True)
                print(f"Alpha threshold processed: {filename}")
            except Exception as e:
                print(f"Error processing alpha for {filename}: {str(e)}")
    
    # Process upscaling in order (regular must be first)
    if options['regular_upscale']:
        process_regular_upscale(files, folder_path)
        
    if options['anime_upscale']:
        process_anime_upscale(files, folder_path)

    if options.get('regular_upscale_x2'):
        process_regular_upscale_x2(files, folder_path)

    if options.get('anime_upscale_x2'):
        process_anime_upscale_x2(files, folder_path)

    print("Processing complete!")