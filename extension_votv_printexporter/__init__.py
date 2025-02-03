# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy  # type: ignore
import os
import mathutils # type: ignore
import numpy as np # type: ignore

def calculate_overall_bounding_box(selected_objects):
    if not selected_objects:
        return None

    # Initialize min and max vectors
    min_bound = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_bound = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))

    # Iterate over selected objects
    for obj in selected_objects:
        if obj.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
            # Get the world space bounding box corners
            bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
            # Update min and max bounds
            for corner in bbox_corners:
                min_bound.x = min(min_bound.x, corner.x)
                min_bound.y = min(min_bound.y, corner.y)
                min_bound.z = min(min_bound.z, corner.z)
                max_bound.x = max(max_bound.x, corner.x)
                max_bound.y = max(max_bound.y, corner.y)
                max_bound.z = max(max_bound.z, corner.z)

    # Calculate overall dimensions
    overall_dimensions = (max_bound.x - min_bound.x, max_bound.z - min_bound.z, max_bound.y - min_bound.y)
    return overall_dimensions

def getSizeLimit(limitIdentifier):
    return [100.00, 100.00, 150.00] if limitIdentifier == "FULLSIZE" else [22.50, 22.50, 30.00]

def exportOBJ(self, file_path, exportSelected):
    try:
        export_func = bpy.ops.wm.obj_export if bpy.app.version >= (4, 0, 0) else bpy.ops.export_scene.obj
        export_func(filepath=file_path, export_selected_objects=exportSelected)
    except:
        self.report({'ERROR'}, "Export path does not exist.")
        return {"CANCELLED"}

def create_folder(self, folder_path):
    try:
        os.makedirs(folder_path, exist_ok=True)
    except Exception:
        self.report({'ERROR'}, "Could not create folder.")

def applyShapeKeys(obj):
    if not hasattr(obj.data, "shape_keys"):
        return {"CANCELLED"}
    obj.shape_key_add(name='CombinedKeys', from_mix=True)
    if obj.data.shape_keys:
        for shapeKey in obj.data.shape_keys.key_blocks:
            obj.shape_key_remove(shapeKey)

def save_properties_file(export_path, properties):
    properties_file_path = os.path.join(export_path, "properties.cfg")
    with open(properties_file_path, 'w') as f:
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    if mat_slot.material:
                        for setting in mat_slot.material.material_settings:
                            f.write(f"filter_{setting.materialType}_{mat_slot.material.name}={setting.materialFilter}\n")
        for key, value in properties.items():
            if value is not None:
                f.write(f"{key}={value}\n")

def combine_channels(metallic_img=None, roughness_img=None, specular_img=None):
    if metallic_img:
        width, height = metallic_img.size
    elif roughness_img:
        width, height = roughness_img.size
    elif specular_img:
        width, height = specular_img.size
    else:
        return {"CANCELLED"}

    combined_img = bpy.data.images.new('CombinedImage', width=width, height=height)
    metallic_pixels = np.array(metallic_img.pixels[:]) if metallic_img else np.zeros((width * height * 4,), dtype=np.float32)
    roughness_pixels = np.array(roughness_img.pixels[:]) if roughness_img else np.zeros((width * height * 4,), dtype=np.float32)
    subsurface_weight_pixels = np.array(specular_img.pixels[:]) if specular_img else np.zeros((width * height * 4,), dtype=np.float32)

    combined_pixels = np.zeros((width * height * 4,), dtype=np.float32)
    combined_pixels[0::4] = metallic_pixels[0::4]  # Red channel
    combined_pixels[1::4] = subsurface_weight_pixels[1::4]  # Green channel
    combined_pixels[2::4] = roughness_pixels[2::4]  # Blue channel
    combined_pixels[3::4] = 1.0  # Alpha channel (fully opaque)

    combined_img.pixels = combined_pixels.tolist()
    return combined_img

