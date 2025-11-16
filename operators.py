import bpy
from bpy.props import (
    PointerProperty,
    CollectionProperty,
    BoolProperty,
    IntProperty,
    StringProperty,
)
import os
from .importers import ensure_node_group
from .sv_eye_bake_operator import (
    OBJECT_OT_generate_sv_eye_material,
    OBJECT_OT_bake_eye_texture,
)


# -----------------------------------------------------------------------------
# Material Combiner Classes
# -----------------------------------------------------------------------------
class MaterialItem(bpy.types.PropertyGroup):
    material: PointerProperty(
        name="Material",
        type=bpy.types.Material
    )
    select: BoolProperty(
        name="Combine",
        default=False,
        description="Select this material to combine"
    )
    # Store the actual index in obj.data.materials
    material_index: IntProperty(
        name="Material Index",
        default=-1,
        description="Real index of this material in the object's material slots"
    )

class MCProps(bpy.types.PropertyGroup):
    materials: CollectionProperty(type=MaterialItem)
    index: IntProperty(
        name="Index", 
        default=0,
        min=0
    )
    # Add a flag to track if we're in a problematic state
    needs_resync: BoolProperty(default=False)

def safe_material_access(material, test_nodes=False):
    """
    Minimal, non-intrusive check for material validity
    Only checks basic accessibility without deep inspection
    """
    if not material:
        return False
    
    try:
        # Only do the most basic check to avoid conflicts
        _ = material.name
        
        # Don't check if it exists in bpy.data.materials as this can cause conflicts
        # Only check node tree if specifically requested and safe to do so
        if test_nodes and hasattr(material, 'use_nodes') and material.use_nodes:
            if hasattr(material, 'node_tree') and material.node_tree:
                # Don't iterate through nodes, just check if node_tree exists
                pass
                
        return True
    except:
        return False
# --- 1) Añade este operador (p. ej. tras OBJECT_OT_add_solidifier) ---
class OBJECT_OT_add_merger(bpy.types.Operator):
    """Add Merger (OpenMerger) Geometry Nodes modifier"""
    bl_idname = "object.add_merger"
    bl_label = "Add Merger"
    bl_options = {'REGISTER', 'UNDO'}

    def ensure_openmerger_wrapper(self) -> bpy.types.NodeTree:
        """
        Crea (o reutiliza si ya existe) un node group de Geometry Nodes que:
        Group Input(Geometry, Distance float) -> OpenMerger -> Group Output(Geometry)
        """
        # 1) Asegurar que OpenMerger existe (cargado desde DynamicFigure.blend si hace falta)
        ensure_node_group("OpenMerger")  # usa importers.ensure_node_group  :contentReference[oaicite:0]{index=0}

        group_name = "OpenMerger_Wrapper"
        ng = bpy.data.node_groups.get(group_name)
        if ng:
            return ng

        # 2) Crear el group vacío
        ng = bpy.data.node_groups.new(name=group_name, type='GeometryNodeTree')

        # 3) Nodos de entrada/salida
        n_in = ng.nodes.new("NodeGroupInput")
        n_out = ng.nodes.new("NodeGroupOutput")
        n_in.location = (-400, 0)
        n_out.location = (300, 0)

        # 4) Interfaz: Geometry (INPUT), Distance (INPUT), Geometry (OUTPUT)
        #    - Geometry INPUT
        ng.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        #    - Distance INPUT
        s_dist = ng.interface.new_socket(name="Distance", in_out='INPUT', socket_type='NodeSocketFloat')
        s_dist.default_value = 0.001
        #    - Geometry OUTPUT
        ng.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

        # 5) Nodo Group que referencia al OpenMerger interno
        openmerger_node = ng.nodes.new("GeometryNodeGroup")
        openmerger_node.location = (0, 0)
        openmerger_node.node_tree = bpy.data.node_groups.get("OpenMerger")

        # 6) Conexiones: Input -> OpenMerger -> Output
        ng.links.new(n_in.outputs["Geometry"], openmerger_node.inputs.get("Geometry"))
        # El grupo OpenMerger debe tener un input "Distance"; lo conectamos
        if "Distance" in openmerger_node.inputs:
            ng.links.new(n_in.outputs["Distance"], openmerger_node.inputs["Distance"])
        else:
            # Por si el input se llama distinto en tu grupo, intenta nombres comunes
            for cand in ("MergeDistance", "Distance", "distance"):
                if cand in openmerger_node.inputs:
                    ng.links.new(n_in.outputs["Distance"], openmerger_node.inputs[cand])
                    break

        # Salida
        ng.links.new(openmerger_node.outputs.get("Geometry"), n_out.inputs.get("Geometry"))

        return ng

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object selected.")
            return {'CANCELLED'}

        # Crear / obtener el wrapper
        wrapper = self.ensure_openmerger_wrapper()

        # Añadir el modificador de Geometry Nodes
        mod = obj.modifiers.new(name="Merger", type='NODES')
        mod.node_group = wrapper

        # Valor inicial razonable
        try:
            mod["Distance"] = 0.001
        except Exception:
            pass

        self.report({'INFO'}, "Merger added successfully.")
        return {'FINISHED'}

