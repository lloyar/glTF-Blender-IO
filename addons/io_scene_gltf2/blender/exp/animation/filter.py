import bpy

from ...com.data_path import get_channelbag_for_slot
from .tracks import __get_data_blender_tracks


POINTER_TYPES = ('materials', 'lights', 'cameras', 'nodes')


def filter_animation(export_settings):
    """Build the Pointer paths needed by each NLA track group.

    Static resource gathering registers every Blender path that can be
    represented by KHR_animation_pointer. Track baking needs only the paths
    driven by the current group of NLA strips, plus the paths required to
    calculate derived glTF properties.
    """
    export_settings.pop('gltf_pointer_animation_plan', None)

    # Scene baking intentionally samples the evaluated scene. Filtering it by
    # NLA F-Curves would discard drivers and other scene-level animation.
    if export_settings['gltf_animation_mode'] != 'NLA_TRACKS':
        return

    pointer_plan = {blender_type_data: {} for blender_type_data in POINTER_TYPES}

    for blender_type_data in POINTER_TYPES:
        registry = export_settings['KHR_animation_pointer'][blender_type_data]
        for blender_id in list(registry.keys()):
            blender_data_object = _get_blender_data_object(
                blender_type_data, blender_id, export_settings)
            if blender_data_object is None:
                # Generated materials (for example from Geometry Nodes) have
                # no Blender animation data to inspect or sample.
                del registry[blender_id]
                continue
            tracks_data = __get_data_blender_tracks(blender_type_data, blender_id, export_settings)
            resource_plan = {}

            for track_data in tracks_data.values():
                paths = _get_track_paths(
                    blender_type_data,
                    blender_data_object,
                    track_data,
                    registry[blender_id]['paths'])
                if len(paths) > 0:
                    resource_plan[track_data.plan_key] = paths

            if len(resource_plan) > 0:
                pointer_plan[blender_type_data][blender_id] = resource_plan
            else:
                # Avoid entering gather_data_track_animations for resources
                # that do not animate a supported Pointer property.
                del registry[blender_id]

    export_settings['gltf_pointer_animation_plan'] = pointer_plan


def _get_blender_data_object(blender_type_data, blender_id, export_settings):
    if blender_type_data == 'materials':
        if export_settings['gltf_apply'] is True:
            return export_settings['material_identifiers'].get(blender_id)
        return next((material for material in bpy.data.materials if id(material) == blender_id), None)
    if blender_type_data == 'lights':
        return next((light for light in bpy.data.lights if id(light) == blender_id), None)
    if blender_type_data == 'cameras':
        return next((camera for camera in bpy.data.cameras if id(camera) == blender_id), None)
    if blender_type_data == 'nodes':
        return next((obj for obj in bpy.data.objects if id(obj) == blender_id), None)
    raise ValueError("Unsupported animation pointer data type: {}".format(blender_type_data))


def _get_track_paths(blender_type_data, blender_data_object, track_data, registered_paths):
    animation_data = _get_animation_data(blender_data_object, track_data.on_type)
    if animation_data is None:
        return ()

    selected = set()
    has_fcurves = False
    for fcurve in _iter_track_fcurves(animation_data, track_data):
        has_fcurves = True
        _mark_fcurve_paths(
            blender_type_data,
            track_data.on_type,
            fcurve.data_path,
            fcurve.array_index,
            registered_paths,
            selected)

    # Some evaluated properties do not use the same RNA path as their source
    # F-Curve (camera lens -> angle, for example). Preserve the old behavior
    # for such uncommon tracks, but only for this one resource and track.
    if blender_type_data in ('cameras', 'lights') and has_fcurves and len(selected) == 0:
        selected.update(registered_paths.keys())

    # Drivers have no Action/Strip. If the data block has a matching NLA
    # track, keep its driven Pointer path for every track group because the
    # evaluated value may depend on that track.
    for fcurve in animation_data.drivers:
        _mark_fcurve_paths(
            blender_type_data,
            track_data.on_type,
            fcurve.data_path,
            fcurve.array_index,
            registered_paths,
            selected)

    _expand_dependencies(registered_paths, selected)
    return tuple(path for path in registered_paths.keys() if path in selected)


