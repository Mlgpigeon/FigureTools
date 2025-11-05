import bpy
import os

def ensure_node_group(node_group_name):
    """
    Find and load the node group from the addon's .blend file
    """
    if node_group_name in bpy.data.node_groups:
        return

    addon_dir = os.path.dirname(__file__)
    blend_filepath = os.path.join(addon_dir, "DynamicFigure.blend")

    if not os.path.exists(blend_filepath):
        print(f"Node group file not found: {blend_filepath}")
        return

    try:
        with bpy.data.libraries.load(blend_filepath, link=False) as (data_from, data_to):
            if node_group_name in data_from.node_groups:
                data_to.node_groups = [node_group_name]
            else:
                print(f"Node group {node_group_name} not found in {blend_filepath}")
    except Exception as e:
        print(f"Error loading node group {node_group_name}: {e}")


def create_dynamic_displacement_group(num_pairs):
     # Ensure all required nodes exist before use
    ensure_node_group("ImageDisplacement")
    ensure_node_group("OpenMerger")
    ensure_node_group("Manifolder")
    
    # Create new node group
    node_group = bpy.data.node_groups.new(name="Dynamic_Multi_Displacement", type='GeometryNodeTree')
    
    # Create input/output nodes
    group_inputs = node_group.nodes.new('NodeGroupInput')
    group_outputs = node_group.nodes.new('NodeGroupOutput')
    
    # Position input/output nodes
    group_inputs.location = (-1200, 0)
    group_outputs.location = (400, 0)
    
    # Create interface sockets
    node_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    
    initial_merge = node_group.interface.new_socket(name='InitialMergeDistance', in_out='INPUT', socket_type='NodeSocketFloat')
    initial_merge.default_value = 0.001
    
    subdiv = node_group.interface.new_socket(name='SubdivisionLevel', in_out='INPUT', socket_type='NodeSocketInt')
    subdiv.default_value = 1
    subdiv.min_value = 0
    subdiv.max_value = 8
    
    uvmap = node_group.interface.new_socket(name='UVMap', in_out='INPUT', socket_type='NodeSocketVector')
    
    scale = node_group.interface.new_socket(name='Scale', in_out='INPUT', socket_type='NodeSocketFloat')
    scale.default_value = 0.005
    
    merge = node_group.interface.new_socket(name='MergeDistance', in_out='INPUT', socket_type='NodeSocketFloat')
    merge.default_value = 0.001
    
    # Create material/image/materialsubdiv/addscale/manifold quintuplets sockets
    for i in range(num_pairs):
        # Material input
        material_socket = node_group.interface.new_socket(name=f'Material{i+1}', in_out='INPUT', socket_type='NodeSocketMaterial')
          
        # Image input
        node_group.interface.new_socket(name=f'Image{i+1}', in_out='INPUT', socket_type='NodeSocketImage')
        
        # Material Subdivision input
        material_subdiv = node_group.interface.new_socket(name=f'MaterialSubdiv{i+1}', in_out='INPUT', socket_type='NodeSocketInt')
        material_subdiv.default_value = 0
        material_subdiv.min_value = 0
        material_subdiv.max_value = 8
        
        # Add Scale input
        add_scale = node_group.interface.new_socket(name=f'AddScale{i+1}', in_out='INPUT', socket_type='NodeSocketFloat')
        add_scale.default_value = 0.0
        
        # Manifold input (new)
        manifold = node_group.interface.new_socket(name=f'Manifold{i+1}', in_out='INPUT', socket_type='NodeSocketBool')
        manifold.default_value = False
    
    node_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    
    # Initial merge by distance
    initial_merge = node_group.nodes.new('GeometryNodeGroup')
    initial_merge.node_tree = bpy.data.node_groups.get("OpenMerger")
    initial_merge.location = (-1000, 0)
    node_group.links.new(group_inputs.outputs['Geometry'], initial_merge.inputs['Geometry'])
    node_group.links.new(group_inputs.outputs['InitialMergeDistance'], initial_merge.inputs['Distance'])
    
    # Create manifolder nodes for each material
    manifolder_nodes = []
    for i in range(num_pairs):
        manifolder = node_group.nodes.new('GeometryNodeGroup')
        manifolder.node_tree = bpy.data.node_groups.get("Manifolder")
        manifolder.location = (-900, i * -100)
        node_group.links.new(initial_merge.outputs['Geometry'], manifolder.inputs['Geometry'])
        node_group.links.new(group_inputs.outputs[f'Material{i+1}'], manifolder.inputs['Material'])
        node_group.links.new(group_inputs.outputs[f'Manifold{i+1}'], manifolder.inputs['Manifold'])  # Connect the Manifold boolean
        manifolder_nodes.append(manifolder)
    
    # Join manifolded geometries before subdivision
    pre_subdiv_join = node_group.nodes.new('GeometryNodeJoinGeometry')
    pre_subdiv_join.location = (-750, 0)
    for manifolder in manifolder_nodes:
        node_group.links.new(manifolder.outputs['Geometry'], pre_subdiv_join.inputs['Geometry'])
    

    pre_subdiv_merge = node_group.nodes.new('GeometryNodeGroup')
    pre_subdiv_merge.node_tree = bpy.data.node_groups.get("OpenMerger")
    pre_subdiv_merge.location = (-700, 0)
    node_group.links.new(pre_subdiv_join.outputs['Geometry'], pre_subdiv_merge.inputs['Geometry'])
    node_group.links.new(group_inputs.outputs['InitialMergeDistance'], pre_subdiv_merge.inputs['Distance'])

    # Named attribute node for edge crease
    named_attribute = node_group.nodes.new('GeometryNodeInputNamedAttribute')
    named_attribute.location = (-650, -100)
    named_attribute.data_type = 'FLOAT'
    named_attribute.inputs['Name'].default_value = "crease_edge"

    # Subdivision Surface
    subdivision = node_group.nodes.new('GeometryNodeSubdivisionSurface')
    subdivision.location = (-600, 0)
    node_group.links.new(pre_subdiv_merge.outputs['Geometry'], subdivision.inputs['Mesh'])
    node_group.links.new(group_inputs.outputs['SubdivisionLevel'], subdivision.inputs['Level'])
    node_group.links.new(named_attribute.outputs['Attribute'], subdivision.inputs['Edge Crease'])
    
    # Create displacement nodes
    displacement_nodes = []
    for i in range(num_pairs):
        disp_node = node_group.nodes.new('GeometryNodeGroup')
        disp_node.node_tree = bpy.data.node_groups['ImageDisplacement']
        disp_node.location = (-400, -i * 200)
        displacement_nodes.append(disp_node)
        
        # Connect inputs (now from subdivision)
        node_group.links.new(subdivision.outputs['Mesh'], disp_node.inputs['Geometry'])
        node_group.links.new(group_inputs.outputs['UVMap'], disp_node.inputs['Vector'])
        node_group.links.new(group_inputs.outputs['Scale'], disp_node.inputs['Scale'])
        node_group.links.new(group_inputs.outputs[f'Material{i+1}'], disp_node.inputs['Material'])
        node_group.links.new(group_inputs.outputs[f'Image{i+1}'], disp_node.inputs['Image'])
        node_group.links.new(group_inputs.outputs[f'MaterialSubdiv{i+1}'], disp_node.inputs['IndividualSubdiv'])
        node_group.links.new(group_inputs.outputs[f'AddScale{i+1}'], disp_node.inputs['AddScale'])
    
    # Join geometries after displacement
    join_node = node_group.nodes.new('GeometryNodeJoinGeometry')
    join_node.location = (-100, 0)
    for disp_node in displacement_nodes:
        node_group.links.new(disp_node.outputs['Geometry'], join_node.inputs['Geometry'])
    
    # Final merge by distance node
    open_merger = node_group.nodes.new('GeometryNodeGroup')
    open_merger.node_tree = bpy.data.node_groups.get("OpenMerger")
    open_merger.location = (150, 0)
    
    # Connect nodes
    node_group.links.new(join_node.outputs['Geometry'], open_merger.inputs['Geometry'])
    node_group.links.new(group_inputs.outputs['MergeDistance'], open_merger.inputs['Distance'])
    
    # Connect final output
    node_group.links.new(open_merger.outputs['Geometry'], group_outputs.inputs['Geometry'])
    
    return node_group