import bpy
import uuid
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper


class OBJECT_OT_bake_scvi_material(bpy.types.Operator, ImportHelper):
    """Bakea todos los materiales del objeto activo a PNGs individuales"""
    bl_idname = "figure_tools.bake_scvi_material"
    bl_label = "Bake SCVI Materials"
    bl_options = {'REGISTER', 'UNDO'}

    # Ahora solo pide directorio, no archivo específico
    filename_ext = ""
    use_filter_folder = True
    
    directory: StringProperty(
        name="Output Directory",
        description="Directory where PNG files will be saved",
        subtype='DIR_PATH'
    )
    
    bake_resolution: IntProperty(name="Resolution", default=1024, min=64, max=8192)
    margin: IntProperty(name="Margin (px)", default=4, min=0, max=64)
    use_emit_trick: BoolProperty(
        name="Force Emission Bake",
        description="Usa EMIT para materiales con Node Groups (recomendado)",
        default=False  # True por defecto para Node Groups
    )
    bake_all_materials: BoolProperty(
        name="Bake All Materials",
        description="Bakea todos los materiales del objeto. Si está desactivado, solo bakea el material activo",
        default=True
    )

    @classmethod
    def poll(cls, context):
        o = getattr(context, "active_object", None)
        return o and o.type == 'MESH' and len(o.data.materials) > 0

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "bake_all_materials")
        col.prop(self, "bake_resolution")
        col.prop(self, "margin")
        col.prop(self, "use_emit_trick")
        
        # Info
        obj = context.active_object
        if obj and obj.type == 'MESH':
            mat_count = len([m for m in obj.data.materials if m and m.use_nodes])
            if self.bake_all_materials:
                layout.label(text=f"Will bake {mat_count} materials", icon='INFO')
            else:
                layout.label(text=f"Will bake active material only", icon='INFO')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def bake_single_material(self, context, obj, mat, mat_index, output_path):
        """
        Bakea un solo material del objeto
        Retorna (success: bool, message: str, non_black_pixels: int)
        """
        if not mat or not mat.use_nodes:
            return (False, f"Material '{mat.name if mat else 'None'}' no usa nodos", 0)
        
        nt = mat.node_tree
        nodes = nt.nodes
        links = nt.links
        
        print(f"\n--- Baking: {mat.name} (index {mat_index}) ---")
        
        # Verificar Material Output
        output = next((n for n in nodes if isinstance(n, bpy.types.ShaderNodeOutputMaterial)), None)
        if not output:
            return (False, f"'{mat.name}' no tiene Material Output", 0)
        
        surf_input = output.inputs.get("Surface")
        if not surf_input or not surf_input.is_linked:
            return (False, f"'{mat.name}' no tiene shader conectado", 0)
        
        orig_link = surf_input.links[0]
        orig_from_node = orig_link.from_node
        orig_from_socket = orig_link.from_socket
        
        # Crear nodo de bake
        bake_node = next((n for n in nodes
                        if isinstance(n, bpy.types.ShaderNodeTexImage) and n.name == "BakeNode"), None)
        if not bake_node:
            bake_node = nodes.new("ShaderNodeTexImage")
            bake_node.name = "BakeNode"
            bake_node.label = "BakeTarget"
            bake_node.location = (0, -500)

        import uuid
        unique = uuid.uuid4().hex[:8]
        img_name = f"{mat.name}_Baked_{unique}"
        bake_img = bpy.data.images.new(img_name, width=self.bake_resolution, height=self.bake_resolution)
        bake_img.filepath_raw = output_path
        bake_img.file_format = 'PNG'
        bake_node.image = bake_img

        # Activar el BakeNode
        for n in nodes:
            n.select = False
        bake_node.select = True
        nodes.active = bake_node
        
        # Añadir nodos dummy en otros materiales
        dummy_nodes = {}
        for i, other_mat in enumerate(obj.data.materials):
            if i == mat_index or not other_mat or not other_mat.use_nodes:
                continue
            
            other_nodes = other_mat.node_tree.nodes
            dummy = None
            for n in other_nodes:
                if isinstance(n, bpy.types.ShaderNodeTexImage) and n.name == "BakeNode":
                    dummy = n
                    break
            
            if not dummy:
                dummy = other_nodes.new("ShaderNodeTexImage")
                dummy.name = "BakeNode"
                dummy.location = (0, -500)
            
            dummy.image = bake_img
            dummy_nodes[other_mat] = dummy
        
        # ========== CLAVE: GUARDAR Y RESETEAR TODAS LAS CARAS ==========
        mesh = obj.data
        original_hide_state = {}
        
        # PRIMERO: Guardar el estado original de TODAS las caras
        for i, poly in enumerate(mesh.polygons):
            original_hide_state[i] = poly.hide
        
        # SEGUNDO: MOSTRAR TODAS las caras (limpiar estado previo)
        for poly in mesh.polygons:
            poly.hide = False
        
        # TERCERO: Ocultar solo las que NO son de este material
        for poly in mesh.polygons:
            if poly.material_index != mat_index:
                poly.hide = True
        
        mesh.update()
        
        scene = context.scene
        temp_emit = None
        
        try:
            # Lógica de color exacta del código original
            if self.use_emit_trick:
                if orig_link:
                    links.remove(orig_link)
                temp_emit = nodes.new("ShaderNodeEmission")
                temp_emit.location = ( (orig_from_node.location.x + 200) if orig_from_node else output.location.x - 200,
                                    (orig_from_node.location.y if orig_from_node else output.location.y) )
                if orig_from_socket:
                    links.new(orig_from_socket, temp_emit.inputs["Color"])
                links.new(temp_emit.outputs["Emission"], surf_input)

                scene.cycles.bake_type = 'EMIT'
            else:
                scene.cycles.bake_type = 'DIFFUSE'
                scene.render.bake.use_pass_direct = False
                scene.render.bake.use_pass_indirect = False
                scene.render.bake.use_pass_color = True

            # Bake
            bpy.ops.object.bake(type=scene.cycles.bake_type, save_mode='EXTERNAL')
            bake_img.save()
            
            # Verificar resultado
            pixels = list(bake_img.pixels)
            non_black = sum(1 for p in pixels if p > 0.01)
            
            print(f"  Non-black pixels: {non_black}/{len(pixels)}")
            
            success = non_black > 0
            message = f"✓ {mat.name}" if success else f"✗ {mat.name} (negro)"
            
            return (success, message, non_black)
            
        except Exception as e:
            return (False, f"✗ {mat.name}: {str(e)}", 0)
            
        finally:
            # ========== RESTAURAR TODO AL ESTADO ORIGINAL ==========
            # 1. Restaurar estado de caras
            for i, poly in enumerate(mesh.polygons):
                poly.hide = original_hide_state.get(i, False)
            mesh.update()
            
            # 2. Restaurar enlaces del material
            if temp_emit:
                try:
                    if surf_input:
                        for l in list(surf_input.links):
                            links.remove(l)
                        if orig_from_socket:
                            links.new(orig_from_socket, surf_input)
                    nodes.remove(temp_emit)
                except:
                    pass
            
            # 3. Limpiar BakeNode del material actual
            try:
                nodes.remove(bake_node)
            except:
                pass
            
            # 4. Limpiar dummy nodes de otros materiales
            for other_mat, dummy in dummy_nodes.items():
                try:
                    other_mat.node_tree.nodes.remove(dummy)
                except:
                    pass
            
            # 5. Limpiar imagen temporal de Blender
            try:
                bpy.data.images.remove(bake_img)
            except:
                pass

    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Selecciona un objeto mesh")
            return {'CANCELLED'}
        
        # Verificar directorio
        import os
        if not self.directory or not os.path.isdir(self.directory):
            self.report({'ERROR'}, "Directorio inválido")
            return {'CANCELLED'}
        
        print(f"\n{'='*60}")
        print(f"BATCH BAKING MATERIALS")
        print(f"Object: {obj.name}")
        print(f"Output: {self.directory}")
        print(f"{'='*60}")
        
        # UVs check
        mesh = obj.data
        if not mesh.uv_layers:
            mode_prev = obj.mode
            try:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.uv.smart_project()
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                self.report({'ERROR'}, "No se pudieron crear UVs")
                return {'CANCELLED'}
        
        # Guardar estado
        scene = context.scene
        prev_engine = scene.render.engine
        prev_bake = {
            "type": scene.cycles.bake_type if hasattr(scene, 'cycles') else 'DIFFUSE',
            "margin": scene.render.bake.margin,
            "use_pass_direct": scene.render.bake.use_pass_direct,
            "use_pass_indirect": scene.render.bake.use_pass_indirect,
            "use_pass_color": scene.render.bake.use_pass_color,
            "use_selected_to_active": scene.render.bake.use_selected_to_active,
            "use_clear": scene.render.bake.use_clear,
        }
        
        prev_active = context.view_layer.objects.active
        sel_state = {o: o.select_get() for o in context.view_layer.objects}
        
        # Configurar escena para bake
        scene.render.engine = 'CYCLES'
        scene.render.bake.margin = self.margin
        scene.render.bake.use_selected_to_active = False
        scene.render.bake.use_clear = True
        scene.render.bake.use_pass_direct = False
        scene.render.bake.use_pass_indirect = False
        scene.render.bake.use_pass_color = True
        
        # Seleccionar solo este objeto
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        context.view_layer.update()
        
        # Determinar materiales a bakear
        if self.bake_all_materials:
            materials_to_bake = [
                (i, mat) for i, mat in enumerate(obj.data.materials)
                if mat and mat.use_nodes
            ]
        else:
            mat = obj.active_material
            if not mat or not mat.use_nodes:
                self.report({'ERROR'}, "Material activo no válido")
                return {'CANCELLED'}
            
            mat_index = None
            for i, slot_mat in enumerate(obj.data.materials):
                if slot_mat == mat:
                    mat_index = i
                    break
            
            if mat_index is None:
                self.report({'ERROR'}, "Material activo no encontrado")
                return {'CANCELLED'}
            
            materials_to_bake = [(mat_index, mat)]
        
        print(f"\nMaterials to bake: {len(materials_to_bake)}")
        
        # Bakear cada material
        results = []
        successful = 0
        failed = 0
        
        try:
            for mat_index, mat in materials_to_bake:
                # Generar nombre de archivo
                safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in mat.name)
                output_path = os.path.join(self.directory, f"{safe_name}.png")
                
                # Bakear
                success, message, pixels = self.bake_single_material(
                    context, obj, mat, mat_index, output_path
                )
                
                results.append(message)
                
                if success:
                    successful += 1
                    print(f"  ✓ Saved: {output_path}")
                else:
                    failed += 1
                    print(f"  ✗ Failed: {message}")
        
        finally:
            # Restaurar todo
            for o, s in sel_state.items():
                try:
                    o.select_set(s)
                except:
                    pass
            context.view_layer.objects.active = prev_active
            
            scene.render.engine = prev_engine
            scene.render.bake.margin = prev_bake["margin"]
            scene.render.bake.use_pass_direct = prev_bake["use_pass_direct"]
            scene.render.bake.use_pass_indirect = prev_bake["use_pass_indirect"]
            scene.render.bake.use_pass_color = prev_bake["use_pass_color"]
            scene.render.bake.use_selected_to_active = prev_bake["use_selected_to_active"]
            scene.render.bake.use_clear = prev_bake["use_clear"]
            if hasattr(scene, 'cycles'):
                scene.cycles.bake_type = prev_bake["type"]
        
        # Reporte final
        print(f"\n{'='*60}")
        print(f"BAKE COMPLETE")
        print(f"Successful: {successful}/{len(materials_to_bake)}")
        print(f"Failed: {failed}/{len(materials_to_bake)}")
        print(f"{'='*60}\n")
        
        summary = f"Baked {successful}/{len(materials_to_bake)} materials"
        if failed > 0:
            summary += f" ({failed} failed)"
        
        self.report({'INFO'}, summary)
        
        return {'FINISHED'}


