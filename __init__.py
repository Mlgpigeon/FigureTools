bl_info = {
    "name": "Figure Tools",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Object Context Menu",
    "description": "Collection of tools for figure preparation and manipulation",
    "category": "Object",
}

import bpy
from . import operators
from . import menus
from . import dynamic_displacement
from . import sv_eye_bake_operator

def register():
    operators.register()
    menus.register()
    dynamic_displacement.register()
    sv_eye_bake_operator.register()

def unregister():
    sv_eye_bake_operator.unregister()
    dynamic_displacement.unregister()
    menus.unregister()
    operators.unregister()

if __name__ == "__main__":
    register()