class MaterialSettings(bpy.types.PropertyGroup):
    imageFilepath: bpy.props.StringProperty(name="Image Filepath", default="imageFilepath")  # type: ignore
    imageName: bpy.props.StringProperty(name="Image name", default="imageName")  # type: ignore
    materialType: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('diffuse', "Diffuse", "The main texture of the object."),
            ('normal', "Normal", ""),
            ('emissive', "Emissive", ""),
            ('PBR_roughness', "Roughness", ""),
            ('PBR_metalic', "Metalic", ""),
            ('PBR_specular', "Specular", "")
        ],
        default='diffuse'
    )  # type: ignore

    materialFilter: bpy.props.EnumProperty(
        name="Filter",
        items=[
            ('0', "Nearest", ""),
            ('1', "Bilinear", "")
        ],
        default='0'
    )  # type: ignore

class VOTVExporterPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    export_path: bpy.props.StringProperty(
        name="Export Path",
        default="",
        description="Define the default export path",
        subtype='DIR_PATH'
    )  # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "export_path")

class copyPosButton(bpy.types.Operator):
    bl_idname = "object.copy_position"
    bl_label = "Copy Position"
    bl_description = "Copy the position of the selected object to the lamp offset"

    def execute(self, context):
        active_object = context.active_object
        if active_object:
            context.scene.lamp_offset_x = active_object.location.x
            context.scene.lamp_offset_y = active_object.location.y
            context.scene.lamp_offset_z = active_object.location.z
            self.report({'INFO'}, f"Copied position from {active_object.name} in lamp offset.")
            return {"FINISHED"}
        self.report({'WARNING'}, "No valid object selected.")
        return {"CANCELLED"}

class UpdateMaterialSettingsOperator(bpy.types.Operator):
    bl_idname = "material.update_settings"
    bl_label = "Update Material Settings"

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    if mat_slot.material:
                        material = mat_slot.material
                        if "material_settings" not in material:
                            material["material_settings"] = bpy.props.CollectionProperty(type=MaterialSettings)()

                        for node in material.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                imagename = node.label or node.image.name
                                exists = any(setting.imageFilepath == node.image.filepath_raw for setting in material.material_settings)

                                if not exists:
                                    new_setting = material.material_settings.add()
                                    new_setting.imageFilepath = node.image.filepath_raw
                                    new_setting.imageName = imagename

        return {"FINISHED"}

class ClearMaterialSettingsOperator(bpy.types.Operator):
    bl_idname = "material.clear_settings"
    bl_label = "Clear Material Settings"

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    if mat_slot.material:
                        mat_slot.material.material_settings.clear()
        return {"FINISHED"}

def saveImage(exportpath, image):
    try:
        image.file_format = "PNG"
        image.save(filepath=exportpath)
    except Exception as e:
        print(f"Failed to save image {exportpath}: {e}")

def exportOBJMaterials(obj, exportpath):
    for material in obj.data.materials:
        if material and material.use_nodes:
            pbrmats = []
            existing_material_types = set()
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    image = node.image
                    imagename = node.label or image.name
                    if image.size[0] > 0 and image.size[1] > 0:
                        for setting in material.material_settings:
                            if setting.imageName == imagename:
                                if setting.materialType.startswith("PBR") and setting.materialType not in existing_material_types:
                                    pbrmats.append((setting.materialType, image))
                                    existing_material_types.add(setting.materialType)
                                else:
                                    texture_path = os.path.join(exportpath, f"{setting.materialType}_{material.name}.png")
                                    saveImage(texture_path, image)

                                    if setting.materialType == "emissive":
                                        diffuse_texture_path = os.path.join(exportpath, f"diffuse_{material.name}.png")
                                        # Check if the file already exists
                                        if not os.path.exists(diffuse_texture_path):
                                            saveImage(diffuse_texture_path, image)

            if pbrmats:
                metallic_img = next((img for mat_type, img in pbrmats if mat_type == "PBR_metallic"), None)
                roughness_img = next((img for mat_type, img in pbrmats if mat_type == "PBR_roughness"), None)
                subsurface_weight_img = next((img for mat_type, img in pbrmats if mat_type == "PBR_specular"), None)

                pbrimage = combine_channels(metallic_img, roughness_img, subsurface_weight_img)
                saveImage(os.path.join(exportpath, f"pbr_{material.name}.png"), pbrimage)

