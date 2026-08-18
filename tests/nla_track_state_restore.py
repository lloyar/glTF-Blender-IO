# Copyright 2018-2026 The Khronos Group Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import math
from pathlib import Path
import sys
import tempfile

import bpy


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / 'addons'))

import io_scene_gltf2


def stash_action_in_muted_track(obj, track_name):
    action = obj.animation_data.action
    action.name = track_name

    track = obj.animation_data.nla_tracks.new()
    track.name = track_name
    track.strips.new(track_name, int(action.frame_range[0]), action)
    track.mute = True

    obj.animation_data.action_slot = None
    obj.animation_data.action = None


def stash_action_in_track(obj, track, strip_name):
    action = obj.animation_data.action
    action.name = strip_name
    track.strips.new(strip_name, int(action.frame_range[0]), action)

    obj.animation_data.action_slot = None
    obj.animation_data.action = None


def matrix_values(matrix):
    return tuple(value for row in matrix for value in row)


io_scene_gltf2.register()

scene = bpy.context.scene

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

parent = bpy.data.objects.new('Animated parent', None)
scene.collection.objects.link(parent)
parent.rotation_euler[1] = 0.0
parent.keyframe_insert(data_path='rotation_euler', index=1, frame=0)
parent.rotation_euler[1] = math.radians(60.0)
parent.keyframe_insert(data_path='rotation_euler', index=1, frame=60)
stash_action_in_muted_track(parent, 'Parent animation')
parent.rotation_euler[1] = 0.0

# An intermediate parent reproduces the stale descendant world matrix that can remain after
# sampling and restoring an ancestor's NLA track.
intermediate = bpy.data.objects.new('Intermediate parent', None)
scene.collection.objects.link(intermediate)
intermediate.parent = parent

bpy.ops.mesh.primitive_cube_add(location=(1.0, 0.0, 0.0))
child = bpy.context.object
child.name = 'Visibility-only child'
child.parent = intermediate

material = bpy.data.materials.new('Animated material')
material.use_nodes = True
surface = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
surface.name = 'Renamed surface'
base_color = surface.inputs['Base Color']
base_color.default_value = (0.8, 0.1, 0.1, 1.0)
base_color.keyframe_insert(data_path='default_value', frame=10)
base_color.default_value = (0.1, 0.8, 0.1, 1.0)
base_color.keyframe_insert(data_path='default_value', frame=12)
stash_action_in_muted_track(material.node_tree, 'Material animation')

roughness = surface.inputs['Roughness']
roughness.default_value = 0.2
roughness.keyframe_insert(data_path='default_value', frame=0)
roughness.default_value = 0.8
roughness.keyframe_insert(data_path='default_value', frame=2)
material_track = material.node_tree.animation_data.nla_tracks['Material animation']
stash_action_in_track(material.node_tree, material_track, 'Roughness strip')

child.data.materials.append(material)

child.hide_render = False
child.keyframe_insert(data_path='hide_render', frame=64)
child.hide_render = True
child.keyframe_insert(data_path='hide_render', frame=66)
stash_action_in_muted_track(child, 'Visibility animation')

camera_data = bpy.data.cameras.new('Animated camera')
camera = bpy.data.objects.new('Animated camera', camera_data)
scene.collection.objects.link(camera)
camera_data.lens = 35.0
camera_data.keyframe_insert(data_path='lens', frame=20)
camera_data.lens = 70.0
camera_data.keyframe_insert(data_path='lens', frame=22)
stash_action_in_muted_track(camera_data, 'Camera animation')

light_data = bpy.data.lights.new('Animated light', type='POINT')
light = bpy.data.objects.new('Animated light', light_data)
scene.collection.objects.link(light)
light_data.energy = 10.0
light_data.keyframe_insert(data_path='energy', frame=30)
light_data.energy = 100.0
light_data.keyframe_insert(data_path='energy', frame=32)
stash_action_in_muted_track(light_data, 'Light animation')

scene.frame_set(0)
initial_basis = matrix_values(child.matrix_basis.copy())

with tempfile.TemporaryDirectory() as temp_dir:
    gltf_path = Path(temp_dir) / 'nla_track_state_restore.gltf'
    result = bpy.ops.export_scene.gltf(
        filepath=str(gltf_path),
        export_format='GLTF_SEPARATE',
        export_animation_mode='NLA_TRACKS',
        export_animations=True,
        export_cameras=True,
        export_lights=True,
        export_pointer_animation=True,
    )

    exported_gltf = json.loads(gltf_path.read_text())

if result != {'FINISHED'}:
    print(f'glTF export failed: {result}', file=sys.stderr)
    sys.exit(1)

pointer_paths = [
    channel['target']['extensions']['KHR_animation_pointer']['pointer']
    for animation in exported_gltf.get('animations', [])
    for channel in animation.get('channels', [])
    if 'KHR_animation_pointer' in channel['target'].get('extensions', {})
]
expected_pointer_suffixes = {
    '/pbrMetallicRoughness/baseColorFactor',
    '/pbrMetallicRoughness/roughnessFactor',
    '/extensions/KHR_node_visibility/visible',
    '/perspective/yfov',
    '/intensity',
}
if len(pointer_paths) != len(expected_pointer_suffixes):
    print(f'Unexpected animation pointers: {sorted(pointer_paths)}', file=sys.stderr)
    sys.exit(1)

for suffix in expected_pointer_suffixes:
    matching_pointers = [pointer for pointer in pointer_paths if pointer.endswith(suffix)]
    if len(matching_pointers) != 1:
        print(
            f'Expected one animation pointer ending in {suffix}: {sorted(pointer_paths)}',
            file=sys.stderr,
        )
        sys.exit(1)

exported_basis = matrix_values(child.matrix_basis)
max_delta = max(abs(before - after) for before, after in zip(initial_basis, exported_basis))
if max_delta > 1e-6:
    print(
        'NLA track export changed the child local transform:\n'
        f'before={initial_basis}\n'
        f'after={exported_basis}',
        file=sys.stderr,
    )
    sys.exit(1)
