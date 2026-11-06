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

import bpy
import os
import mathutils
import numpy as np

#
# Function Used
#

sizeLimits = {
    "FULLSIZE": [100.00, 100.00, 150.00],
    "DESKTOP": [22.50, 22.50, 30.00]
}

def saveImage(exportpath, image):
    try:
        image.file_format = "PNG"
        image.save(filepath=exportpath)
    except Exception as e:
        print(f"Failed to save image {exportpath}: {e}")

def exportOBJMaterials(obj, exportpath):
    if not obj or not obj.data or not hasattr(obj.data, "materials"):
        return

    for material in obj.data.materials:
        if not material or not material.use_nodes:
            continue

        existing_material_types = set()

        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:            
                image = node.image
                imagename = node.label or image.name

                settings = material.material_settings

                if not settings:
                    continue

                for setting in settings:
                    if setting.imageName != imagename or image.size[0] <= 0 or image.size[1] <= 0 or setting.materialType == "noexport":
                        continue

                    saveImage(os.path.join(exportpath, f"{setting.materialType}_{material.name}.png"), image)

                    if setting.materialType == "emissive":
                        diffuse_texture_path = os.path.join(exportpath, f"diffuse_{material.name}.png")

                        if not os.path.exists(diffuse_texture_path):
                            saveImage(diffuse_texture_path, image)

def selectAll(objects, select, type = {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}, selectUCX = False):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        if obj.type not in type:
            continue

        if not selectUCX and obj.name.startswith("UCX_"):
            continue
        obj.select_set(select)

def calculate_overall_bounding_box(selected_objects):
    if not selected_objects:
        return None

    all_corners = []

    for obj in selected_objects:
        if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
            continue

        local = np.array(obj.bound_box)                    # (8, 3)
        mw = np.array(obj.matrix_world)                    # (4, 4)
        world = local @ mw[:3, :3].T + mw[:3, 3]           # apply transform
        all_corners.append(world)

    if not all_corners:
        return None

    pts = np.concatenate(all_corners)
    return tuple(pts.max(axis=0) - pts.min(axis=0))

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

def save_properties_file(export_path, properties):
    properties_file_path = os.path.join(export_path, "properties.cfg")

    with open(properties_file_path, 'w') as f:
        # Texture properties
        for obj in bpy.context.selected_objects:
            if obj.type != 'MESH':
                continue

            for mat_slot in obj.material_slots:
                if not mat_slot.material:
                    continue

                for setting in mat_slot.material.material_settings:
                    f.write(f"filter_{setting.materialType}_{mat_slot.material.name}={setting.materialFilter}\n")

        # Misc properties
        for key, value in properties.items():
            if value is not None:
                f.write(f"{key}={value}\n")

def sizeCheck():
    TINY_THRESHOLDS = (10, 10, 15)
    properties = bpy.context.scene.votv_properties
    dims = calculate_overall_bounding_box(bpy.context.selected_objects)

    if dims is None:
        return "ERROR: No valid objects selected"

    limits = sizeLimits[bpy.context.scene.votv_properties.sizelimit]
    x, y, z = (round(d / 2, 3) for d in dims)
    maxX, maxY, maxZ = limits

    if x > maxX or y > maxY or z > maxZ:
        return (f"ERROR: Model is too big for printing\n"
                f"X = {x}, Max is {maxX}\n"
                f"Y = {y}, Max is {maxY}\n"
                f"Z = {z}, Max is {maxZ}")

    if x < TINY_THRESHOLDS[0] and y < TINY_THRESHOLDS[1] and z < TINY_THRESHOLDS[2]:
        return ("WARNING: Model is very tiny, it probably won't be able to be seen in-game due to its size\n"
                "Your model has still been exported to Voices of the Void")
    return "Success: Completed"

#
# Classes
#

class MaterialSettings(bpy.types.PropertyGroup):
    image : bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
        description="The image to be used for the material."
    )
    imageName : bpy.props.StringProperty(name="Image name", default="imageName")
    materialType : bpy.props.EnumProperty(
        name="Type",
        items=[
            ('noexport', "None", "This won't export a texture"),
            ('diffuse', "Diffuse", "The main texture of the object."),
            ('normal', "Normal", ""),
            ('emissive', "Emissive", ""),
            ('pbr', 'PBR', ""),
        ],
        default='diffuse'
    )
    materialFilter : bpy.props.EnumProperty(
        name="Filter",
        items=[
            ('0', "Nearest", ""),
            ('1', "Bilinear", "")
        ],
        default='0'
    )

class VOTVExporterPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    export_path : bpy.props.StringProperty(
        name="Export Path",
        default="",
        description="Define the default export path",
        subtype='DIR_PATH'
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "export_path")

class VOTVProperties(bpy.types.PropertyGroup):
    show_export:        bpy.props.BoolProperty(name="Export Settings", default=True)
    show_material:      bpy.props.BoolProperty(name="Materials", default=False)
    show_size:          bpy.props.BoolProperty(name="Size Settings", default=False)
    show_light:         bpy.props.BoolProperty(name="Light Settings", default=False)
    show_properties:    bpy.props.BoolProperty(name="Print Properties", default=False)

    modelname : bpy.props.StringProperty(
        name="Model name",
        default="",
        description="This will be your file name.\nWARNING: If exporting multiple objects it will instead use the object name rather than the file name."
    )
    export_prefix : bpy.props.StringProperty(
        name="Export Prefix (Not required)",
        default="",
        description="Define a prefix for the exported OBJ file names"
    )
    sizelimit : bpy.props.EnumProperty(
        name="Size Limit",
        description="Choose for which printer you want your object to print from",
        items=[
            ('FULLSIZE', "Industrial Printer", "Export the entire scene"),
            ('DESKTOP', "Desktop Printer", "Export only selected objects")
        ],
        default='FULLSIZE'
    )
    useAllUCX: bpy.props.BoolProperty(name="Use all collision meshes", default=False)
    limitbypass : bpy.props.BoolProperty(
        name="Bypass Size Limit",
        default=False
    )
    export_mode : bpy.props.EnumProperty(
        name="Export Mode",
        description="Choose how to export the objects",
        items=[
            ('SELECTED', "Combined selected Objects", "Export all selected objects into one object"),
            ('INDIVIDUAL', "Individual selected Objects", "Export all selected objects individually"),
            ('SCENE', "Scene", "Exports the entire scene as a printable object")
        ],
        default='SELECTED'
    )
    physical_material : bpy.props.EnumProperty(
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
    emissive_strength : bpy.props.FloatProperty(
        name="Emissive Strength",
        description="Strength of the emissive texture",
        default=0.0,
        min=0.0
    )
    lamp : bpy.props.BoolProperty(
        name="Lamp",
        default=False
    )
    lamp_color : bpy.props.FloatVectorProperty(
        name="Lamp Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0)
    )
    lamp_offset : bpy.props.FloatVectorProperty(
        name="Lamp Offset",
        subtype='XYZ',
        size=3,
        default=(0.0, 0.0, 0.0)
    )
    lamp_intensity : bpy.props.FloatProperty(
        name="Lamp Intensity",
        default=5000,
        min=0.0
    )
    lamp_attenuation : bpy.props.FloatProperty(
        name="Lamp Attenuation",
        default=2500,
        min=0.0
    )
    lamp_shadows : bpy.props.BoolProperty(
        name="Lamp Shadows",
        default=False
    )
    lamp_toggle : bpy.props.BoolProperty(
        name="Lamp Toggle",
        default=False
    )
    health : bpy.props.FloatProperty(
        name="Health (0 = Unbreakable)",
        default=0.0,
        min=0.0
    )
    impact_resistance : bpy.props.FloatProperty(
        name="Impact resistance",
        default=0.0,
        min=0.0
    )
    damage_resistance : bpy.props.FloatProperty(
        name="Damage resistance",
        default=0.0,
        min=0.0
    )

class CopyPosButton(bpy.types.Operator):
    bl_idname = "object.copy_position"
    bl_label = "Copy Position"
    bl_description = "Copy the position of the selected object to the lamp offset"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.mode == 'OBJECT'

    def execute(self, context):
        properties = context.scene.votv_properties
        active_object = context.active_object

        if active_object:
            properties.lamp_offset[0] = active_object.location.x
            properties.lamp_offset[1] = active_object.location.y
            properties.lamp_offset[2] = active_object.location.z
            self.report({'INFO'}, f"Copied position from {active_object.name} in lamp offset.")
            return {"FINISHED"}

        self.report({'WARNING'}, "No valid object selected.")
        return {"CANCELLED"}

class UpdateMaterialSettingsOperator(bpy.types.Operator):
    bl_idname = "material.update_settings"
    bl_label = "Update Material Settings"

    @classmethod
    def poll(cls, context):
        return context.selected_objects and context.mode == 'OBJECT'

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
               
            for mat_slot in obj.material_slots:
                if not mat_slot.material:
                    continue

                material = mat_slot.material
                if "material_settings" not in material:
                    material["material_settings"] = bpy.props.CollectionProperty(type=MaterialSettings)()

                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        imagename = node.label or node.image.name
                        exists = any(setting.image == node.image for setting in material.material_settings)

                        if not exists:
                            new_setting = material.material_settings.add()
                            new_setting.image = node.image
                            new_setting.imageName = imagename

        return {"FINISHED"}

class ClearMaterialSettingsOperator(bpy.types.Operator):
    bl_idname = "material.clear_settings"
    bl_label = "Clear Material Settings"

    @classmethod
    def poll(cls, context):
        return context.selected_objects and context.mode == 'OBJECT'

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    if mat_slot.material:
                        mat_slot.material.material_settings.clear()
        return {"FINISHED"}
    
#
# Main Export Function
#

# Set Name to None to select em all
def getUCX(view_layer, useAllUCX=False, name=None):
    collisions = []
    for o in view_layer.objects:
        print(o.name)
        if o.type != 'MESH' or not o.name.startswith("UCX_") or (name is not None and o.name[4:] not in name) or (o.hide_render and not useAllUCX):
            continue

        collisions.append(o)
    return collisions

def getExportObject(context, objects):
    view_layer = context.view_layer
 
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    view_layer.objects.active = objects[0]
 
    bpy.ops.object.duplicate()
    duplicates = list(context.selected_objects)
 
    view_layer.objects.active = duplicates[0]
    bpy.ops.object.convert(target='MESH')
    if len(duplicates) > 1:
        bpy.ops.object.join()
 
    return view_layer.objects.active

def removeObject(obj):
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)

