import bpy

bl_info = {
    "name": "DS Virtual Camera Exporter",
    "category": "Generic",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    'location': 'File > Export > glTF 2.0',
    'description': 'Add DS_virtual_camera extension to exported glTF cameras.',
    'tracker_url': "",
    'isDraft': False,
    'developer': "",
    'url': '',
}

glTF_extension_name = "DS_virtual_camera"
extension_is_required = False


# ===== PropertyGroup =====

class ActionItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Action Name",
        description="Name of the action to trigger.",
        default=""
    )


class DSVirtualCameraProperties(bpy.types.PropertyGroup):
    priority: bpy.props.IntProperty(
        name="Priority",
        description="Priority of this virtual camera. Higher priority cameras take precedence.",
        default=10,
        min=0,
        max=100
    )

    # --- follow: reference to a scene object ---
    follow: bpy.props.PointerProperty(
        name="Follow",
        description="Object this virtual camera follows.",
        type=bpy.types.Object
    )

    # --- look_at ---
    look_at_type: bpy.props.EnumProperty(
        name="Look At Type",
        description="Type of look-at target.",
        items=[
            ('NONE', "None", "No look-at target"),
            ('ENTITY', "Entity", "Look at a scene object"),
            ('POSITION', "Position", "Look at a fixed world position"),
        ],
        default='NONE'
    )

    look_at_object: bpy.props.PointerProperty(
        name="Look At Object",
        description="Object to look at.",
        type=bpy.types.Object
    )

    look_at_position: bpy.props.FloatVectorProperty(
        name="Look At Position",
        description="Fixed world position to look at.",
        subtype='XYZ',
        default=(0.0, 0.0, 0.0)
    )

    look_at_offset: bpy.props.FloatVectorProperty(
        name="Look At Offset",
        description="Offset from the look-at target.",
        subtype='XYZ',
        default=(0.0, 0.0, 0.0)
    )

    # --- controller ---
    controller_type: bpy.props.EnumProperty(
        name="Controller",
        description="Type of dynamic camera controller.",
        items=[
            ('NONE', "None (Static)", "No dynamic controller, pose is purely static"),
            ('ORBIT', "Orbit", "Orbit camera: user input drives orbiting around a target"),
        ],
        default='NONE'
    )

    # Orbit controller config
    orbit_speed: bpy.props.FloatProperty(
        name="Orbit Speed",
        description="Speed multiplier for orbital movement.",
        default=1.0,
        min=0.0,
        soft_max=10.0
    )

    pan_speed: bpy.props.FloatProperty(
        name="Pan Speed",
        description="Speed multiplier for panning movement.",
        default=1.0,
        min=0.0,
        soft_max=10.0
    )

    zoom_speed: bpy.props.FloatProperty(
        name="Zoom Speed",
        description="Speed multiplier for zoom movement.",
        default=1.0,
        min=0.0,
        soft_max=10.0
    )

    zoom_min: bpy.props.FloatProperty(
        name="Zoom Min",
        description="Minimum zoom distance.",
        default=0.1,
        min=0.001,
        soft_max=10.0
    )

    zoom_max: bpy.props.FloatProperty(
        name="Zoom Max",
        description="Maximum zoom distance.",
        default=10.0,
        min=0.001,
        soft_max=100.0
    )

    pitch_min: bpy.props.FloatProperty(
        name="Pitch Min",
        description="Minimum pitch angle in radians.",
        default=-1.57,
        min=-3.14159,
        max=3.14159,
        subtype='ANGLE'
    )

    pitch_max: bpy.props.FloatProperty(
        name="Pitch Max",
        description="Maximum pitch angle in radians.",
        default=1.57,
        min=-3.14159,
        max=3.14159,
        subtype='ANGLE'
    )

    smoothing_factor: bpy.props.FloatProperty(
        name="Smoothing Factor",
        description="Factor controlling how quickly the camera moves toward target values (0.0-1.0).",
        default=0.2,
        min=0.0,
        max=1.0
    )

    # --- camera_blend ---
    blend_duration: bpy.props.FloatProperty(
        name="Blend Duration",
        description="Duration of the camera blend transition in seconds.",
        default=1.0,
        min=0.0,
        soft_max=10.0
    )

    blend_style: bpy.props.EnumProperty(
        name="Blend Style",
        description="Interpolation style for camera blending.",
        items=[
            ('LINEAR', "Linear", "Linear interpolation"),
            ('SMOOTH_STEP', "Smooth Step", "Smooth step interpolation"),
        ],
        default='SMOOTH_STEP'
    )

    enable_enter_actions: bpy.props.BoolProperty(
        name="Enable Enter Actions",
        description="Enable on-enter-start and on-enter-complete action lists.",
        default=False
    )

    on_enter_start_actions: bpy.props.CollectionProperty(
        name="On Enter Start Actions",
        description="Actions to trigger when this camera starts entering.",
        type=ActionItem
    )

    on_enter_start_actions_index: bpy.props.IntProperty(
        name="Index",
        default=0
    )

    on_enter_complete_actions: bpy.props.CollectionProperty(
        name="On Enter Complete Actions",
        description="Actions to trigger when this camera enter completes.",
        type=ActionItem
    )

    on_enter_complete_actions_index: bpy.props.IntProperty(
        name="Index",
        default=0
    )

    enable_exit_actions: bpy.props.BoolProperty(
        name="Enable Exit Actions",
        description="Enable on-exit-start and on-exit-complete action lists.",
        default=False
    )

    on_exit_start_actions: bpy.props.CollectionProperty(
        name="On Exit Start Actions",
        description="Actions to trigger when this camera starts exiting.",
        type=ActionItem
    )

    on_exit_start_actions_index: bpy.props.IntProperty(
        name="Index",
        default=0
    )

    on_exit_complete_actions: bpy.props.CollectionProperty(
        name="On Exit Complete Actions",
        description="Actions to trigger when this camera exit completes.",
        type=ActionItem
    )

    on_exit_complete_actions_index: bpy.props.IntProperty(
        name="Index",
        default=0
    )

    enable_control_actions: bpy.props.BoolProperty(
        name="Enable Control Actions",
        description="Enable on-control-start and on-control-complete action lists.",
        default=False
    )

    on_control_start_actions: bpy.props.CollectionProperty(
        name="On Control Start Actions",
        description="Actions to trigger when this camera control starts.",
        type=ActionItem
    )

    on_control_start_actions_index: bpy.props.IntProperty(
        name="Index",
        default=0
    )

    on_control_complete_actions: bpy.props.CollectionProperty(
        name="On Control Complete Actions",
        description="Actions to trigger when this camera control completes.",
        type=ActionItem
    )

    on_control_complete_actions_index: bpy.props.IntProperty(
        name="Index",
        default=0
    )

    enable_idle_actions: bpy.props.BoolProperty(
        name="Enable Idle Actions",
        description="Enable idle duration and on-idle action list.",
        default=False
    )

    idle_duration: bpy.props.FloatProperty(
        name="Idle Duration",
        description="Duration in seconds before idle actions are triggered.",
        default=1.0,
        min=0.0,
        soft_max=60.0
    )

    on_idle_actions: bpy.props.CollectionProperty(
        name="On Idle Actions",
        description="Actions to trigger when this camera is idle.",
        type=ActionItem
    )

    on_idle_actions_index: bpy.props.IntProperty(
        name="Index",
        default=0
    )