class MATERIAL_UL_combine_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        try:
            if not item:
                layout.label(text="Invalid item")
                return
                
            # Since we only sync valid materials now, we should always have a material
            if item.material and safe_material_access(item.material):
                try:
                    material_name = item.material.name
                    row = layout.row(align=True)
                    row.prop(item, "select", text="")
                    row.label(text=f"[{item.material_index}] {material_name}", icon='MATERIAL')
                except:
                    row = layout.row(align=True)
                    row.prop(item, "select", text="")
                    row.label(text=f"[{item.material_index}] <Access Error>", icon='ERROR')
            else:
                row = layout.row(align=True)
                row.prop(item, "select", text="")
                row.label(text=f"[{item.material_index}] <Invalid>", icon='ERROR')
                
        except Exception as e:
            layout.label(text="List Error")

class OBJECT_OT_sync_materials(bpy.types.Operator):
    """Sincronizar lista de materiales del objeto"""
    bl_idname = "figure_tools.sync_materials"
    bl_label = "Sync Materials"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            obj = context.object
            if not obj or obj.type != 'MESH':
                self.report({'WARNING'}, "Select a mesh object")
                return {'CANCELLED'}
                
            mc = obj.mc_props
            
            # Clear flags
            mc.needs_resync = False
            
            # LIMPIAR COMPLETAMENTE la lista anterior
            mc.materials.clear()
            mc.index = 0
            
            # Verificar que el objeto tenga materiales
            if not hasattr(obj.data, 'materials') or not obj.data.materials:
                self.report({'INFO'}, "Object has no materials")
                return {'FINISHED'}
            
            # Add only valid materials (not None) to avoid confusion
            valid_materials = 0
            print(f"=== SYNC MATERIALS DEBUG ===")
            print(f"Object: {obj.name}")
            print(f"Total material slots: {len(obj.data.materials)}")
            
            for i, mat in enumerate(obj.data.materials):
                try:
                    print(f"  Slot [{i}]: {mat.name if mat else 'None'}")
                    # Only add non-None materials
                    if mat:
                        item = mc.materials.add()
                        item.material = mat
                        item.material_index = i  # Store the real index
                        item.select = False
                        valid_materials += 1
                        print(f"    -> Added to UI list as item {valid_materials-1} with real index {i}")
                    else:
                        print(f"    -> Skipped (None material)")
                except Exception as e:
                    print(f"Error adding material {i}: {e}")
                    continue
            
            print(f"Total valid materials added: {valid_materials}")
                
            self.report({'INFO'}, f"Synchronized {valid_materials} materials")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error in sync_materials: {str(e)}")
            return {'CANCELLED'}
        