def exportPrint(self, context, export_path, name, objects, collisions, properties, properties_file):
    prefixed_name = f"{properties.export_prefix}_{name}" if properties.export_prefix else name
    export_folder = os.path.join(export_path, prefixed_name)
    object_file_path = os.path.join(export_folder, f"{prefixed_name}.obj")
 
    exportObject = getExportObject(context, objects)
    try:
        bpy.ops.object.select_all(action='DESELECT')
        for collision in collisions:
            collision.select_set(True)

        exportObject.select_set(True)
        context.view_layer.objects.active = exportObject
 
        if not properties.limitbypass:
            result = sizeCheck()
            if "ERROR" in result:
                self.report({'ERROR'}, result)
                return False
            if "WARNING" in result:
                self.report({'WARNING'}, result)
 
        create_folder(self, export_folder)
        exportOBJ(self, object_file_path, True)
        exportOBJMaterials(exportObject, export_folder)
        save_properties_file(export_folder, properties_file)
        return True
    finally:
        # Runs on success, on cancel, and if anything above raises
        removeObject(exportObject)

class ExportButton(bpy.types.Operator):
    bl_idname = "object.export_print"
    bl_label = "Export OBJ"
    bl_description = "Export selected objects or the entire scene to OBJ format."

    @classmethod
    def poll(cls, context):
        return (context.selected_objects and context.mode == 'OBJECT') or (len(context.scene.votv_properties.modelname) > 0 and context.scene.votv_properties.export_mode != "INDIVIDUAL")

    def execute(self, context):
        properties = context.scene.votv_properties
        preferences = bpy.context.preferences.addons[__package__].preferences
        export_path = bpy.path.abspath(preferences.export_path)

        if not export_path:
            self.report({'ERROR'}, "Export path is not set.")
            return {"CANCELLED"}
        
        if not os.path.exists(export_path):
            self.report({'ERROR'}, "Export path does not exist.")
            return {"CANCELLED"}
        
        properties_file = {
            "physical_material": properties.physical_material,
            "emissive_strength": round(properties.emissive_strength, 3),
            "is_lamp": int(properties.lamp),
            "lamp_color": f"(R={round(properties.lamp_color[0], 3)},G={round(properties.lamp_color[1], 3)},B={round(properties.lamp_color[2], 3)})",
            "lamp_offset": f"(X={round(properties.lamp_offset[0], 3)},Y={round(-properties.lamp_offset[1], 3)},Z={round(properties.lamp_offset[2], 3)})",
            "lamp_intensity": round(properties.lamp_intensity, 3),
            "lamp_attenuation": round(properties.lamp_attenuation, 3),
            "lamp_shadows": int(properties.lamp_shadows),
            "health": round(properties.health, 3),
            "impact_resistance": round(properties.impact_resistance, 3),
            "damage_resistance": round(properties.damage_resistance, 3),
            "light_toggle": int(properties.lamp_toggle)
        }

        mode = properties.export_mode
        if mode == "INDIVIDUAL" and len(context.selected_objects) == 1:
            mode = "SELECTED"

        if mode == "SELECTED":
            bpy.context.view_layer.objects.active = context.selected_objects[0]

            name = properties.modelname or bpy.context.active_object.name
            if not exportPrint(self, bpy.context, export_path, name, context.selected_objects, getUCX(bpy.data, properties.useAllUCX, name), properties, properties_file):
                return {"CANCELLED"}

            bpy.ops.object.select_all(action='DESELECT')

            self.report({'INFO'}, f"Exported Selected")
                
        elif mode == "INDIVIDUAL":           
            for object in context.selected_objects:
                bpy.ops.object.select_all(action='DESELECT')

                if not exportPrint(self, bpy.context, export_path, object.name, [object], getUCX(bpy.data, properties.useAllUCX, object.name), properties, properties_file):
                    return {"CANCELLED"}
                    
                bpy.ops.object.select_all(action='DESELECT')

            self.report({'INFO'}, f"Exported Individual")

        elif mode == "SCENE":
            name = properties.modelname or bpy.context.active_object.name

            if not exportPrint(self, bpy.context, export_path, name, bpy.context.view_layer.objects, getUCX(bpy.data, properties.useAllUCX), properties, properties_file):
                return {"CANCELLED"}

            bpy.ops.object.select_all(action='DESELECT')

            self.report({'INFO'}, f"Exported Scene")
            
        return {"FINISHED"}