# ===== UI Panel (on glTF export panel) =====

def draw_export(context, layout):
    header, body = layout.panel("DS_virtual_camera_exporter", default_closed=False)
    header.use_property_split = False
    header.label(text="DS Virtual Camera")

    if body is None:
        return

    # This draws on the glTF export panel, but we need per-camera settings.
    # Show a note directing users to the Camera properties panel.
    col = body.column(align=False)
    col.label(text="Configure per-camera settings in:", icon='INFO')
    col.label(text="  Properties > Camera > DS Virtual Camera")


# ===== Camera Properties Panel =====

class CAMERA_PT_DSVirtualCamera(bpy.types.Panel):
    bl_label = "DS Virtual Camera"
    bl_idname = "CAMERA_PT_DSVirtualCamera"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        return getattr(context, 'camera', None) is not None

    def draw(self, context):
        layout = self.layout
        camera = context.camera
        props = camera.DSVirtualCameraProperties

        layout.use_property_split = True

        # Priority
        layout.prop(props, 'priority')

        # Follow
        layout.separator()
        layout.label(text="Follow:", icon='CON_TRACKTO')
        layout.prop(props, 'follow')

        # Look At
        layout.separator()
        layout.label(text="Look At:", icon='CONSTRAINT')
        layout.prop(props, 'look_at_type')

        if props.look_at_type == 'ENTITY':
            layout.prop(props, 'look_at_object')
        elif props.look_at_type == 'POSITION':
            layout.prop(props, 'look_at_position')

        layout.prop(props, 'look_at_offset')

        # Camera Blend
        layout.separator()
        layout.label(text="Camera Blend:", icon='IPO_EASE_IN_OUT')
        layout.prop(props, 'blend_duration')
        layout.prop(props, 'blend_style')

        # Controller
        layout.separator()
        layout.label(text="Controller:", icon='CAMERA_DATA')
        layout.prop(props, 'controller_type')

        if props.controller_type == 'ORBIT':
            col = layout.box().column(align=True)
            col.prop(props, 'orbit_speed')
            col.prop(props, 'pan_speed')
            col.prop(props, 'zoom_speed')
            col.separator()
            col.prop(props, 'zoom_min')
            col.prop(props, 'zoom_max')
            col.separator()
            col.prop(props, 'pitch_min')
            col.prop(props, 'pitch_max')
            col.separator()
            col.prop(props, 'smoothing_factor')

            # Control Event
            col.separator()
            control_box = col.box()
            control_box.prop(props, 'enable_control_actions')
            if props.enable_control_actions:
                control_box.label(text="On Control Start Actions:", icon='PLAY')
                self._draw_action_list(control_box, props, 'on_control_start_actions', 'on_control_start_actions_index', 'control_start_actions')
                control_box.separator()
                control_box.label(text="On Control End Actions:", icon='CHECKMARK')
                self._draw_action_list(control_box, props, 'on_control_complete_actions', 'on_control_complete_actions_index', 'control_complete_actions')

        # Idle Event
        layout.separator()
        idle_box = layout.box()
        idle_box.prop(props, 'enable_idle_actions')
        if props.enable_idle_actions:
            idle_box.prop(props, 'idle_duration')
            idle_box.label(text="On Idle Actions:", icon='ACTION')
            self._draw_action_list(idle_box, props, 'on_idle_actions', 'on_idle_actions_index', 'idle_actions')

        # Enter Event
        layout.separator()
        enter_box = layout.box()
        enter_box.prop(props, 'enable_enter_actions')
        if props.enable_enter_actions:
            enter_box.label(text="On Enter Start Actions:", icon='PLAY')
            self._draw_action_list(enter_box, props, 'on_enter_start_actions', 'on_enter_start_actions_index', 'enter_start_actions')
            enter_box.separator()
            enter_box.label(text="On Enter Complete Actions:", icon='CHECKMARK')
            self._draw_action_list(enter_box, props, 'on_enter_complete_actions', 'on_enter_complete_actions_index', 'enter_complete_actions')

        # Exit Event
        layout.separator()
        exit_box = layout.box()
        exit_box.prop(props, 'enable_exit_actions')
        if props.enable_exit_actions:
            exit_box.label(text="On Exit Start Actions:", icon='PLAY')
            self._draw_action_list(exit_box, props, 'on_exit_start_actions', 'on_exit_start_actions_index', 'exit_start_actions')
            exit_box.separator()
            exit_box.label(text="On Exit Complete Actions:", icon='CHECKMARK')
            self._draw_action_list(exit_box, props, 'on_exit_complete_actions', 'on_exit_complete_actions_index', 'exit_complete_actions')


    @staticmethod
    def _draw_action_list(layout, props, collection_attr, index_attr, list_id):
        collection = getattr(props, collection_attr)
        index = getattr(props, index_attr)

        row = layout.row()
        row.template_list(
            "UI_UL_list", list_id,
            props, collection_attr,
            props, index_attr,
            rows=3
        )

        col = row.column(align=True)
        col.operator("ds_virtual_camera.action_add", icon='ADD', text="").collection = collection_attr
        col.operator("ds_virtual_camera.action_remove", icon='REMOVE', text="").collection = collection_attr