class OBJECT_OT_combine_materials(bpy.types.Operator):
    """Combina los materiales marcados en el primero"""
    bl_idname = "figure_tools.combine_materials"
    bl_label = "Combine Materials"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            obj = context.object
            if not obj or obj.type != 'MESH':
                return False
            mc = obj.mc_props
            
            # Don't do complex validation in poll, just basic checks
            if not mc.materials or mc.needs_resync:
                return False
                
            # Simple count of selected materials
            selected_count = sum(1 for item in mc.materials 
                                if item.select and item.material and item.material_index >= 0)
            return selected_count >= 2
        except:
            return False

    def execute(self, context):
        try:
            obj = context.object
            mc = obj.mc_props
            mats = obj.data.materials

            print(f"=== STARTING MATERIAL COMBINATION ===")
            print(f"Object: {obj.name}")
            print(f"Total materials in object: {len(mats)}")
            for i, mat in enumerate(mats):
                print(f"  [{i}] {mat.name if mat else 'None'}")

            # Simple validation
            if mc.needs_resync:
                print("ERROR: Materials need resync")
                self.report({'WARNING'}, "Please sync materials first.")
                return {'CANCELLED'}

            # Get selected materials using their stored real indices
            selected_materials = []
            print(f"Checking {len(mc.materials)} items in UI list:")
            for i, item in enumerate(mc.materials):
                print(f"  UI[{i}]: select={item.select}, material={item.material.name if item.material else 'None'}, index={item.material_index}")
                if item.select and item.material and item.material_index >= 0:
                    # Verify the index is still valid
                    if item.material_index < len(obj.data.materials):
                        # Double-check that the material at this index matches
                        if obj.data.materials[item.material_index] == item.material:
                            selected_materials.append((item.material_index, item.material))
                            print(f"    -> SELECTED: Index {item.material_index} = {item.material.name}")
                        else:
                            print(f"    -> MISMATCH at index {item.material_index}")
                            mc.needs_resync = True
                    else:
                        print(f"    -> INVALID INDEX {item.material_index}")
                        mc.needs_resync = True
            
            if mc.needs_resync:
                print("ERROR: Materials out of sync after validation")
                self.report({'WARNING'}, "Materials are out of sync. Please sync first.")
                return {'CANCELLED'}
            
            if len(selected_materials) < 2:
                print(f"ERROR: Only {len(selected_materials)} materials selected")
                self.report({'WARNING'}, "Select at least two valid materials")
                return {'CANCELLED'}

            # Sort by index to process in order
            selected_materials.sort(key=lambda x: x[0])
            
            # Use the first selected material as target
            target_index, target_material = selected_materials[0]
            target_material_name = target_material.name
            
            # Get all the indices we want to merge INTO the target
            indices_to_merge = [idx for idx, mat in selected_materials]
            
            print(f"=== COMBINATION PLAN ===")
            print(f"Target material: {target_material_name} (index {target_index})")
            print(f"All selected materials:")
            for idx, mat in selected_materials:
                print(f"  - Index {idx}: {mat.name if mat else 'None'}")
            print(f"Indices to merge: {indices_to_merge}")
            
            # Debug: Check current face assignments BEFORE changes
            print(f"=== FACE ASSIGNMENTS BEFORE ===")
            face_counts = {}
            if hasattr(obj.data, 'polygons'):
                for poly in obj.data.polygons:
                    face_counts[poly.material_index] = face_counts.get(poly.material_index, 0) + 1
                for mat_idx, count in sorted(face_counts.items()):
                    mat_name = mats[mat_idx].name if mat_idx < len(mats) and mats[mat_idx] else 'None'
                    print(f"  Material [{mat_idx}] {mat_name}: {count} faces")
            
            # Reasignar todas las caras de los materiales seleccionados al material target
            faces_reassigned = 0
            if hasattr(obj.data, 'polygons'):
                for poly in obj.data.polygons:
                    if poly.material_index in indices_to_merge and poly.material_index != target_index:
                        old_index = poly.material_index
                        poly.material_index = target_index
                        faces_reassigned += 1
                        if faces_reassigned <= 5:  # Show first few reassignments
                            print(f"    Face reassigned from [{old_index}] to [{target_index}]")
            
            print(f"Total faces reassigned: {faces_reassigned}")
            
            # Reasignar todas las caras de los materiales seleccionados al material target
            faces_reassigned = 0
            if hasattr(obj.data, 'polygons'):
                for poly in obj.data.polygons:
                    if poly.material_index in indices_to_merge and poly.material_index != target_index:
                        old_index = poly.material_index
                        poly.material_index = target_index
                        faces_reassigned += 1
                        if faces_reassigned <= 5:  # Show first few reassignments
                            print(f"    Face reassigned from [{old_index}] to [{target_index}]")
            
            print(f"Total faces reassigned: {faces_reassigned}")
            
            # Remove the secondary material slots (from highest to lowest index)
            # This automatically handles reindexing of remaining materials
            indices_to_remove = [idx for idx, mat in selected_materials[1:]]  # All except target
            removed_count = 0
            
            print(f"=== REMOVING MATERIALS ===")
            for idx in sorted(indices_to_remove, reverse=True):
                if idx < len(mats):
                    mat_name = mats[idx].name if mats[idx] else 'None'
                    print(f"Removing material at index {idx}: {mat_name}")
                    mats.pop(index=idx)
                    removed_count += 1

            # Debug: Check final face assignments
            print(f"=== FACE ASSIGNMENTS AFTER ===")
            face_counts = {}
            if hasattr(obj.data, 'polygons'):
                for poly in obj.data.polygons:
                    face_counts[poly.material_index] = face_counts.get(poly.material_index, 0) + 1
                for mat_idx, count in sorted(face_counts.items()):
                    mat_name = mats[mat_idx].name if mat_idx < len(mats) and mats[mat_idx] else 'None'
                    print(f"  Material [{mat_idx}] {mat_name}: {count} faces")

            # Clear the UI list to force re-synchronization
            mc.materials.clear()
            mc.index = 0
            mc.needs_resync = True
            
            print(f"=== COMBINATION COMPLETE ===")
            print(f"Removed {removed_count} material slots")
            print(f"Final material count: {len(mats)}")
            print(f"Materials remaining:")
            for i, mat in enumerate(mats):
                print(f"  [{i}] {mat.name if mat else 'None'}")
            
            self.report(
                {'INFO'},
                f"Combined {removed_count} materials into '{target_material_name}'. "
                f"Faces reassigned: {faces_reassigned}. Please sync materials to refresh the list."
            )
            return {'FINISHED'}
            
        except Exception as e:
            print(f"EXCEPTION in combine_materials: {str(e)}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Error in combine_materials: {str(e)}")
            return {'CANCELLED'}
        
