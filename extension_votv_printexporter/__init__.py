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

import bpy # type: ignore
import os

def getSizeLimit(limitIdentifier):
    if limitIdentifier == "FULLSIZE":
        return [ 100.00, 100.00, 150.00 ]
    elif limitIdentifier == "DESKTOP":
        return [ 22.50, 22.50, 30.00 ]
    
def exportOBJ(self, file_path, exportSelected):
    try:
        if bpy.app.version >= (4, 0, 0):
            bpy.ops.wm.obj_export(filepath=file_path, export_selected_objects=exportSelected)
        else:
            bpy.ops.export_scene.obj(filepath=file_path, use_selection=exportSelected)
    except:
        self.report({'ERROR'}, "Export path does not exist.")
        return {"CANCELLED"}
        
def create_folder(self, folder_path):
    try:
        os.makedirs(folder_path, exist_ok=True)
    except Exception as e:
        self.report({'ERROR'}, "Could not create folder.")

def save_texture_as_png(material, export_path, object_name):
    if material and material.use_nodes:
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                image = node.image
                if image:
                    texture_path = os.path.join(export_path, f"{object_name}.png")
                    
                    if bpy.app.version > (3, 0, 0):
                        image.file_format = "PNG"
                        image.save(filepath=texture_path)
                    else:
                        image.file_format = "PNG"
                        image.save_render(filepath = texture_path)

def save_properties_file(export_path, properties):
    properties_file_path = os.path.join(export_path, "properties.cfg")
    with open(properties_file_path, 'w') as f:
        materials = []

        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    if mat_slot.material:
                        material_settings = mat_slot.material.material_settings

                        if not material_settings:
                            continue
                                
                        for i, setting in enumerate(material_settings):
                            if not any(materialName == setting.materialName for materialName in materials):
                                materials.append(setting.materialName)
                                f.write(f"filter_{setting.materialType}_{setting.materialName}={setting.materialFilter}\n")

        for key, value in properties.items():
            if value is not None:
                f.write(f"{key}={value}\n")
    
###
### Classes:
###

class MaterialSettings(bpy.types.PropertyGroup):
    materialName: bpy.props.StringProperty(name="Material Name", default="materialName")  # type: ignore
    materialType: bpy.props.EnumProperty(
        name="Type",
        description="",
        items=[
            ('diffuse', "Diffuse", "The main texture of the object."),
            ('pbr', "PBR", ""),
            ('normal', "Normal", ""),
            ('emissive', "Emissive", "")
        ],
        default='diffuse'
    )  # type: ignore

    materialFilter: bpy.props.EnumProperty(
        name="Filter",
        description="",
        items=[
            ('0', "Nearest", ""),
            ('1', "Bilinear", "")
        ],
        default='0'
    )  # type: ignore

class VOTVExporterPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__ 

    export_path: bpy.props.StringProperty(
        name = "Export Path",
        default="",
        description="Define the default export path",
        subtype='DIR_PATH'
    ) # type: ignore

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
        else:
            self.report({'WARNING'}, "No valid object selected.")
            return {"CANCELLED"}
        
class UpdateMaterialSettingsOperator(bpy.types.Operator):
    bl_idname = "material.update_settings"
    bl_label = "Update Material Settings"

    def execute(self, context):
        selected_objects = context.selected_objects

        for obj in selected_objects:
            if obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    if mat_slot.material:
                        if "material_settings" in mat_slot.material:
                            for i, setting in enumerate(mat_slot.material.material_settings):
                                if setting.materialName != mat_slot.material.name:
                                    setting.materialName = mat_slot.material.name
                        else:
                            mat_slot.material["material_settings"] = bpy.props.CollectionProperty(type=MaterialSettings)()
                            new_setting = mat_slot.material.material_settings.add()
                            new_setting.materialName = mat_slot.material.name

                        

        return {"FINISHED"}

