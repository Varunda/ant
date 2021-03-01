import json
import os.path
import math
import sys
from os import path
from pathlib import Path

PRINT_PROPS = False
USE_BLENDER = False
try:
	import bpy
	USE_BLENDER = True
except ImportError:
	USE_BLENDER = False

hexes = []
fac_x = 0
fac_y = 0

with open('D:/Planetside2/Builder/indar_zones.txt', 'r') as f:
    zones = json.load(f)

    #for key in props['objects']:
    #    print(key['actorDefinition'])

def in_hexes(x, y):
	for hex in hexes:
		min_x = (float(hex['x']) - 1) * 200
		max_x = (float(hex['x']) + 1) * 200
		min_y = (float(hex['y']) - 1) * 200
		max_y = (float(hex['y']) + 1) * 200
		if (min_x < x and max_x > x
				and min_y < y and max_y > y):
			print(hex, min_x, max_x, min_y, max_y, x, y)
			return True
	return False

def get_collection(name, layer = None):
	if (USE_BLENDER == False):
		return None

	if (layer == None):
		layer = bpy.context.view_layer.layer_collection

	if (layer.name == name):
		return layer

	found = None
	for layer_kids in layer.children:
		found = get_collection(name, layer_kids)
		if found:
			return found

def set_active_collection(name):
	if (USE_BLENDER == False):
		return
	found = get_collection(name)
	if (found == None):
		print('Failed to find', name)
		return

	bpy.context.view_layer.active_layer_collection = found

def in_range(x, y):
	ax = (x - fac_x) ** 2
	ay = (y - fac_y) ** 2
	return ax + ay < 200 ** 2

def get_model_path(actor):
	return 'D:/Planetside2/Models/' + actor_name + '_LOD0/' + actor_name + '_LOD0.obj'

def has_model(actor):
	path = get_model_path(actor_name)
	return os.path.exists(path)

def deg(radian):
	return radian * 180 / math.pi

def rad(deg):
	return deg * math.pi / 180

#base = input('Base name: ')
base = 'Regent Rock Garrison'
print('Looking for: %s' % (base))

found = False

for types in zones['zone_list'][0]['regions']:
	for zone in zones['zone_list'][0]['regions'][types]:
		#print('Checking %s' % zone['facility_name'])
		if (zone['facility_name'] == base):
			found = True
			fac_x = float(zone['location_x'])
			fac_y = float(zone['location_z'])
			print('Found base, at (%s, %s) loading hexes' % (fac_x, fac_y))
			for hex in zone['hex']:
				print(hex)
				hexes.append(hex)
			break

if (found == False):
	print("Failed to find", base)
	sys.exit()

with open('D:/Planetside2/Builder/indar_old_props.json', 'r') as f:
    props = json.load(f)

count = 0
meshes = dict()
missing_actors = set()
base_collection = None
base_layer_collection = None

# Create the base collection where all sub-collections will go
if (USE_BLENDER == True):
	base_collection = bpy.data.collections.new(base)
	bpy.context.scene.collection.children.link(base_collection)
	set_active_collection(base_collection.name)

for prop in props['objects']:
	# Has no mesh
	if "Occluder" in prop['actorDefinition']:
		continue
	if "AntiGravity" in prop['actorDefinition']:
		continue

	for inst in prop['instances']:
		inst_x = float(inst['position'][0])
		inst_y = float(inst['position'][2])

		#if (in_hexes(inst_x, inst_y)):
		if (in_range(inst_x, inst_y)):
			count += 1
			actor_name = str(Path(prop['actorDefinition']).with_suffix(''))
			model_name = get_model_path(actor_name)
			model_exists = has_model(actor_name)
			if (PRINT_PROPS == True):
				print('Found %s/%s\n\tLOC: (%f, %f, %f)\n\tROT: (%f, %f, %f)\n\tSCL: (%f, %f, %f)'
					% (actor_name, prop['actorDefinition'],
					inst_x, inst['position'][1], inst_y,
					deg(inst['rotation'][1]) + 90, deg(inst['rotation'][2]), deg(inst['rotation'][0]),
					inst['scale'][0],inst['scale'][1],inst['scale'][2]))
				print('\tMDL: ' + str(has_model(actor_name)))

			if (model_exists == True):
				if (USE_BLENDER == True):

					# Place each prop in a separate collection to avoid lists of hundreds of props
					actor_coll = base_collection.children.get(actor_name)
					if (actor_coll == None):
						actor_coll = bpy.data.collections.new(actor_name)
						base_collection.children.link(actor_coll)
					set_active_collection(actor_coll.name)

					# Copy a mesh instead of importing it if possible, lot faster
					if actor_name in meshes:
						#print('Found %s under %s' % (actor_name, meshes[actor_name]))
						og_obj = bpy.data.objects[meshes[actor_name]]
						obj = og_obj.copy()
						obj.data = og_obj.data.copy()
						bpy.context.collection.objects.link(obj)
					else:
						bpy.ops.import_scene.obj(filepath=model_name)
						obj = bpy.context.selected_objects[0]
						meshes[actor_name] = obj.name

					obj.scale = [
						math.fmod(inst['scale'][0], math.pi),
						math.fmod(inst['scale'][1], math.pi),
						math.fmod(inst['scale'][2], math.pi)
					]
					obj.rotation_mode = 'XYZ'
					obj.rotation_euler = [inst['rotation'][1] + rad(90), inst['rotation'][2], inst['rotation'][0]]
					obj["ps2_id"] = str(inst["id"])

					loc = [inst_x, -inst_y, inst['position'][1]]
					obj.location = loc
			else:
				missing_actors.add(model_name)

print("Missing models: ", missing_actors)
print(count)
print("Copy this to run in Blender:")
print("exec(compile(open('D:/Planetside2/Builder/run.py').read(), '', 'exec'))")