def sizeCheck():
    returnMsg = "Success: Completed"
    sizeLimit = getSizeLimit(bpy.context.scene.sizelimit)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj.name in bpy.context.view_layer.objects:
            obj.select_set(True)

    bpy.ops.object.duplicate()
    duplicatedObjects = bpy.context.selected_objects

    for dupeObj in duplicatedObjects:
        for modifier in dupeObj.modifiers:
            try:
                bpy.context.view_layer.objects.active = dupeObj
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            except Exception as e:
                print(f"Failed to apply modifier {modifier.name}: {e}")

    bpy.context.view_layer.objects.active = duplicatedObjects[0]
    bpy.ops.object.join()
    joinedObject = bpy.context.selected_objects[0]

    bpy.ops.object.select_all(action='DESELECT')
    joinedObject.select_set(True)
    bpy.context.view_layer.objects.active = joinedObject

    dimensions = [round(joinedObject.dimensions.x / 2, 3), round(joinedObject.dimensions.y / 2, 3), round(joinedObject.dimensions.z / 2, 3)]
    if any(dim > limit for dim, limit in zip(dimensions, sizeLimit)):
        returnMsg = f"ERROR: Model is too big for printing\nX = {dimensions[0]}, Max is {sizeLimit[0]}\nY = {dimensions[1]}, Max is {sizeLimit[1]}\nZ = {dimensions[2]}, Max is {sizeLimit[2]}"

    if all(dim < threshold for dim, threshold in zip(dimensions, [15, 15, 20])):
        returnMsg = "WARNING: Model is very tiny, it probably won't be able to be seen in-game due to its size\nYour model has still been exported to Voices of the Void"

    bpy.ops.object.delete(use_global=False)
    return returnMsg