def _get_animation_data(blender_data_object, on_type):
    if on_type == 'NODETREE':
        node_tree = getattr(blender_data_object, 'node_tree', None)
        return None if node_tree is None else node_tree.animation_data
    return blender_data_object.animation_data


def _iter_track_fcurves(animation_data, track_data):
    for nla_track in track_data.tracks:
        track = animation_data.nla_tracks[nla_track.idx]
        for strip in track.strips:
            action = strip.action
            if action is None:
                continue
            channelbag = get_channelbag_for_slot(action, strip.action_slot)
            if channelbag is None:
                continue
            yield from channelbag.fcurves


def _mark_fcurve_paths(
        blender_type_data,
        on_type,
        data_path,
        array_index,
        registered_paths,
        selected):
    source_path = "node_tree." + data_path if on_type == 'NODETREE' else data_path
    candidates = {source_path, "{}[{}]".format(source_path, array_index)}

    for candidate in candidates:
        if candidate in registered_paths:
            selected.add(candidate)

    # Some glTF values are calculated from a differently named Blender
    # property, such as spot_blend + spot_size -> innerConeAngle.
    for path, path_data in registered_paths.items():
        if path_data.get('additional_path') in candidates:
            selected.add(path)

    # One Blender orthographic scale produces both glTF magnitudes.
    if blender_type_data == 'cameras' and data_path == 'ortho_scale':
        selected.update(path for path in ('ortho_scale_x', 'ortho_scale_y') if path in registered_paths)

    # Perspective FOV is registered as the evaluated ``angle`` property, but
    # Blender normally writes camera animation to ``lens``.
    if blender_type_data == 'cameras' and data_path in ('lens', 'sensor_width'):
        selected.update(
            path for path, path_data in registered_paths.items()
            if path_data['path'].endswith('/perspective/yfov'))

    # In Cycles the exported light color can be the product of the light data
    # color and an emission-node color. Either source should select the glTF
    # color channel.
    if blender_type_data == 'lights' and on_type == 'LIGHT' and data_path == 'color':
        selected.update(
            path for path, path_data in registered_paths.items()
            if path_data['path'].endswith('/color'))


def _expand_dependencies(registered_paths, selected):
    pending = list(selected)
    while pending:
        path = pending.pop()
        path_data = registered_paths[path]

        dependencies = []
        for dependency_name in ('strength_channel', 'factor_channel'):
            dependency = path_data.get(dependency_name)
            if dependency in registered_paths:
                dependencies.append(dependency)

        pointer = path_data['path']
        # Multiple Blender inputs can form one glTF property (base color and
        # alpha), while texture transform and specular conversion require a
        # small group of related glTF properties to be sampled together.
        if pointer == '/materials/XXX/pbrMetallicRoughness/baseColorFactor':
            dependencies.extend(
                candidate for candidate, candidate_data in registered_paths.items()
                if candidate_data['path'] == pointer)
        elif 'KHR_texture_transform' in pointer:
            pointer_parent = pointer.rsplit('/', 1)[0]
            dependencies.extend(
                candidate for candidate, candidate_data in registered_paths.items()
                if candidate_data['path'].rsplit('/', 1)[0] == pointer_parent)
        elif pointer.endswith('/specularFactor') or pointer.endswith('/specularColorFactor'):
            pointer_parent = pointer.rsplit('/', 1)[0]
            dependencies.extend(
                candidate for candidate, candidate_data in registered_paths.items()
                if candidate_data['path'].rsplit('/', 1)[0] == pointer_parent)

        for dependency in dependencies:
            if dependency not in selected:
                selected.add(dependency)
                pending.append(dependency)
