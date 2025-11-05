import bpy
from bpy.props import BoolProperty, StringProperty
import os

class OBJECT_OT_process_images(bpy.types.Operator):
    bl_idname = "figure_tools.process_images"
    bl_label = "Process Images"
    bl_description = "Process images with selected upscaling methods"
    
    # File path property
    directory: StringProperty(
        name="Directory",
        description="Choose a directory",
        subtype='DIR_PATH'
    )
    
    # Checkbox properties
    use_regular_upscale: BoolProperty(
        name="Regular Upscale",
        description="Apply regular upscaling to images",
        default=False
    )
    
    use_anime_upscale: BoolProperty(
        name="Anime Upscale",
        description="Apply anime-optimized upscaling to images",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        # Add checkboxes
        layout.prop(self, "use_regular_upscale")
        layout.prop(self, "use_anime_upscale")
    
    def execute(self, context):
        # Import the processing script
        from . import image_processor
        
        # Create processing options dictionary
        options = {
            'regular_upscale': self.use_regular_upscale,
            'anime_upscale': self.use_anime_upscale
        }
        
        # Call the processing function
        image_processor.process_images(self.directory, options)
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Open the file browser
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class VIEW3D_PT_upscale_tools(bpy.types.Panel):
    """Creates a Panel in the N menu for upscaling tools"""
    bl_label = "Upscale Tools"
    bl_idname = "VIEW3D_PT_upscale_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Upscale'  # This creates the new tab
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        if obj:
            # Process Images button
            layout.operator("figure_tools.process_images", text="Process Images")

# List of classes for registration
classes = [
    OBJECT_OT_process_images,
    VIEW3D_PT_upscale_tools,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()