class ExportButton(bpy.types.Operator):
    bl_idname = "object.export_obj"
    bl_label = "Export OBJ"
    

    def execute(self, context):
        name = None

        preferences = bpy.context.preferences.addons[__name__ ].preferences
        export_path = bpy.path.abspath(preferences.export_path)
        prefix = context.scene.export_prefix
        export_mode = context.scene.export_mode

        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if not export_path:
            self.report({'ERROR'}, "Export path is not set.")
            return {"CANCELLED"}
        
        if not os.path.exists(export_path):
            self.report({'ERROR'}, "Export path does not exist.")
            return {"CANCELLED"}

        exported_count = 0
        collision_count = 0
        skipped_count = 0
        
        properties = {
            "physical_material": context.scene.physical_material,
            "emissive_strength": context.scene.emissive_strength,
            "is_lamp": int(context.scene.lamp),
            "lamp_color": f"(R={round(context.scene.lamp_color[0], 3)},G={round(context.scene.lamp_color[1], 3)},B={round(context.scene.lamp_color[2], 3)})",
            "lamp_offset": f"(X={round(context.scene.lamp_offset_x, 3)},Y={round(context.scene.lamp_offset_y*-1)},Z={round(context.scene.lamp_offset_z, 3)})",
            "lamp_intensity": context.scene.lamp_intensity,
            "lamp_attenuation": context.scene.lamp_attenuation,
            "lamp_shadows": int(context.scene.lamp_shadows),
        }
        try:
            if export_mode == 'SELECTED' or (export_mode == 'INDIVIDUAL' and len(context.selected_objects) == 1):
                bpy.context.view_layer.objects.active = context.selected_objects[0]

                if context.scene.modelname:
                    name = context.scene.modelname
                else: 
                    name = bpy.context.active_object.name

                prefixedName = f"{prefix}_{name}" if prefix else name

                export_folder = os.path.join(export_path, prefixedName)
                create_folder(self, export_folder)  # Create the folder for the scene
                
                object_file_path = os.path.join(export_folder, f"{prefixedName}.obj")

                bpy.ops.object.duplicate()

                duplicatedObjects = context.selected_objects

                for object in duplicatedObjects:
                    applyShapeKeys(object)
                    for modifier in object.modifiers:
                        try:
                            # Apply the modifier
                            bpy.context.view_layer.objects.active = object
                            bpy.ops.object.modifier_apply(modifier=modifier.name)
                        except Exception as e:
                            print(f"Failed to apply modifier {modifier.name}: {e}")

                    object.select_set(True)                
                
                bpy.context.view_layer.objects.active = duplicatedObjects[0]
                bpy.ops.object.join()
                joinedObject = bpy.context.active_object

                sizeCheckReturn = sizeCheck()

                if not context.scene.limitbypass:
                    sizeCheckReturn = sizeCheck()

                    if "ERROR" in sizeCheckReturn:
                        self.report({'ERROR'}, sizeCheckReturn)
                        return {"CANCELLED"}
                    elif "WARNING" in sizeCheckReturn:
                        self.report({'ERROR'}, sizeCheckReturn)

                bpy.ops.object.select_all(action='DESELECT')

                for collision in bpy.context.scene.objects:
                    if collision.type == 'MESH' and collision.name.startswith("UCX_") and name in collision.name and collision.name in bpy.context.view_layer.objects:
                        collision.select_set(True)
                        collision_count += 1
                
                joinedObject.select_set(True)
                bpy.context.view_layer.objects.active = joinedObject
                
                exportOBJ(self, object_file_path, True)
                exportOBJMaterials(joinedObject, export_folder)

                bpy.ops.object.select_all(action='DESELECT')
                joinedObject.select_set(True)

                save_properties_file(export_folder, properties)

                bpy.ops.object.delete(use_global=False)

                self.report({'INFO'}, f"Exported selected object(s) with {collision_count} collision object(s) and skipped {skipped_count} non-mesh object(s).")
            elif export_mode == 'INDIVIDUAL':

                if not context.selected_objects:
                    self.report({'ERROR'}, "No objects selected for export")
                    return {"CANCELLED"}

                selected_objects = context.selected_objects

                for object in selected_objects:
                    if object.name in bpy.context.view_layer.objects:
                        name = object.name
                        prefixedName = f"{prefix}_{name}" if prefix else name

                        export_folder = os.path.join(export_path, prefixedName)
                        create_folder(self, export_folder)  # Create the folder for the scene

                        object_file_path = os.path.join(export_folder, f"{prefixedName}.obj")
                        
                        bpy.ops.object.select_all(action='DESELECT')
                        object.select_set(True)
                        bpy.context.view_layer.objects.active = object
                        bpy.ops.object.duplicate()

                        duplicatedObject = bpy.context.active_object

                        bpy.ops.object.select_all(action='DESELECT')

                        for collision in bpy.context.scene.objects:
                            if collision.type == 'MESH' and collision.name.startswith("UCX_") and name in collision.name and collision.name in bpy.context.view_layer.objects:
                                collision.select_set(True)
                                collision_count += 1
                                
                        duplicatedObject.select_set(True)
                        bpy.context.view_layer.objects.active = duplicatedObject

                        exportOBJ(self, object_file_path, True)
                        exportOBJMaterials(duplicatedObject, export_folder)
                        save_properties_file(export_folder, properties)

                        bpy.ops.object.select_all(action='DESELECT')
                        duplicatedObject.select_set(True)
                        bpy.context.view_layer.objects.active = duplicatedObject
                        bpy.ops.object.delete(use_global=False)

                        exported_count+=1
                self.report({'INFO'}, f"Exported {exported_count} individual object(s) with {collision_count} collision object(s) and skipped {skipped_count} non-mesh object(s).")

            elif export_mode == 'SCENE':
                name = context.scene.modelname or bpy.context.active_object.name

                prefixedName = f"{prefix}_{name}" if prefix else name

                export_folder = os.path.join(export_path, prefixedName)
                create_folder(self, export_folder)  # Create the folder for the scene
                
                object_file_path = os.path.join(export_folder, f"{prefixedName}.obj")


                bpy.ops.object.select_all(action='DESELECT')
                for obj in context.scene.objects:
                    if obj.type == 'MESH' and not obj.name.startswith("UCX_") and obj.name in bpy.context.view_layer.objects:
                        obj.select_set(True)

                bpy.ops.object.duplicate()

                duplicatedObjects = context.selected_objects

                for object in duplicatedObjects:
                    applyShapeKeys(object)
                    for modifier in object.modifiers:
                        try:
                            # Apply the modifier
                            bpy.context.view_layer.objects.active = object
                            bpy.ops.object.modifier_apply(modifier=modifier.name)
                        except Exception as e:
                            print(f"Failed to apply modifier {modifier.name}: {e}")

                    object.select_set(True)                
                
                bpy.context.view_layer.objects.active = duplicatedObjects[0]
                bpy.ops.object.join()
                joinedObject = bpy.context.active_object

                sizeCheckReturn = sizeCheck()

                if not context.scene.limitbypass:
                        sizeCheckReturn = sizeCheck()

                        if "ERROR" in sizeCheckReturn:
                            self.report({'ERROR'}, sizeCheckReturn)
                            return {"CANCELLED"}
                        elif "WARNING" in sizeCheckReturn:
                            self.report({'ERROR'}, sizeCheckReturn)

                bpy.ops.object.select_all(action='DESELECT')

                for collision in bpy.context.scene.objects:
                    if collision.type == 'MESH' and collision.name.startswith("UCX_") and collision.name in bpy.context.view_layer.objects:
                        collision.select_set(True)
                        collision_count += 1
                
                joinedObject.select_set(True)
                bpy.context.view_layer.objects.active = joinedObject
                
                exportOBJ(self, object_file_path, True)
                exportOBJMaterials(joinedObject, export_folder)
                save_properties_file(export_folder, properties)

                bpy.ops.object.select_all(action='DESELECT')
                joinedObject.select_set(True)
                bpy.context.view_layer.objects.active = joinedObject
                bpy.ops.object.delete(use_global=False)

                self.report({'INFO'}, f"Exported  scene with {collision_count} collision object(s) and skipped {skipped_count} non-mesh object(s).")
        except Exception as e:
            self.report({'ERROR'}, f"An error occured during the export!\n{e}")
        return {"FINISHED"}

