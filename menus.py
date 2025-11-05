import bpy

class VIEW3D_MT_figure_tools_menu(bpy.types.Menu):
    bl_label = "Figure Tools"
    bl_idname = "VIEW3D_MT_figure_tools_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("figure_tools.rename_uvmaps", text="Rename UV Maps")
        layout.operator("figure_tools.bake_sv_eyes", text="Bake SV Eyes")  
        layout.operator("figure_tools.bake_scvi_material", text="Bake ZA Material")

def add_to_context_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.menu(VIEW3D_MT_figure_tools_menu.bl_idname)

menu_classes = [
    VIEW3D_MT_figure_tools_menu,
]

def register():
    for cls in menu_classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object_context_menu.append(add_to_context_menu)

def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(add_to_context_menu)
    for cls in reversed(menu_classes):
        bpy.utils.unregister_class(cls)
