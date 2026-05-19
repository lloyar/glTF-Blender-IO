import bpy

from ...com.data_path import get_channelbag_for_slot
from ..animation.tracks import __get_nla_tracks_node_tree, __get_nla_tracks_obj


def filter_animation(export_settings):
    vtree = export_settings['vtree']
    for obj_uuid in vtree.get_all_objects():
        blender_object = export_settings['vtree'].nodes[obj_uuid].blender_object

        obj_tracks_data = __get_nla_tracks_obj(obj_uuid, export_settings)
        node_tree_tracks_data = __get_nla_tracks_node_tree(obj_uuid, export_settings)

        obj_tracks_data.extend(node_tree_tracks_data)

        for track_data in obj_tracks_data.values():
            nla_track = track_data.tracks[0]  # TrackData.tracks have only one NLATrack
            if track_data.on_type == "OBJECT":
                export_settings['KHR_animation_pointer']['nodes'][id(blender_object)]['used'] = True
                nla_strip: bpy.types.NlaStrip = blender_object.animation_data.nla_tracks[nla_track.idx].strips[0]
            elif track_data.on_type == "NODETREE":
                blender_material = blender_object.active_material
                export_settings['KHR_animation_pointer']['materials'][id(blender_material)]['used'] = True
                nla_strip: bpy.types.NlaStrip = \
                    blender_material.node_tree.animation_data.nla_tracks[nla_track.idx].strips[0]
            else:
                continue

            track_action: bpy.types.Action = nla_strip.action
            track_action_slot: bpy.types.ActionSlot = nla_strip.action_slot

            channelbag = get_channelbag_for_slot(track_action, track_action_slot)
            fcurves = channelbag.fcurves if channelbag else []
            for fcurve in fcurves:
                data_path = fcurve.data_path

                if track_data.on_type == "OBJECT":
                    if data_path == "hide_render":
                        export_settings['KHR_animation_pointer']['nodes'][id(blender_object)]['paths'][data_path][
                            'used'] = True
                        if 'nla_track_idx' not in \
                                export_settings['KHR_animation_pointer']['nodes'][id(blender_object)]['paths'][
                                    data_path]:
                            export_settings['KHR_animation_pointer']['nodes'][id(blender_object)]['paths'][data_path][
                                'nla_track_idx'] = []

                        export_settings['KHR_animation_pointer']['nodes'][id(blender_object)]['paths'][data_path][
                            'nla_track_idx'].append(nla_track.idx)

                elif track_data.on_type == "NODETREE":
                    node_name = data_path.split('nodes["')[1].split('"]')[0]
                    node = blender_material.node_tree.nodes[node_name]
                    if node.type == 'MAPPING':
                        export_settings['KHR_animation_pointer']['materials'][id(blender_material)]['paths'][
                            f'node_tree.nodes["{node_name}"].inputs[1].default_value']['used'] = True
                        export_settings['KHR_animation_pointer']['materials'][id(blender_material)]['paths'][
                            f'node_tree.nodes["{node_name}"].inputs[3].default_value']['used'] = True
                        export_settings['KHR_animation_pointer']['materials'][id(blender_material)]['paths'][
                            f'node_tree.nodes["{node_name}"].inputs[2].default_value[2]']['used'] = True
                    elif data_path.startswith("nodes[\"Principled BSDF\"].inputs"):
                        # TODO(lloyar): process
                        export_settings['KHR_animation_pointer']['materials'][id(blender_material)]['paths'][
                            f'node_tree.{data_path}']['used'] = True
                        pass
                    else:
                        pass
                else:
                    continue

    delete_unused_pointer(export_settings, 'nodes')
    delete_unused_pointer(export_settings, 'materials')

    # for node_id in list(export_settings['KHR_animation_pointer']['nodes'].keys()):
    #     if 'used' not in export_settings['KHR_animation_pointer']['nodes'][node_id]:
    #         del export_settings['KHR_animation_pointer']['nodes'][node_id]
    #     else:
    #         for path in list(export_settings['KHR_animation_pointer']['nodes'][node_id]['paths'].keys()):
    #             if 'used' not in export_settings['KHR_animation_pointer']['nodes'][node_id]['paths'][path]:
    #                 del export_settings['KHR_animation_pointer']['nodes'][node_id]['paths'][path]
    #
    # for material_id in list(export_settings['KHR_animation_pointer']['materials'].keys()):
    #     if 'used' not in export_settings['KHR_animation_pointer']['materials'][material_id]:
    #         del export_settings['KHR_animation_pointer']['materials'][material_id]
    #     else:
    #         for path in list(export_settings['KHR_animation_pointer']['materials'][material_id]['paths'].keys()):
    #             if 'used' not in export_settings['KHR_animation_pointer']['materials'][material_id]['paths'][path]:
    #                 del export_settings['KHR_animation_pointer']['materials'][material_id]['paths'][path]


def delete_unused_pointer(export_settings, type_str):
    for id in list(export_settings['KHR_animation_pointer'][type_str].keys()):
        if 'used' not in export_settings['KHR_animation_pointer'][type_str][id]:
            del export_settings['KHR_animation_pointer'][type_str][id]
        else:
            for path in list(export_settings['KHR_animation_pointer'][type_str][id]['paths'].keys()):
                if 'used' not in export_settings['KHR_animation_pointer'][type_str][id]['paths'][path]:
                    del export_settings['KHR_animation_pointer'][type_str][id]['paths'][path]