class VOTVE_PT_mainGUI(bpy.types.Panel):
    bl_label = "VOTV Print Exporter"
    bl_idname = "VOTVE_PT_mainGUI"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VOTV Print Exporter"

    def draw(self, context):
        layout = self.layout
        MainColumn = layout.column()
        MainColumn.label(text=("Selected object(s): " + ", ".join(obj.name for obj in context.selected_objects)) if context.selected_objects else "No object selected")

        dimensionRow = MainColumn.row()
        dimensionRow.label(text="Object dimensions are:")
        
        if context.selected_objects:
            overall_width, overall_height, overall_depth = calculate_overall_bounding_box(context.selected_objects)
            x_dim = round(overall_width / 2, 3)
            y_dim = round(overall_height / 2, 3)
            z_dim = round(overall_depth / 2, 3)
        else:
            x_dim, y_dim, z_dim = "0", "0", "0"

        dimensionRow.box().label(text=f"X={x_dim}")
        dimensionRow.box().label(text=f"Y={y_dim}")
        dimensionRow.box().label(text=f"Z={z_dim}")

        MainColumn.separator()
        MainColumn.prop(context.scene, 'modelname')
        MainColumn.prop(context.scene, 'export_prefix')
        MainColumn.prop(context.scene, 'export_mode')
        MainColumn.separator()
        MainColumn.prop(context.scene, 'sizelimit')
        MainColumn.prop(context.scene, 'limitbypass')
        
        MainColumn.separator()
        rowExport = MainColumn.row()
        rowExport.operator(ExportButton.bl_idname, text="Export Objects")
        rowExport.enabled = bool(context.selected_objects or context.scene.modelname)