#
# Main GUI
#

class VOTVE_PT_mainGUI(bpy.types.Panel):
    bl_label = "VOTV Print Exporter"
    bl_idname = "VOTVE_PT_mainGUI"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VOTV Print Exporter"

    def draw(self, context):
        preferences = bpy.context.preferences.addons[__package__].preferences
        properties = context.scene.votv_properties

        layout = self.layout

        MainColumn = layout.box()

        # Export Settings
        # The fact I need to make my own panel logic for this to look good is fucking insane
        # Fuck you
        # Code heavily inspired by Falkener's from the "Ariral Maker v2" addon: https://jinxxy.com/Gigaroni/6uAoz

        exportSettingsBox = MainColumn.box()

        eSettingsRow = exportSettingsBox.row()
        eSettingsRow.prop(properties, "show_export", icon="TRIA_DOWN" if properties.show_export else "TRIA_RIGHT", icon_only=True, emboss=False)
        eSettingsRow.label(text="Export Settings", icon="EXPORT")

        if properties.show_export:
            exportSettingsRow = exportSettingsBox.row()
            exportSettingsRow.alert = not preferences.export_path or not os.path.isdir(preferences.export_path)
            exportSettingsRow.prop(preferences, "export_path")

            exportSettingsBox.prop(properties, "modelname")
            exportSettingsBox.prop(properties, "export_prefix")
            exportSettingsBox.prop(properties, "export_mode")
            exportSettingsBox.prop(properties, "useAllUCX")

        # Material Settings
        materialsSettingsBox = MainColumn.box()

        mSettingsRow = materialsSettingsBox.row()
        mSettingsRow.prop(properties, "show_material", icon="TRIA_DOWN" if properties.show_material else "TRIA_RIGHT", icon_only=True, emboss=False)
        mSettingsRow.label(text="Material settings:", icon='MATERIAL')

        if properties.show_material:
            if not context.selected_objects:
                materialsSettingsBox.label(text="Please select an object to see its material list", icon="INFO")
            else:
                materials = {}

                for obj in context.selected_objects:
                    if obj.type != 'MESH':
                        continue

                    for mat_slot in obj.material_slots:
                        material = mat_slot.material

                        if not material or material.name in materials:
                            continue

                        if not material.material_settings:
                            continue

                        materials[material.name] = material

                if not materials:
                    materialsSettingsBox.label(text="No materials with settings found.",icon='INFO')
                else:
                    for material_name, material in sorted(materials.items()):
                        materialBox = materialsSettingsBox.box()
                        material_header = materialBox.row()
                        material_header.label(text=material_name)

                        for setting in material.material_settings:
                            settingRow = materialBox.box().row(align=True)

                            settingRow.label(text=setting.imageName, icon='IMAGE_DATA')
                            settingRow.prop(setting, "materialType", text="")
                            settingRow.prop(setting, "materialFilter", text="")

            matButtonRow = materialsSettingsBox.row(align=True)
            matButtonRow.operator("material.update_settings",text="Update Materials",icon='FILE_REFRESH')
            matButtonRow.operator("material.clear_settings",text="Clear Materials",icon='TRASH')
        
        # Size Settings

        sizeSettingsBox = MainColumn.box()

        sSettingsRow = sizeSettingsBox.row()
        sSettingsRow.prop(properties, "show_size", icon="TRIA_DOWN" if properties.show_size else "TRIA_RIGHT", icon_only=True, emboss=False)
        sSettingsRow.label(text='Size settings:', icon="FIXED_SIZE")

        if properties.show_size:
            sizeLimitBox = sizeSettingsBox.box()
            curSizeLimit = sizeLimits[properties.sizelimit]

            sizeLimitBox.prop(properties, 'sizelimit')

            sizeSettingsRow = sizeLimitBox.row()
            sizeSettingsRow.box().label(text=f"X={curSizeLimit[0]}")
            sizeSettingsRow.box().label(text=f"Y={curSizeLimit[1]}")
            sizeSettingsRow.box().label(text=f"Z={curSizeLimit[2]}")
            
            dimensionBox = sizeSettingsBox.box()
            dimensionBox.label(text="Object dimensions are:")

            dimensionRow = dimensionBox.row()
            
            if context.selected_objects:
                bb_x, bb_y, bb_z = calculate_overall_bounding_box(context.selected_objects)
                x_dim = round(bb_x / 2, 3)
                y_dim = round(bb_y / 2, 3)
                z_dim = round(bb_z / 2, 3)
            else:
                x_dim, y_dim, z_dim = "0", "0", "0"

            dimensionRow.box().label(text=f"X={x_dim}")
            dimensionRow.box().label(text=f"Y={y_dim}")
            dimensionRow.box().label(text=f"Z={z_dim}")

            sizeSettingsBox.prop(properties, 'limitbypass')

        # Light Settings

        lightSettings = MainColumn.box()
        
        lSettingsRow = lightSettings.row()
        lSettingsRow.prop(properties, "show_light", icon="TRIA_DOWN" if properties.show_light else "TRIA_RIGHT", icon_only=True, emboss=False)
        lSettingsRow.label(text="Light settings:", icon='LIGHT')

        if properties.show_light:
            lightSettings.prop(properties, 'lamp', text="Enable Light")
            lampBox = lightSettings.box()   
            lampBox.enabled = properties.lamp

            lampBox.row().prop(properties, 'lamp_color', text="Light Color:")

            dimensionRow = lampBox.row()
            dimensionRow.label(text="Light Offset:")

            dimensionRow.operator(CopyPosButton.bl_idname, text="Copy Position to:")
            dimensionRow.enabled = bool(context.selected_objects)

            dimensionRow.prop(properties, 'lamp_offset', text="")

            lampBox.prop(properties, 'lamp_intensity', text="Light Intensity:")
            lampBox.prop(properties, 'lamp_attenuation', text="Light Attenuation:")
            lampBox.prop(properties, 'lamp_toggle', text="Light toggle")
            lampBox.prop(properties, 'lamp_shadows', text="Light Shadows")

        # Print Properties
        
        printProperties = MainColumn.box()
        pRow = printProperties.row()
        pRow.prop(properties, "show_properties", icon="TRIA_DOWN" if properties.show_properties else "TRIA_RIGHT", icon_only=True, emboss=False)
        pRow.label(text="Print properties:", icon='TOOL_SETTINGS')

        if properties.show_properties:
            printProperties.prop(properties, "emissive_strength")
            printProperties.prop(properties, "health")
            printProperties.prop(properties, "damage_resistance")
            printProperties.prop(properties, "impact_resistance")
            printProperties.prop(properties, "physical_material")

        rowExport = MainColumn.row()
        rowExport.scale_y = 2
        rowExport.operator(ExportButton.bl_idname, text="Export Objects", icon="EXPORT")

classes = (
    VOTVExporterPreferences, 
    VOTVProperties, 
    MaterialSettings, 
    ExportButton, 
    CopyPosButton, 
    UpdateMaterialSettingsOperator, 
    VOTVE_PT_mainGUI, 
    ClearMaterialSettingsOperator
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Material.material_settings = bpy.props.CollectionProperty(type=MaterialSettings)
    bpy.types.Scene.votv_properties = bpy.props.PointerProperty(type=VOTVProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.votv_properties