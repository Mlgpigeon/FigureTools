import bpy
from bpy.props import BoolProperty, StringProperty
import os
from .importers import ensure_node_group
from .sv_eye_bake_operator import (
    OBJECT_OT_generate_sv_eye_material,
    OBJECT_OT_bake_eye_texture,
)


class OBJECT_OT_rename_uvmaps(bpy.types.Operator):
    """Rename UV maps of selected objects to the same name"""
    bl_idname = "figure_tools.rename_uvmaps"
    bl_label = "Rename UV Maps"
    bl_options = {'REGISTER', 'UNDO'}
    
    new_name: bpy.props.StringProperty(
        name="New Name",
        description="New name for all UV maps",
        default="UVMap"
    )
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects and any(obj.type == 'MESH' for obj in context.selected_objects)
    
    def execute(self, context):
        renamed_count = 0
        skipped_count = 0
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if obj.data.uv_layers:
                    for uv_layer in obj.data.uv_layers:
                        if uv_layer.name != self.new_name:
                            uv_layer.name = self.new_name
                            renamed_count += 1
                else:
                    skipped_count += 1
        
        if renamed_count > 0:
            self.report({'INFO'}, f"Renamed {renamed_count} UV map(s). Skipped {skipped_count} objects without UV maps.")
        else:
            self.report({'WARNING'}, f"No UV maps renamed. Skipped {skipped_count} objects without UV maps.")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class OBJECT_OT_add_volumifier(bpy.types.Operator):
    """Add Volumifier Node Modifier"""
    bl_idname = "object.add_volumifier"
    bl_label = "Add Volumifier"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object selected.")
            return {'CANCELLED'}

        ensure_node_group("Volumifier")

        # Add Volumifier as a Geometry Nodes modifier
        mod = obj.modifiers.new(name="Volumifier", type='NODES')
        mod.node_group = bpy.data.node_groups["Volumifier"]

        self.report({'INFO'}, "Volumifier added successfully.")
        return {'FINISHED'}

class OBJECT_OT_add_solidifier(bpy.types.Operator):
    """Add Solidifier Node Modifier"""
    bl_idname = "object.add_solidifier"
    bl_label = "Add Solidifier"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object selected.")
            return {'CANCELLED'}

        ensure_node_group("Solidifier")

        # Add Solidifier as a Geometry Nodes modifier
        mod = obj.modifiers.new(name="Solidifier", type='NODES')
        mod.node_group = bpy.data.node_groups["Solidifier"]

        self.report({'INFO'}, "Solidifier added successfully.")
        return {'FINISHED'}

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
    use_regular_upscale_x2: BoolProperty(
        name="Regular Upscale ×2",
        description="Apply regular upscaling at 2× via Real-ESRGAN-ncnn-vulkan",
        default=False
    )
    
    use_anime_upscale: BoolProperty(
        name="Anime Upscale",
        description="Apply anime-optimized upscaling to images",
        default=False
    )

    use_anime_upscale_x2: BoolProperty(
        name="Anime Upscale ×2",
        description="Apply anime-optimized upscaling at 2× via Real-ESRGAN-ncnn-vulkan",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        # Add checkboxes
        layout.prop(self, "use_regular_upscale")
        layout.prop(self, "use_anime_upscale")
        layout.prop(self, "use_regular_upscale_x2")
        layout.prop(self, "use_anime_upscale_x2")
    
    def execute(self, context):
        from . import upscale_operator
        
        options = {
            'regular_upscale':       self.use_regular_upscale,
            'regular_upscale_x2':    self.use_regular_upscale_x2,
            'anime_upscale':         self.use_anime_upscale,
            'anime_upscale_x2':      self.use_anime_upscale_x2
        }
        
        from . import thresholdpng
        thresholdpng.process_images(self.directory,options)
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Open the file browser
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def on_figure_toggle(self, context):
    obj = context.active_object
    if not obj.is_figure:
        # Remove Dynamic_Displacement modifier when figure is toggled off
        for mod in obj.modifiers:
            if mod.name.startswith("Dynamic_Displacement"):
                obj.modifiers.remove(mod)

class VIEW3D_PT_upscale_tools(bpy.types.Panel):
    """Creates a Panel in the N menu for upscaling tools"""
    bl_label = "Figure Tools"
    bl_idname = "VIEW3D_PT_figure_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Figures'  # This creates the new tab
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        if obj:
            # Is Figure toggle
            layout.prop(obj, "is_figure", text="Is Figure")
            
            # Process Images button
            layout.operator("figure_tools.process_images", text="Process Images")
            
            # UV Map renaming
            layout.operator("figure_tools.rename_uvmaps", text="Rename UV Maps")

            layout.operator("object.add_volumifier", text="Volumifier")
            
            # Add the new Solidifier button
            layout.operator("object.add_solidifier", text="Solidifier")
            
            layout.operator("figure_tools.generate_sv_eye_material", text="Generate SV Eye Material")
            layout.operator("figure_tools.bake_eye_texture", text="Bake Eye To PNG")



# List of classes for registration
classes = [
    OBJECT_OT_rename_uvmaps,
    OBJECT_OT_process_images,
    VIEW3D_PT_upscale_tools,
    OBJECT_OT_add_volumifier,
    OBJECT_OT_add_solidifier,
    OBJECT_OT_generate_sv_eye_material,
    OBJECT_OT_bake_eye_texture,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register is_figure property
    bpy.types.Object.is_figure = bpy.props.BoolProperty(
        name="Is Figure",
        description="Mark this object as a figure",
        default=False,
        update=on_figure_toggle
    )

def unregister():
    # Unregister is_figure property
    del bpy.types.Object.is_figure
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()