class VOTVE_PT_properties(bpy.types.Panel):
    bl_label = "Properties:"
    bl_parent_id = "VOTVE_PT_mainGUI"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VOTV Print Exporter"
    bl_options = {"DEFAULT_CLOSED"}

    def draw (self, context):
        layout = self.layout
        layout.prop(context.scene, "physical_material")
        layout.prop(context.scene, "emissive_strength")

        propertiesBox = layout.box()
        propertiesBox.label(text="Materials:")
        materialsBox = propertiesBox.box()

        selected_objects = context.selected_objects
        curMats = set()

        if selected_objects:
            for obj in selected_objects:
                if obj.type == 'MESH':
                    for mat_slot in obj.material_slots:
                        if mat_slot.material:
                            material_settings = mat_slot.material.material_settings
                            if not material_settings:
                                materialsBox.row().label(text="No materials settings, please update the materials")
                                break
                            
                            if mat_slot.material.name not in curMats:
                                curMats.add(mat_slot.material.name)
                                box = materialsBox.box()
                                box.label(text=f"{mat_slot.material.name}:")
                                for setting in material_settings:
                                    materialRow = box.row()
                                    materialRow.label(text=setting.imageName)
                                    materialRow.prop(setting, "materialType", text="Type")
                                    materialRow.prop(setting, "materialFilter", text="Filter")
                else:
                    materialsBox.row().label(text="One or more objects in selection cannot contain materials")
        else:
            materialsBox.row().label(text="No object selected.")

        matButtonRow = propertiesBox.row()
        matButtonRow.operator("material.update_settings", text="Update materials")
        matButtonRow.operator("material.clear_settings", text="Clear materials")

class VOTVE_PT_lightProperties(bpy.types.Panel):
    bl_label = "Light settings:"
    bl_parent_id = "VOTVE_PT_mainGUI"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VOTV Print Exporter"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, 'lamp', text="Enable Light")

        lampBox = layout.box()   
        lampBox.enabled = context.scene.lamp

        colorRow = lampBox.row()
        colorRow.prop(context.scene, 'lamp_color', text="Light Color:")

        dimensionRow = lampBox.row()
        dimensionRow.label(text="Light Offset:")
        button = dimensionRow.column()
        button.operator(copyPosButton.bl_idname, text="Copy Position to:")
        button.enabled = bool(context.selected_objects)

        dimensionRow.prop(context.scene, 'lamp_offset_x', text="X")
        dimensionRow.prop(context.scene, 'lamp_offset_y', text="Y")
        dimensionRow.prop(context.scene, 'lamp_offset_z', text="Z")

        lampBox.prop(context.scene, 'lamp_intensity', text="Light Intensity:")
        lampBox.prop(context.scene, 'lamp_attenuation', text="Light Attenuation:")
        lampBox.prop(context.scene, 'lamp_shadows', text="Light Shadows:")