class OBJECT_OT_debug_selection(bpy.types.Operator):
    """Debug: Show what materials are selected"""
    bl_idname = "figure_tools.debug_selection"
    bl_label = "Debug Selection"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object")
            return {'CANCELLED'}
            
        mc = obj.mc_props
        
        print(f"=== DEBUG SELECTION ===")
        print(f"Object: {obj.name}")
        print(f"UI List has {len(mc.materials)} items:")
        
        selected_count = 0
        for i, item in enumerate(mc.materials):
            status = "SELECTED" if item.select else "not selected"
            mat_name = item.material.name if item.material else "None"
            print(f"  UI[{i}]: {status} - Material: {mat_name} - Real Index: {item.material_index}")
            if item.select:
                selected_count += 1
        
        print(f"Total selected: {selected_count}")
        
        print(f"Object material slots:")
        for i, mat in enumerate(obj.data.materials):
            print(f"  Slot[{i}]: {mat.name if mat else 'None'}")
            
        self.report({'INFO'}, f"Debug complete. Check console for details.")
        return {'FINISHED'}
    """Seleccionar todos los materiales"""
    bl_idname = "figure_tools.select_all_materials"
    bl_label = "Select All"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            obj = context.object
            if obj and obj.type == 'MESH':
                mc = obj.mc_props
                
                if mc.needs_resync:
                    self.report({'WARNING'}, "Please sync materials first.")
                    return {'CANCELLED'}
                
                for item in mc.materials:
                    if item.material and item.material_index >= 0:  # Only select valid materials
                        item.select = True
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
        return {'FINISHED'}
    
