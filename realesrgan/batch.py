import os
from os import listdir
from os.path import isfile, join

current = os.getcwd() + "/images"
print(current)

onlyfiles = [f for f in listdir(current) if isfile(join(current, f))]
print(onlyfiles)
'''
'''
# Anime version

for f in onlyfiles:
    file_extension = os.path.splitext(f)[1]
    file_name = f[:-(len(file_extension))]
    
    if file_extension.lower() in ['.jpg', '.png']:
        print(file_name)
        print(file_extension)
        directories = os.system(f'realesrgan-ncnn-vulkan.exe -n realesrgan-x4plus-anime -i ./images/{f} -o ./images/{file_name}.png')

for f in onlyfiles:
    # Get the last extension only
    file_extension = os.path.splitext(f)[1]
    # Get everything except the last extension
    file_name = f[:-(len(file_extension))]
    
    if file_extension.lower() in ['.jpg', '.png']:
        print(file_name)
        print(file_extension)
        directories = os.system(f'realesrgan-ncnn-vulkan.exe -i ./images/{f} -o ./images/{file_name}.png')
