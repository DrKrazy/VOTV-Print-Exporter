# **VOTV-Print-Exporter**

## Main settings:

### Export settings:

- #### Export folder path:
	The path where you want your 3D print to be exported.
I personally export it straight to my printer folder in the Assets folder.

- #### Model name:
	The name your want your model to have, if empty it will use the name of the selected main object.
	
- #### Export prefix:
	This just adds a prefix to 3D print, mainly used for organizing when doing mass exports (check out my Floor lights or my Lava lamps in the EternityDev discord server).
	
- #### Export modes:
	- Selected objects:
This will export all selected object as a single object along with filtering the collision meshes (UCX_) depending on if they contain the model name.

	- Individual Objects:
This will export each model as it's own print filtering the collision meshes (UCX_) depending on the name of the object itself is present in the collisions mesh's name.

	- Scene mode:
This will export every mesh in the scene with no filtering for the collisions meshes, so everything starting with UCX_ will be a collisions mesh no matter the name after.

### Size settings:

- #### Object dimensions:
	Shows the boundary dimensions of object(s), mainly used to check if an object or multiple 
objects fit on the printer.

- #### Size limit:
	- Industrial printer: Prevents exporting an object too large for the industrial printer to be able to print
	- 
	- Desktop printer: Prevents exporting an object too large for the Desktop Printer to be able to print.
	- 
- #### Bypass size limit:
	This settings just disables the size limit as a whole, allowing you to export models too large to be printed in game without using a "bypass" method.
	
### Materials:

*For each object, generates a list containing the images with settings tied to them.*
- #### Structure:
	- Name of the material:
		- Image present in material with a type and filter setting

- #### Material type:
	- **Diffuse:** Texture of the base color of an object.
	- **Normal:** Texture that simulates detailed surface geometry
	- **Emissive:** Texture for the glowing/emissive parts of an object
	- **PBR:** Texture that defines surface properties of the object like roughness, metallic and specular
	- **Roughness:** Texture determining whether a surface appears shiny (low roughness) or matte (high roughness).
	- **Metallic:** Texture that controls which parts of a model are metallic (white = fully metallic, black = non-metallic).
	- **Specular:** Texture that controls how light reflects off different parts of a model, determining where highlights appear and how intense they are.

- #### Material filter:
	- **Nearest:** Used for lower resolution texture to make them look sharper
	- **Bi-linear:** Used to high resolution texture to make them look smoother

### Export object(s)
*Exports the object.*

### Properties
*Properties of the 3D print*
- #### Health:
	- The health of the 3D print, if set to 0 the print is unbreakable (not recommended).

- #### Damage resistance:
	- Damage resistance affects any damage coming from the player themselves such as using weapons on the 3D print.

- #### Impact resistance:
- Impact resistance affect any other type of damage such as physical damage.

- #### Physical material:
	- A list of the physical materials you want your 3D print to be.
	- Mainly impacts the sound.
	 Some physical materials have unique properties such as Food, making it edible.

- #### Emissive strength:
	- How bright the emissive material is.

### Light settings:

- #### Enable light:
	- Enables a customizable light to the 3D print.

- #### Light toggle:
	- Gives a "Toggle Light" option to the 3D print to turn On and Off the light.

- #### Light color:
	- Color of the light.

- #### Light offset:
	- Position of the light relative to the 3D print.

- #### Light intensity:
	- Intensity of the light

- #### Light attenuation:
	- Distance of the light

- #### Light shadow:
	- Whether the light casts shadows