classes = (ClearMaterialSettingsOperator, UpdateMaterialSettingsOperator, MaterialSettings, ExportButton, VOTVE_PT_mainGUI, VOTVE_PT_properties, VOTVE_PT_lightProperties, VOTVExporterPreferences, copyPosButton)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Material.material_settings = bpy.props.CollectionProperty(type=MaterialSettings)

    bpy.types.Scene.modelname = bpy.props.StringProperty(
        name="Model name",
        default="",
        description="This will be your file name.\nWARNING: If exporting multiple objects it will instead use the object name rather than the file name."
    )

    bpy.types.Scene.export_prefix = bpy.props.StringProperty(
        name="Export Prefix (Not required)",
        default="",
        description="Define a prefix for the exported OBJ file names"
    )
    
    bpy.types.Scene.sizelimit = bpy.props.EnumProperty(
        name="Size Limit",
        description="Choose for which printer you want your object to print from",
        items=[
            ('FULLSIZE', "Industrial Printer", "Export the entire scene"),
            ('DESKTOP', "Desktop Printer", "Export only selected objects")
        ],
        default='FULLSIZE'
    )

    bpy.types.Scene.limitbypass = bpy.props.BoolProperty(
        name="Bypass Size Limit?",
        default=False
    )

    bpy.types.Scene.export_mode = bpy.props.EnumProperty(
        name="Export Mode",
        description="Choose how to export the objects",
        items=[
            ('SELECTED', "Selected Objects", "Export all selected objects into one object"),
            ('INDIVIDUAL', "Individual Objects", "Export all selected objects individually\nWARNING: DOES NOT SUPPORT SHAPE KEYS"),
            ('SCENE', "Whole Scene", "Exports the entire scene")
        ],
        default='SELECTED'
    )

    bpy.types.Scene.physical_material = bpy.props.EnumProperty(
        name="Physical Material",
        items=[
            ('0', "Default", ""),
            ('1', "Wood", ""),
            ('2', "Metal", ""),
            ('9', "Metal (alternate)", ""),
            ('6', "Hollow metal", ""),
            ('13', "Heavy Metal", ""),
            ('4', "Rubber", ""),
            ('15', "Rubber (alternate)", ""),
            ('3', "Concrete", ""),
            ('5', "Paper", ""),
            ('7', "Flesh", ""),
            ('11', "Glass", ""),
            ('12', "Cardboard", ""),
            ('10', "Pinecone", ""),
            ('8', "Food (Edible)", ""),
            ('14', "No Sound", ""),
        ],
        default='0'
    )
    
    bpy.types.Scene.emissive_strength = bpy.props.FloatProperty(
        name="Emissive Strength",
        default=0.0,
        min=0.0
    )
    
    bpy.types.Scene.lamp = bpy.props.BoolProperty(
        name="Lamp",
        default=False
    )
    
    bpy.types.Scene.lamp_color = bpy.props.FloatVectorProperty(
        name="Lamp Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0)
    )
    
    bpy.types.Scene.lamp_offset_x = bpy.props.FloatProperty(
        name="Lamp Offset X",
        default=0.0
    )
    
    bpy.types.Scene.lamp_offset_y = bpy.props.FloatProperty(
        name="Lamp Offset Y",
        default=0.0
    )
    
    bpy.types.Scene.lamp_offset_z = bpy.props.FloatProperty(
        name="Lamp Offset Z",
        default=0.0
    )
    
    bpy.types.Scene.lamp_intensity = bpy.props.FloatProperty(
        name="Lamp Intensity",
        default=5000,
        min=0.0
    )
    
    bpy.types.Scene.lamp_attenuation = bpy.props.FloatProperty(
        name="Lamp Attenuation",
        default=2500,
        min=0.0
    )
    
    bpy.types.Scene.lamp_shadows = bpy.props.BoolProperty(
        name="Lamp Shadows",
        default=False
    )

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Material.material_settings
    del bpy.types.Scene.export_prefix
    del bpy.types.Scene.export_mode
    del bpy.types.Scene.physical_material
    del bpy.types.Scene.emissive_strength
    del bpy.types.Scene.lamp
    del bpy.types.Scene.lamp_color
    del bpy.types.Scene.lamp_offset_x
    del bpy.types.Scene.lamp_offset_y
    del bpy.types.Scene.lamp_offset_z
    del bpy.types.Scene.lamp_intensity
    del bpy.types.Scene.lamp_attenuation
    del bpy.types.Scene.lamp_shadows