# ===== Operators =====

class DSVIRTUALCAMERA_OT_action_add(bpy.types.Operator):
    bl_idname = "ds_virtual_camera.action_add"
    bl_label = "Add Action"
    bl_description = "Add a new action entry."

    collection: bpy.props.StringProperty(
        name="Collection",
        description="Name of the collection property to add to.",
        default=""
    )

    def execute(self, context):
        camera = context.camera
        props = camera.DSVirtualCameraProperties
        collection = getattr(props, self.collection)
        item = collection.add()
        item.name = ""
        return {'FINISHED'}


class DSVIRTUALCAMERA_OT_action_remove(bpy.types.Operator):
    bl_idname = "ds_virtual_camera.action_remove"
    bl_label = "Remove Action"
    bl_description = "Remove the selected action entry."

    collection: bpy.props.StringProperty(
        name="Collection",
        description="Name of the collection property to remove from.",
        default=""
    )

    def execute(self, context):
        camera = context.camera
        props = camera.DSVirtualCameraProperties
        collection = getattr(props, self.collection)
        index_attr = self.collection + "_index"
        idx = getattr(props, index_attr)
        if 0 <= idx < len(collection):
            collection.remove(idx)
            setattr(props, index_attr, min(idx, len(collection) - 1))
        return {'FINISHED'}