class OBJECT_OT_select_all_materials(bpy.types.Operator):
    """Seleccionar todos los materiales"""
    bl_idname = "figure_tools.select_all_materials"
    bl_label = "Select All"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            obj = context.object
            if obj and obj.type == 'MESH':
                mc = obj.mc_props
                
                if mc.needs_resync:
                    self.report({'WARNING'}, "Please sync materials first.")
                    return {'CANCELLED'}
                
                for item in mc.materials:
                    if item.material and item.material_index >= 0:
                        item.select = True
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
        return {'FINISHED'}
    
class OBJECT_OT_deselect_all_materials(bpy.types.Operator):
    """Deseleccionar todos los materiales"""
    bl_idname = "figure_tools.deselect_all_materials"
    bl_label = "Deselect All"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            obj = context.object
            if obj and obj.type == 'MESH':
                mc = obj.mc_props
                
                if mc.needs_resync:
                    self.report({'WARNING'}, "Please sync materials first.")
                    return {'CANCELLED'}
                
                for item in mc.materials:
                    item.select = False
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
        return {'FINISHED'}


import subprocess
import sys
from pathlib import Path

class OBJECT_OT_launch_transform_tool(bpy.types.Operator):
    """Launch Transform Tool (combined_mirrorer.py)"""
    bl_idname = "figure_tools.launch_transform_tool"
    bl_label = "Transform Tools"
    bl_description = "Launch the Transform Tool GUI for texture and model processing"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            addon_dir = Path(__file__).resolve().parent
            transform_dir = addon_dir / "realesrgan" / "Transform Tool"
            
            if sys.platform == "win32":
                bat_path = transform_dir / "mirror.bat"
                
                if not bat_path.exists():
                    self.report({'ERROR'}, f"mirror.bat not found")
                    return {'CANCELLED'}
                
                # Execute mirror.bat which handles everything
                subprocess.Popen(
                    [str(bat_path)],
                    cwd=str(transform_dir),
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                self.report({'INFO'}, "Transform Tool launched")
                return {'FINISHED'}
            else:
                # For non-Windows systems
                script_path = transform_dir / "combined_mirrorer.py"
                venv_python = transform_dir / ".venv" / "bin" / "python"
                
                if venv_python.exists():
                    python_exe = venv_python
                else:
                    python_exe = sys.executable
                
                subprocess.Popen(
                    [str(python_exe), str(script_path)],
                    cwd=str(transform_dir)
                )
                
                self.report({'INFO'}, "Transform Tool launched")
                return {'FINISHED'}
                
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.report({'ERROR'}, f"Failed to launch: {str(e)}")
            return {'CANCELLED'}

# -----------------------------------------------------------------------------
# Original Operators (unchanged)
# -----------------------------------------------------------------------------
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
        
        # Si no hay objeto seleccionado, mostrar mensaje
        if not obj:
            layout.label(text="No object selected", icon='INFO')
            layout.label(text="Select an object to use Figure Tools")
            return
        
        # Is Figure toggle
        layout.prop(obj, "is_figure", text="Is Figure")
        
        layout.separator()
        layout.operator("figure_tools.launch_transform_tool", text="Transform Tools", icon='TOOL_SETTINGS')
        layout.separator()

        # Process Images button
        layout.operator("figure_tools.process_images", text="Process Images")
        
        # UV Map renaming
        layout.operator("figure_tools.rename_uvmaps", text="Rename UV Maps")

        layout.operator("object.add_volumifier", text="Volumifier")
        
        # Add the new Solidifier button
        layout.operator("object.add_solidifier", text="Solidifier")
        layout.operator("object.add_merger", text="Merger")

        layout.operator("figure_tools.generate_sv_eye_material", text="Generate SV Eye Material")
        layout.operator("figure_tools.bake_eye_texture", text="Bake Eye To PNG")
        layout.operator("figure_tools.bake_scvi_material", text="Bake SCVI Material")
        
        # Solo mostrar la sección de materiales para objetos mesh
        if obj.type == 'MESH':
            layout.separator()
            
            # Título siempre visible
            layout.label(text="Materials to combine:", icon='MATERIAL')
            
            # Verificar si tiene materiales
            if not obj.data or not obj.data.materials or len(obj.data.materials) == 0:
                layout.label(text="No materials found", icon='INFO')
                layout.label(text="Add materials to this object first")
                return
                
            # Verificar que mc_props existe
            if not hasattr(obj, 'mc_props'):
                layout.label(text="Error: Material properties not found", icon='ERROR')
                layout.label(text="Try reloading the addon")
                return
                
            mc = obj.mc_props
            
            # Always show sync button
            layout.operator("figure_tools.sync_materials", text="Sync Materials", icon='FILE_REFRESH')
            
            # Only show the list if we have materials and no resync flag
            if len(mc.materials) > 0 and not mc.needs_resync:
                layout.label(text=f"Found {len(mc.materials)} materials:")

                # Show list with minimal error handling
                try:
                    layout.template_list(
                        "MATERIAL_UL_combine_list",
                        "",
                        mc, "materials",
                        mc, "index",
                        rows=min(6, len(mc.materials))
                    )
                    
                    # Preview del material seleccionado (simplified)
                    if (0 <= mc.index < len(mc.materials) and 
                        mc.materials[mc.index].material):
                        
                        try:
                            selected_material = mc.materials[mc.index].material
                            
                            # Crear una caja para la preview
                            preview_box = layout.box()
                            preview_box.label(text=f"Preview: {selected_material.name}", icon='MATERIAL')
                            
                            # Template preview with error handling
                            try:
                                preview_box.template_preview(selected_material)
                                
                                # Basic material info
                                if hasattr(selected_material, 'use_nodes') and selected_material.use_nodes:
                                    preview_box.label(text="Uses Shader Nodes", icon='NODETREE')
                                else:
                                    preview_box.label(text="Legacy Material", icon='MATERIAL')
                            except:
                                preview_box.label(text="Preview unavailable", icon='INFO')
                                
                        except:
                            # If preview fails, just skip it - don't set resync flag
                            pass
                    
                    # Control buttons
                    row = layout.row(align=True)
                    row.operator("figure_tools.select_all_materials", text="Select All")
                    row.operator("figure_tools.deselect_all_materials", text="Deselect All")
                    
                    # Debug button
                    layout.operator("figure_tools.debug_selection", text="Debug Selection")
                    
                    # Combine button
                    layout.operator(
                        "figure_tools.combine_materials",
                        text="Combine Materials"
                    )
                    
                except Exception as e:
                    # If list fails, set resync flag but don't show error immediately
                    mc.needs_resync = True
                    layout.label(text="List needs refresh", icon='INFO')
            else:
                if mc.needs_resync:
                    layout.label(text="Materials need to be resynced", icon='INFO')
                else:
                    layout.label(text="Click 'Sync Materials' to load the list", icon='INFO')

# List of classes for registration
classes = [
    MaterialItem,
    MCProps,
    MATERIAL_UL_combine_list,
    OBJECT_OT_combine_materials,
    OBJECT_OT_sync_materials,
    OBJECT_OT_debug_selection,
    OBJECT_OT_select_all_materials,
    OBJECT_OT_deselect_all_materials,
    OBJECT_OT_rename_uvmaps,
    OBJECT_OT_process_images,
    OBJECT_OT_add_volumifier,
    OBJECT_OT_add_solidifier,
    OBJECT_OT_add_merger,
    OBJECT_OT_generate_sv_eye_material,
    OBJECT_OT_bake_eye_texture,
    OBJECT_OT_bake_scvi_material,
    OBJECT_OT_launch_transform_tool,
    VIEW3D_PT_upscale_tools,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register properties
    bpy.types.Object.is_figure = bpy.props.BoolProperty(
        name="Is Figure",
        description="Mark this object as a figure",
        default=False,
        update=on_figure_toggle
    )
    bpy.types.Object.mc_props = PointerProperty(type=MCProps)

def unregister():
    # Unregister properties
    if hasattr(bpy.types.Object, 'is_figure'):
        del bpy.types.Object.is_figure
    if hasattr(bpy.types.Object, 'mc_props'):
        del bpy.types.Object.mc_props
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()