def exportOBJMaterials(obj, exportpath):
    for material in obj.data.materials:
        if material:
            material_settings = material.material_settings
            for i, setting in enumerate(material_settings):
                save_texture_as_png(material, exportpath, f"{setting.materialType}_{material.name}")
                if setting.materialType == "emissive":
                    save_texture_as_png(material, exportpath, f"diffuse_{material.name}")

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
                # Apply the modifier
                bpy.context.view_layer.objects.active = dupeObj
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            except Exception as e:
                print(f"Failed to apply modifier {modifier.name}: {e}")

        dupeObj.select_set(True)                
    
    bpy.context.view_layer.objects.active = duplicatedObjects[0]
    bpy.ops.object.join()

    joinedObject = bpy.context.selected_objects[0]

    bpy.ops.object.select_all(action='DESELECT')
    joinedObject.select_set(True)
    bpy.context.view_layer.objects.active = joinedObject

    if round(joinedObject.dimensions.x / 2, 3) > sizeLimit[0] or \
       round(joinedObject.dimensions.y / 2, 3) > sizeLimit[1] or \
       round(joinedObject.dimensions.z / 2, 3) > sizeLimit[2]:
        returnMsg = f"ERROR: Model is too big for printing\nX = {round(joinedObject.dimensions.x / 2, 3)}, Max is {sizeLimit[0]}\nY = {round(joinedObject.dimensions.y / 2, 3)}, Max is {sizeLimit[1]}\nZ = {round(joinedObject.dimensions.z / 2, 3)}, Max is {sizeLimit[2]}"

    if round(joinedObject.dimensions.x / 2, 3) < 15 and \
       round(joinedObject.dimensions.y / 2, 3) < 15 and \
       round(joinedObject.dimensions.z / 2, 3) < 20:
        returnMsg = f"WARNING: Model is very tiny, it probably won't be able to be seen in-game due to its size\nYour model has still been export to Voices of the Void"

    bpy.ops.object.delete(use_global=False)

    return returnMsg

class ExportButton(bpy.types.Operator):
    bl_idname = "object.export_obj"
    bl_label = "Export OBJ"
    
    def execute(self, context):
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
            "lamp_color": f"(R={context.scene.lamp_color[0]},G={context.scene.lamp_color[1]},B={context.scene.lamp_color[2]})",
            "lamp_offset": f"(X={context.scene.lamp_offset_x},Y={context.scene.lamp_offset_y*-1},Z={context.scene.lamp_offset_z})",
            "lamp_intensity": context.scene.lamp_intensity,
            "lamp_attenuation": context.scene.lamp_attenuation,
            "lamp_shadows": int(context.scene.lamp_shadows),
        }

        if export_mode == 'SELECTED':
            if not context.selected_objects:
                self.report({'ERROR'}, "No objects selected for export")
                return {"CANCELLED"}
            
            selected_objects = context.selected_objects

            for obj in selected_objects:
                if obj.type != 'MESH':
                    skipped_count += 1
                    continue
                
                if len(selected_objects) > 1 or not context.scene.modelname:
                    name=obj.name
                else:
                    name = context.scene.modelname

                prefixedName = f"{prefix}_{name}" if prefix else name
                
                obj_folder = os.path.join(export_path, prefixedName)
                create_folder(self, obj_folder)
                file_path = os.path.join(obj_folder, f"{prefixedName}.obj")
                
                if not context.scene.limitbypass:
                    sizeCheckReturn = sizeCheck()

                    if "ERROR" in sizeCheckReturn:
                        self.report({'ERROR'}, sizeCheckReturn)
                        return {"CANCELLED"}
                    elif "WARNING" in sizeCheckReturn:
                        self.report({'ERROR'}, sizeCheckReturn)

                for collision in bpy.context.scene.objects:
                    if collision.type == 'MESH' and collision.name.startswith("UCX_") and obj.name in collision.name:
                        collision.select_set(True)
                        collision_count += 1

                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                exportOBJ(self, file_path, True)
                exportOBJMaterials(obj, obj_folder)

                save_properties_file(obj_folder, properties)
                exported_count += 1

                self.report({'INFO'}, f"Exported {exported_count} objects, {collision_count} collision objects and skipped {skipped_count} non-mesh objects.")
        elif export_mode == 'SCENE':
            if context.scene.modelname:
                name = context.scene.modelname
            else: 
                name = bpy.context.active_object.name

            prefixedName = f"{prefix}_{name}" if prefix else name

            scene_folder = os.path.join(export_path, prefixedName)
            create_folder(self, scene_folder)  # Create the folder for the scene
            
            scene_file_path = os.path.join(scene_folder, f"{prefixedName}.obj")

            bpy.ops.object.select_all(action='DESELECT')
            for obj in context.scene.objects:
                if obj.type == 'MESH' and not obj.name.startswith("UCX_") and obj.name in bpy.context.view_layer.objects:
                    obj.select_set(True)

            bpy.ops.object.duplicate()

            duplicatedObjects = context.selected_objects

            for dupeObj in duplicatedObjects:
                for modifier in dupeObj.modifiers:
                    try:
                        # Apply the modifier
                        bpy.context.view_layer.objects.active = dupeObj
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                    except Exception as e:
                        print(f"Failed to apply modifier {modifier.name}: {e}")

                dupeObj.select_set(True)                
            
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
                if collision.type == 'MESH' and collision.name.startswith("UCX_"):
                    collision.select_set(True)
            
            joinedObject.select_set(True)
            bpy.context.view_layer.objects.active = joinedObject
            
            exportOBJ(self, scene_file_path, True)
            exportOBJMaterials(joinedObject, scene_folder)

            bpy.ops.object.select_all(action='DESELECT')
            joinedObject.select_set(True)

            save_properties_file(scene_folder, properties)

            bpy.ops.object.delete(use_global=False)

            self.report({'INFO'}, f"Exported scene succesfully.")

        

        return {"FINISHED"}