# ===== Registration =====

def register():
    bpy.utils.register_class(ActionItem)
    bpy.utils.register_class(DSVirtualCameraProperties)
    bpy.utils.register_class(CAMERA_PT_DSVirtualCamera)
    bpy.utils.register_class(DSVIRTUALCAMERA_OT_action_add)
    bpy.utils.register_class(DSVIRTUALCAMERA_OT_action_remove)

    bpy.types.Camera.DSVirtualCameraProperties = bpy.props.PointerProperty(type=DSVirtualCameraProperties)

    # from io_scene_gltf2 import exporter_extension_layout_draw
    # exporter_extension_layout_draw['DS Virtual Camera'] = draw_export


def unregister():
    from io_scene_gltf2 import exporter_extension_layout_draw
    if 'DS Virtual Camera' in exporter_extension_layout_draw:
        del exporter_extension_layout_draw['DS Virtual Camera']

    del bpy.types.Camera.DSVirtualCameraProperties

    bpy.utils.unregister_class(DSVIRTUALCAMERA_OT_action_remove)
    bpy.utils.unregister_class(DSVIRTUALCAMERA_OT_action_add)
    bpy.utils.unregister_class(CAMERA_PT_DSVirtualCamera)
    bpy.utils.unregister_class(DSVirtualCameraProperties)
    bpy.utils.unregister_class(ActionItem)


# ===== glTF Export User Extension =====

