import bpy
import os
import re
import glob
from bpy.props import StringProperty, FloatProperty, BoolProperty, IntProperty
from bpy_extras.io_utils import ImportHelper

class OBJECT_OT_generate_sv_eye_material(bpy.types.Operator, ImportHelper):
    bl_idname = "figure_tools.generate_sv_eye_material"
    bl_label = "Generate SV Eye Material"
    bl_description = "Generate material from eye layers for preview and editing"
    filename_ext = ""
    use_filter_folder = True
    filter_folder = True

    directory: StringProperty(subtype='DIR_PATH')
    emission_strength: FloatProperty(
        name="Emission Strength",
        description="Brightness of the emission shader",
        default=1.0,
        min=0.0,
        max=10.0
    )
    use_diffuse_shader: BoolProperty(
        name="Use Diffuse Shader",
        description="Use Diffuse BSDF instead of Emission for better baking results",
        default=True
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "emission_strength")
        layout.prop(self, "use_diffuse_shader")

    def execute(self, context):
        folder = self.directory
        if not os.path.isdir(folder):
            self.report({'ERROR'}, "Invalid folder selected.")
            return {'CANCELLED'}

        # Debug: Print all files in the directory
        self.report({'INFO'}, f"Looking for eye layers in: {folder}")
        all_files = os.listdir(folder)
        for file in all_files:
            self.report({'INFO'}, f"Found file: {file}")

        # Find all layer files
        layer_files = []
        for f in all_files:
            if "eye" in f.lower() and f.endswith(".png"):
                layer_files.append((len(layer_files), f))
        
        # Sort by layer index
        layer_files.sort(key=lambda x: x[0])
        self.report({'INFO'}, f"Found layer files: {layer_files}")
        
        if not layer_files:
            self.report({'ERROR'}, "No eye layer files found.")
            return {'CANCELLED'}

        # Find mask file
        mask_files = []
        for f in all_files:
            if "eye" in f.lower() and ("msk" in f.lower() or "mask" in f.lower()) and f.endswith(".png"):
                mask_files.append(f)
        
        self.report({'INFO'}, f"Found mask files: {mask_files}")
        
        # Create the plane and material
        bpy.ops.mesh.primitive_plane_add(size=1)
        plane = bpy.context.active_object
        plane.name = "EyePreviewPlane"

        mat = bpy.data.materials.new(name="EyePreviewMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()
        output_node = nodes.new(type="ShaderNodeOutputMaterial")
        output_node.location = (300, 0)
        
        # Choose between Emission and Diffuse shader
        if self.use_diffuse_shader:
            shader = nodes.new(type="ShaderNodeBsdfDiffuse")
            shader.location = (100, 0)
            links.new(shader.outputs['BSDF'], output_node.inputs['Surface'])
        else:
            shader = nodes.new(type="ShaderNodeEmission")
            shader.inputs['Strength'].default_value = self.emission_strength
            shader.location = (100, 0)
            links.new(shader.outputs['Emission'], output_node.inputs['Surface'])

        # Starting point - black color
        result = None
        base_color = nodes.new(type="ShaderNodeRGB")
        base_color.outputs[0].default_value = (0, 0, 0, 1)
        base_color.location = (-600, 0)
        
        # Process each layer
        x_position = -400
        y_position = 0
        spacing = 200
        
        for i, (layer_idx, layer_file) in enumerate(layer_files):
            path = os.path.join(folder, layer_file)
            self.report({'INFO'}, f"Processing layer {layer_idx}: {path}")
            
            try:
                # Load image
                img = bpy.data.images.load(path)
                
                # Create texture node
                tex_node = nodes.new(type="ShaderNodeTexImage")
                tex_node.image = img
                tex_node.interpolation = 'Closest'
                tex_node.location = (x_position, y_position + 200)
                
                # Create Mix RGB node
                mix = nodes.new(type="ShaderNodeMixRGB")
                mix.blend_type = 'MIX'
                mix.location = (x_position, y_position)
                
                # Connect texture to factor input
                links.new(tex_node.outputs['Color'], mix.inputs['Fac'])
                
                # Connect previous result to color1 (or base color for first layer)
                if result is None:
                    links.new(base_color.outputs['Color'], mix.inputs['Color1'])
                else:
                    links.new(result.outputs['Color'], mix.inputs['Color1'])
                
                # Set color2 to white (or can be parameterized)
                color_node = nodes.new(type="ShaderNodeRGB")
                color_node.outputs[0].default_value = (1, 1, 1, 1)  # White by default
                color_node.location = (x_position, y_position - 200)
                links.new(color_node.outputs['Color'], mix.inputs['Color2'])
                
                # Update result
                result = mix
                x_position += spacing
                
            except Exception as e:
                self.report({'ERROR'}, f"Failed to process layer {layer_idx}: {str(e)}")
        
        # If no layers were processed successfully
        if result is None:
            self.report({'WARNING'}, "No layers were processed. Using fallback.")
            result = base_color
        
        # Apply mask if found
        if mask_files:
            try:
                mask_path = os.path.join(folder, mask_files[0])
                self.report({'INFO'}, f"Applying mask: {mask_path}")
                
                # Load mask
                mask_img = bpy.data.images.load(mask_path)
                
                # Create mask texture node
                mask_node = nodes.new(type="ShaderNodeTexImage")
                mask_node.image = mask_img
                mask_node.interpolation = 'Closest'
                mask_node.location = (x_position, y_position + 200)
                
                # Create final mix node
                final_mix = nodes.new(type="ShaderNodeMixRGB")
                final_mix.blend_type = 'MIX'
                final_mix.location = (x_position, y_position)
                
                # Connect mask to factor
                links.new(mask_node.outputs['Color'], final_mix.inputs['Fac'])
                
                # Connect previous result to Color1 (as requested)
                links.new(result.outputs['Color'], final_mix.inputs['Color1'])
                
                # Create white background for Color2
                white_bg = nodes.new(type="ShaderNodeRGB")
                white_bg.outputs[0].default_value = (1, 1, 1, 1)
                white_bg.location = (x_position, y_position - 200)
                links.new(white_bg.outputs['Color'], final_mix.inputs['Color2'])
                
                # Update result
                result = final_mix
                
            except Exception as e:
                self.report({'ERROR'}, f"Failed to apply mask: {str(e)}")
        
        # Connect final result to shader
        if self.use_diffuse_shader:
            links.new(result.outputs['Color'], shader.inputs['Color'])
        else:
            links.new(result.outputs['Color'], shader.inputs['Color'])
        
        # Assign material to plane
        plane.data.materials.append(mat)
        self.report({'INFO'}, "Eye material generated successfully.")
        return {'FINISHED'}

class OBJECT_OT_bake_eye_texture(bpy.types.Operator, ImportHelper):
    bl_idname = "figure_tools.bake_eye_texture"
    bl_label = "Bake Eye To PNG"
    bl_description = "Bake current result to eye_bake.png"
    
    filename_ext = ".png"
    filter_glob: StringProperty(default="*.png", options={'HIDDEN'})
    
    bake_resolution: IntProperty(
        name="Resolution",
        description="Resolution of the baked texture",
        default=512,
        min=64,
        max=4096
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "bake_resolution")

    def execute(self, context):
        plane = context.active_object
        if not plane or not plane.data.materials:
            self.report({'ERROR'}, "No object or material found.")
            return {'CANCELLED'}

        mat = plane.data.materials[0]
        nodes = mat.node_tree.nodes
        
        # Create a new image texture node for baking
        bake_node = None
        for node in nodes:
            if isinstance(node, bpy.types.ShaderNodeTexImage) and node.name == "BakeNode":
                bake_node = node
                break
        
        if not bake_node:
            bake_node = nodes.new(type="ShaderNodeTexImage")
            bake_node.name = "BakeNode"
            bake_node.location = (0, -300)
        
        try:
            # Delete existing image if it exists
            if "BakedEye" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["BakedEye"])
                
            # Create a new image for baking
            bake_image = bpy.data.images.new(
                "BakedEye", 
                width=self.bake_resolution, 
                height=self.bake_resolution
            )
            
            # Use the filepath provided by the file browser
            bake_image.filepath_raw = self.filepath
            bake_image.file_format = 'PNG'
            bake_node.image = bake_image
            
            # Make sure this is the active node for baking
            for node in nodes:
                node.select = False
            bake_node.select = True
            nodes.active = bake_node

            # Set up UV mapping for the plane
            if not plane.data.uv_layers:
                bpy.ops.mesh.uv_texture_add()

            # Configure baking settings
            bpy.context.scene.render.engine = 'CYCLES'
            bpy.context.scene.cycles.bake_type = 'DIFFUSE'
            bpy.context.scene.render.bake.use_pass_direct = False
            bpy.context.scene.render.bake.use_pass_indirect = False
            bpy.context.scene.render.bake.use_pass_color = True
            bpy.context.scene.render.bake.margin = 2
            
            # Make sure the object is selected and active
            bpy.ops.object.select_all(action='DESELECT')
            plane.select_set(True)
            bpy.context.view_layer.objects.active = plane
            
            # Perform the bake
            bpy.ops.object.bake(type='DIFFUSE', save_mode='EXTERNAL')
            
            # Save the image
            bake_image.save()

            self.report({'INFO'}, f"Baked image saved to: {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Baking failed: {str(e)}")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(OBJECT_OT_generate_sv_eye_material)
    bpy.utils.register_class(OBJECT_OT_bake_eye_texture)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_bake_eye_texture)
    bpy.utils.unregister_class(OBJECT_OT_generate_sv_eye_material)

if __name__ == "__main__":
    register()