#
#
# THIS IS THE GUI, STOP LOSING IT AND ORGANIZE YOUR CODE YOU DUMBFUCK
#
#

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
        dimensionRow.label(text=f"Object dimensions are:")
        
        dimX = dimensionRow.box()
        x_dim = round(context.selected_objects[0].dimensions.x / 2, 3) if context.selected_objects else "0"
        dimX.label(text=f"X={x_dim}")

        dimY = dimensionRow.box()
        y_dim = round(context.selected_objects[0].dimensions.y / 2, 3) if context.selected_objects else "0"
        dimY.label(text=f"Y={y_dim}")

        dimZ = dimensionRow.box()
        z_dim = round(context.selected_objects[0].dimensions.z / 2, 3) if context.selected_objects else "0"
        dimZ.label(text=f"Z={z_dim}")

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
        
        if not context.selected_objects and not context.scene.modelname:
            rowExport.enabled = False
        else:
            rowExport.enabled = True
    
class VOTVE_PT_properties(bpy.types.Panel):
    bl_label = "Properties:"
    bl_parent_id = "VOTVE_PT_mainGUI"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VOTV Print Exporter"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene, "physical_material")
        layout.prop(context.scene, "emissive_strength")

        propertiesBox = layout.box()
        propertiesBox.label(text="Materials:")
        materialsBox = propertiesBox.box()

        propertiesBox.operator("material.update_settings", text=" Update materials")

        selected_objects = context.selected_objects

        materialUI = []

        if selected_objects:
            for obj in selected_objects:
                if obj.type == 'MESH':
                    for mat_slot in obj.material_slots:
                        if mat_slot.material:
                            material_settings = mat_slot.material.material_settings

                            if not material_settings:
                                materialsBox.row().label(text="No materials settings, please update the materials")
                                break
                                    
                            for i, setting in enumerate(material_settings):
                                if not any(materialName == setting.materialName for materialName in materialUI):
                                    materialUI.append(setting.materialName)
                                    materialRow = materialsBox.row()
                                    materialRow.label(text=setting.materialName)
                                    materialRow.prop(setting, "materialType", text=f"Type")
                                    materialRow.prop(setting, "materialFilter", text=f"Filter")
                else:
                    materialsBox.row().label(text="One or more object in selection cannot contain materials")
                    break
        else:
            materialsBox.row().label(text="No object selected.")


    
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

classes = (UpdateMaterialSettingsOperator, MaterialSettings, ExportButton, VOTVE_PT_mainGUI, VOTVE_PT_properties, VOTVE_PT_lightProperties, VOTVExporterPreferences, copyPosButton)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)   

    bpy.types.Material.material_settings = bpy.props.CollectionProperty(type=MaterialSettings)

    bpy.types.Scene.modelname = bpy.props.StringProperty(
        name="Model name",
        default="",
        description="This will be your file name.\nWARNING: If exporting multiple objects it will instead use the object name rather then the file name."
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
        name="Bypass Size Limit ?",
        default=False
    )

    bpy.types.Scene.export_mode = bpy.props.EnumProperty(
        name="Export Mode",
        description="Choose how to export the objects",
        items=[
            ('SELECTED', "Selected Objects", "Export only selected objects"),
            ('SCENE', "Whole Scene", "Export the entire scene")
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