class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension

    def gather_camera_hook(self, gltf2_camera, blender_camera, export_settings):
        if not hasattr(blender_camera, 'DSVirtualCameraProperties'):
            return

        props = blender_camera.DSVirtualCameraProperties

        # vtree nodes' .node attributes are not yet populated at this point
        # (gather_camera_hook is called inside gather_node() before vnode.node is set).
        # So we store id(blender_object) as placeholders and resolve them later
        # in gather_gltf_extensions_hook, when vtree is fully initialized.
        ext_data = {
            "priority": props.priority,
        }

        # follow — store blender object id as placeholder
        if props.follow is not None:
            ext_data["follow"] = id(props.follow)

        # look_at
        if props.look_at_type == 'ENTITY' and props.look_at_object is not None:
            ext_data["look_at"] = {
                "Entity": id(props.look_at_object)
            }
        elif props.look_at_type == 'POSITION':
            ext_data["look_at"] = {
                "Position": [
                    props.look_at_position[0],
                    props.look_at_position[2],
                    - props.look_at_position[1],
                ]
            }

        # look_at_offset
        offset = props.look_at_offset
        ext_data["look_at_offset"] = [offset[0], offset[1], offset[2]]

        # controller
        if props.controller_type == 'ORBIT':
            ext_data["controller"] = {
                "Orbit": {
                    "orbit_speed": props.orbit_speed,
                    "pan_speed": props.pan_speed,
                    "zoom_speed": props.zoom_speed,
                    "zoom_min": props.zoom_min,
                    "zoom_max": props.zoom_max,
                    "pitch_min": props.pitch_min,
                    "pitch_max": props.pitch_max,
                    "smoothing_factor": props.smoothing_factor,
                }
            }
        else:
            ext_data["controller"] = "None"

        # on_enter_start_actions
        if props.enable_enter_actions:
            ext_data["on_enter_start_actions"] = [
                item.name for item in props.on_enter_start_actions if item.name.strip()
            ]

        # on_enter_complete_actions
        if props.enable_enter_actions:
            ext_data["on_enter_complete_actions"] = [
                item.name for item in props.on_enter_complete_actions if item.name.strip()
            ]

        # on_exit_start_actions
        if props.enable_exit_actions:
            ext_data["on_exit_start_actions"] = [
                item.name for item in props.on_exit_start_actions if item.name.strip()
            ]

        # on_exit_complete_actions
        if props.enable_exit_actions:
            ext_data["on_exit_complete_actions"] = [
                item.name for item in props.on_exit_complete_actions if item.name.strip()
            ]

        # on_control_start_actions
        if props.enable_control_actions:
            ext_data["on_control_start_actions"] = [
                item.name for item in props.on_control_start_actions if item.name.strip()
            ]

        # on_control_complete_actions
        if props.enable_control_actions:
            ext_data["on_control_complete_actions"] = [
                item.name for item in props.on_control_complete_actions if item.name.strip()
            ]

        # idle_duration
        if props.enable_idle_actions:
            ext_data["idle_duration"] = props.idle_duration

        # on_idle_actions
        if props.enable_idle_actions:
            ext_data["on_idle_actions"] = [
                item.name for item in props.on_idle_actions if item.name.strip()
            ]

        # camera_blend
        ext_data["camera_blend"] = {
            "duration": props.blend_duration,
            "style": "Linear" if props.blend_style == 'LINEAR' else "SmoothStep",
        }

        if gltf2_camera.extensions is None:
            gltf2_camera.extensions = {}

        gltf2_camera.extensions[glTF_extension_name] = self.Extension(
            name=glTF_extension_name,
            extension=ext_data,
            required=extension_is_required
        )

    def gather_gltf_extensions_hook(self, gltf, export_settings):
        # At this point, vtree is fully populated: all vnode.node attributes
        # are set to the same gltf2_io.Node objects that appear in gltf.nodes.
        # Build blender_object id -> node index mapping via vtree.
        blender_id_to_idx = {}
        vtree = export_settings.get('vtree')
        if vtree is not None and gltf.nodes is not None:
            # node object id -> index in gltf.nodes
            node_to_idx = {}
            for idx, node in enumerate(gltf.nodes):
                node_to_idx[id(node)] = idx

            # blender_object id -> node index (via vtree)
            for vnode in vtree.nodes.values():
                if vnode.blender_object is not None and vnode.node is not None:
                    node_idx = node_to_idx.get(id(vnode.node))
                    if node_idx is not None:
                        blender_id_to_idx[id(vnode.blender_object)] = node_idx

        # Resolve camera extensions: replace placeholder id(blender_object) with node index.
        # Note: at this point, the Extension objects have already been
        # traversed by add_scene() -> __traverse(), so camera.extensions
        # values are now raw dicts (not Extension objects).
        if gltf.cameras is not None:
            for camera in gltf.cameras:
                if camera.extensions is None:
                    continue
                data = camera.extensions.get(glTF_extension_name)
                if data is None:
                    continue

                # Resolve follow (stored as id(blender_object) -> node index)
                if "follow" in data and isinstance(data["follow"], int):
                    obj_id = data["follow"]
                    if obj_id in blender_id_to_idx:
                        data["follow"] = blender_id_to_idx[obj_id]
                    else:
                        del data["follow"]

                # Resolve look_at.Entity (stored as id(blender_object) -> node index)
                if "look_at" in data:
                    look_at = data["look_at"]
                    if "Entity" in look_at and isinstance(look_at["Entity"], int):
                        obj_id = look_at["Entity"]
                        if obj_id in blender_id_to_idx:
                            look_at["Entity"] = blender_id_to_idx[obj_id]
                        else:
                            del data["look_at"]


def glTF2_pre_export_callback(export_settings):
    pass


def glTF2_post_export_callback(export_settings):
    pass