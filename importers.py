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

