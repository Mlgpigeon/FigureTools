import os
from os import listdir
from os.path import isfile, join, dirname

def process_anime_upscale(files_list, input_dir):
    """
    Process images using anime-optimized upscaling.
    
    Args:
        files_list (list): List of files to process
        input_dir (str): Input directory path
    """
    # Get the path to the realesrgan folder where the exe is located
    realesrgan_dir = os.path.join(dirname(__file__))
    exe_path = os.path.join(realesrgan_dir, "realesrgan-ncnn-vulkan.exe")
    
    for f in files_list:
        file_extension = os.path.splitext(f)[1]
        file_name = f[:-(len(file_extension))]
        
        if file_extension.lower() in ['.jpg', '.png']:
            input_path = os.path.join(input_dir, f).replace('\\', '/')
            output_path = os.path.join(input_dir, f"{file_name}.png").replace('\\', '/')
            exe_path = exe_path.replace('\\', '/')
            
            command = f'"{exe_path}" -n realesrgan-x4plus-anime -i "{input_path}" -o "{output_path}"'
            print(f"Executing command: {command}")
            os.system(f'cd "{os.path.dirname(exe_path)}" && {command}')

def process_regular_upscale(files_list, input_dir):
    """
    Process images using standard upscaling.
    
    Args:
        files_list (list): List of files to process
        input_dir (str): Input directory path
    """
    # Get the path to the realesrgan folder where the exe is located
    realesrgan_dir = os.path.join(dirname(__file__))
    exe_path = os.path.join(realesrgan_dir, "realesrgan-ncnn-vulkan.exe")
    
    for f in files_list:
        file_extension = os.path.splitext(f)[1]
        file_name = f[:-(len(file_extension))]
        
        if file_extension.lower() in ['.jpg', '.png']:
            input_path = os.path.join(input_dir, f).replace('\\', '/')
            output_path = os.path.join(input_dir, f"{file_name}.png").replace('\\', '/')
            exe_path = exe_path.replace('\\', '/')
            
            command = f'"{exe_path}" -i "{input_path}" -o "{output_path}"'
            print(f"Executing command: {command}")
            os.system(f'cd "{os.path.dirname(exe_path)}" && {command}')

def process_regular_upscale_x2(files_list, input_dir):
    """
    Process images using standard upscaling at 2× via Real-ESRGAN‑ncnn‑vulkan.
    """
    realesrgan_dir = os.path.join(dirname(__file__))
    exe_path = os.path.join(realesrgan_dir, "realesrgan-ncnn-vulkan.exe").replace('\\', '/')
    
    for f in files_list:
        ext = os.path.splitext(f)[1].lower()
        if ext in ['.jpg', '.png']:
            inp  = os.path.join(input_dir, f).replace('\\', '/')
            name = os.path.splitext(f)[0]
            outp = os.path.join(input_dir, f"{name}.png").replace('\\', '/')
            
            cmd = f'"{exe_path}" -i "{inp}" -o "{outp}" -s 2'
            print(f"Executing ×2 regular: {cmd}")
            os.system(f'cd "{os.path.dirname(exe_path)}" && {cmd}')

def process_anime_upscale_x2(files_list, input_dir):
    """
    Process images using anime-optimized upscaling at 2× via Real-ESRGAN‑ncnn‑vulkan.
    """
    realesrgan_dir = os.path.join(dirname(__file__))
    exe_path = os.path.join(realesrgan_dir, "realesrgan-ncnn-vulkan.exe").replace('\\', '/')
    
    for f in files_list:
        ext = os.path.splitext(f)[1].lower()
        if ext in ['.jpg', '.png']:
            inp  = os.path.join(input_dir, f).replace('\\', '/')
            name = os.path.splitext(f)[0]
            outp = os.path.join(input_dir, f"{name}.png").replace('\\', '/')
            
            cmd = f'"{exe_path}" -n realesr-animevideov3-x2 -s 2 -i "{inp}" -o "{outp}" '
            print(f"Executing ×2 anime: {cmd}")
            os.system(f'cd "{os.path.dirname(exe_path)}" && {cmd}')