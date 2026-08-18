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
child.hide_render = False
child.keyframe_insert(data_path='hide_render', frame=64)
child.hide_render = True
child.keyframe_insert(data_path='hide_render', frame=66)
stash_action_in_muted_track(child, 'Visibility animation')

scene.frame_set(0)
initial_basis = matrix_values(child.matrix_basis.copy())

with tempfile.TemporaryDirectory() as temp_dir:
    result = bpy.ops.export_scene.gltf(
        filepath=str(Path(temp_dir) / 'nla_track_state_restore.glb'),
        export_format='GLB',
        export_animation_mode='NLA_TRACKS',
        export_animations=True,
        export_pointer_animation=True,
    )

if result != {'FINISHED'}:
    print(f'glTF export failed: {result}', file=sys.stderr)
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