# Rest of the script remains the same (FigurePanel, DynamicDisplacementPanel, AddDynamicPairs, register/unregister functions)
# Only the create_dynamic_displacement_group function needs to be updated

class FigurePanel(bpy.types.Panel):
    bl_label = "Figure Settings"
    bl_idname = "VIEW3D_PT_figure_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'  # This puts it in the N panel
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if obj:
            layout.prop(obj, "is_figure", text="Is Figure")
            if obj.is_figure:
                layout.prop(obj, "displacement_pairs")
                layout.operator("object.add_dynamic_pairs")

class DynamicDisplacementPanel(bpy.types.Panel):
    bl_label = "Dynamic Displacement"
    bl_idname = "VIEW3D_PT_dynamic_displacement"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if obj and obj.is_figure:  # Only show if object is marked as figure
            layout.operator("object.add_dynamic_pairs")
            layout.prop(obj, "displacement_pairs")

class AddDynamicPairs(bpy.types.Operator):
    bl_idname = "object.add_dynamic_pairs"
    bl_label = "Set Number of Pairs"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj.is_figure:
            return {'CANCELLED'}
                
        num_pairs = obj.displacement_pairs
        
        # Store current values with specific types
        # Store all values including multiple materials and images
        # Store all sockets dynamically
        old_values = {}
        for mod in obj.modifiers:
            if mod.name.startswith("Dynamic_Displacement"):
                i = 1
                while True:
                    socket_name = f"Socket_{i}"
                    if socket_name in mod:
                        try:
                            old_values[socket_name] = mod[socket_name]
                            print(f"Stored {socket_name} = {old_values[socket_name]}")
                        except Exception as e:
                            print(f"Failed to store {socket_name}: {e}")
                    else:
                        break  # Stop when no more sockets are found
                    i += 1

                obj.modifiers.remove(mod)  # Remove the existing modifier
                break  # Ensure only one modifier is removed
        
        # Remove any existing Corrective Smooth and Decimate modifiers
        for mod in obj.modifiers[:]:  # Create a copy of the list to avoid issues during removal
            if mod.type == 'CORRECTIVE_SMOOTH' or mod.type == 'DECIMATE':
                obj.modifiers.remove(mod)

        # Create new dynamic displacement modifier
        mod = obj.modifiers.new(name="Dynamic_Displacement", type='NODES')
        mod.node_group = create_dynamic_displacement_group(num_pairs)

        # Ensure the modifier is initialized
        bpy.context.view_layer.update()

        # Restore numeric values first
        for socket, value in old_values.items():
            try:
                if value is not None:
                    if isinstance(value, (float, int, bool)):  # Added bool to handle the new Manifold parameter
                        mod[socket] = value
                        print(f"Restored numeric/boolean {socket} = {value}")
                    elif isinstance(value, bpy.types.Material):
                        mod[socket] = value
                        print(f"Restored material {socket}")
                    elif isinstance(value, bpy.types.Image):
                        mod[socket] = value
                        print(f"Restored image {socket}")
            except Exception as e:
                print(f"Failed to restore {socket}: {e}")
        
        # Add Corrective Smooth modifier
        corrective_smooth = obj.modifiers.new(name="Corrective_Smooth", type='CORRECTIVE_SMOOTH')
        corrective_smooth.factor = 1.0
        corrective_smooth.use_only_smooth = True
        corrective_smooth.use_pin_boundary = True
        
        # Add Decimate modifier
        decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate.ratio = 1.0
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(FigurePanel)
    bpy.utils.register_class(DynamicDisplacementPanel)
    bpy.utils.register_class(AddDynamicPairs)
    
    bpy.types.Object.displacement_pairs = bpy.props.IntProperty(
        name="Number of Pairs",
        description="Number of material/image pairs",
        min=1,
        max=20,
        default=1
    )
    
    bpy.types.Object.is_figure = bpy.props.BoolProperty(
        name="Is Figure",
        description="Mark this object as a figure for dynamic displacement",
        default=False
    )

def unregister():
    bpy.utils.unregister_class(FigurePanel)
    bpy.utils.unregister_class(DynamicDisplacementPanel)
    bpy.utils.unregister_class(AddDynamicPairs)
    del bpy.types.Object.displacement_pairs
    del bpy.types.Object.is_figure

# Register when running the script
if __name__ == "__main__":
    register()