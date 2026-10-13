# SPDX-License-Identifier: Apache-2.0

"""Run with Blender --background --factory-startup --python-exit-code 1 --python."""

import json
from pathlib import Path
import struct
import sys
import tempfile
from unittest.mock import patch

import bpy


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addons'))
import io_scene_gltf2
from io_scene_gltf2.blender.exp import export


io_scene_gltf2.register()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
obj.name = 'Background'
obj.hide_render = True
obj.keyframe_insert(data_path='hide_render', frame=0)
animation_data = obj.animation_data
action = animation_data.action
action.name = 'Hide background'
track = animation_data.nla_tracks.new()
track.name = action.name
track.strips.new(action.name, 0, action)
track.mute = True
animation_data.action_slot = None
animation_data.action = None
bpy.context.scene.frame_set(7)

with tempfile.TemporaryDirectory() as temp_dir:
    for mode, pointer, solo in [
        ('NLA_TRACKS', True, False),
        ('NLA_TRACKS', True, True),
        ('NLA_TRACKS', False, False),
        ('ACTIONS', True, False),
    ]:
        track.is_solo = solo
        bpy.context.scene.frame_set(7)
        # A solo track actively drives hide_render to True. Test its evaluated
        # state; a manual False override can be discarded by Blender before the
        # export operator even starts.
        for initial_hidden in ((True,) if solo else (False, True)):
            obj.hide_render = initial_hidden
            for repeat in range(2):
                path = Path(temp_dir) / f'{mode}_{pointer}_{initial_hidden}_{repeat}.gltf'
                result = bpy.ops.export_scene.gltf(
                    filepath=str(path),
                    export_format='GLTF_SEPARATE',
                    export_animation_mode=mode,
                    export_animations=True,
                    export_pointer_animation=pointer,
                )
                assert result == {'FINISHED'}, result
                assert obj.hide_render == initial_hidden, (
                    f'{mode}, pointer={pointer}, repeat={repeat}: '
                    f'hide_render changed from {initial_hidden} to {obj.hide_render}'
                )
                assert bpy.context.scene.frame_current == 7
                assert animation_data.action is None
                assert track.mute and track.is_solo == solo and animation_data.use_nla
                gltf = json.loads(path.read_text())
                node = next(node for node in gltf['nodes'] if node.get('name') == obj.name)
                visible = node.get('extensions', {}).get('KHR_node_visibility', {}).get('visible', True)
                # Solo overrides mute in Blender: evaluating frame zero really
                # hides this object, even if its current value was set manually.
                assert visible == (not (initial_hidden or solo)), node

                if mode == 'NLA_TRACKS' and pointer:
                    animation = next(a for a in gltf['animations'] if a['name'] == action.name)
                    channel = next(c for c in animation['channels'] if c['target']['path'] == 'pointer')
                    assert channel['target']['extensions']['KHR_animation_pointer']['pointer'].endswith(
                        '/extensions/KHR_node_visibility/visible')
                    sampler = animation['samplers'][channel['sampler']]
                    assert sampler['interpolation'] == 'STEP'
                    accessor = gltf['accessors'][sampler['output']]
                    view = gltf['bufferViews'][accessor['bufferView']]
                    binary = (path.parent / gltf['buffers'][view['buffer']]['uri']).read_bytes()
                    offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
                    values = struct.unpack_from('<' + 'f' * accessor['count'], binary, offset)
                    assert all(value == 0.0 for value in values), values


def fail_during_export(_settings):
    bpy.context.scene.frame_set(3)
    obj.hide_render = True
    raise ValueError('Simulated export failure')


obj.hide_render = False
with patch.object(export, '__notify_start'), patch.object(export, '__export', fail_during_export):
    try:
        export.save(bpy.context, {'gltf_current_frame': False, 'pre_export_callbacks': []})
    except ValueError as error:
        assert str(error) == 'Simulated export failure'
    else:
        raise AssertionError('Expected the simulated export failure')
assert not obj.hide_render
assert bpy.context.scene.frame_current == 7

print('Visibility state and exported animation preserved across repeated exports.')
