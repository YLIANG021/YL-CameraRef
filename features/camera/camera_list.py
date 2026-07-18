"""Scene camera selection, deletion, and quick settings."""

import bpy
from bpy.props import StringProperty
from bpy.types import Menu, Operator, Panel

from ... import i18n
from ...core.camera import get_valid_scene_camera, sync_scene_camera_state
from .add_view_camera import get_view_window_region


def get_scene_cameras(scene):
    if scene is None:
        return []
    return sorted(
        (obj for obj in scene.objects if obj.type == 'CAMERA'),
        key=lambda obj: obj.name.casefold(),
    )


def tag_view3d_redraws(context):
    screen = getattr(context, "screen", None)
    if screen is None:
        return
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def show_camera_in_current_view(context, camera):
    area = getattr(context, "area", None)
    if area is None or area.type != 'VIEW_3D':
        return

    space = getattr(context, "space_data", None) or area.spaces.active
    region_3d = getattr(space, "region_3d", None)
    window_region = get_view_window_region(area)
    if region_3d is None or window_region is None:
        return

    space.camera = camera
    if region_3d.view_perspective == 'CAMERA':
        area.tag_redraw()
        return

    smooth_view = context.preferences.view.smooth_view
    try:
        context.preferences.view.smooth_view = 0
        with context.temp_override(
            window=context.window,
            area=area,
            region=window_region,
            space_data=space,
        ):
            bpy.ops.view3d.view_camera()
    finally:
        context.preferences.view.smooth_view = smooth_view


class BG_OT_SelectSceneCamera(Operator):
    bl_idname = "camera.yl_cameraref_select_scene_camera"
    bl_label = "Set Active Camera"
    bl_description = "Make this the active camera."
    bl_translation_context = i18n.CONTEXT
    bl_options = {'UNDO'}

    camera_name: StringProperty(options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        if get_scene_cameras(getattr(context, "scene", None)):
            return True
        cls.poll_message_set(i18n.tr_iface("No cameras in scene"))
        return False

    def execute(self, context):
        scene = context.scene
        camera = scene.objects.get(self.camera_name)
        if camera is None or camera.type != 'CAMERA':
            self.report(
                {'WARNING'},
                i18n.tr_report("Selected camera is no longer in this scene."),
            )
            return {'CANCELLED'}

        scene.camera = camera
        sync_scene_camera_state(scene, context=context)
        show_camera_in_current_view(context, camera)
        tag_view3d_redraws(context)
        return {'FINISHED'}


class BG_MT_SceneCameras(Menu):
    bl_idname = "BG_MT_scene_cameras"
    bl_label = "Scene Cameras"
    bl_translation_context = i18n.CONTEXT

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        active_camera = get_valid_scene_camera(scene, clear_invalid=True)
        cameras = get_scene_cameras(scene)

        if not cameras:
            layout.label(
                text="No cameras in scene",
                text_ctxt=i18n.CONTEXT,
                icon='KEYTYPE_BREAKDOWN_VEC',
            )
            return

        for camera in cameras:
            operator = layout.operator(
                BG_OT_SelectSceneCamera.bl_idname,
                text=camera.name,
                translate=False,
                icon='RADIOBUT_ON' if camera == active_camera else 'RADIOBUT_OFF',
            )
            operator.camera_name = camera.name


class BG_OT_DuplicateSceneCamera(Operator):
    bl_idname = "camera.yl_cameraref_duplicate_scene_camera"
    bl_label = "Duplicate Camera"
    bl_description = "Duplicate the camera and its reference setup."
    bl_translation_context = i18n.CONTEXT
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if get_valid_scene_camera(getattr(context, "scene", None)) is not None:
            return True
        cls.poll_message_set(i18n.tr_iface("No active camera"))
        return False

    def execute(self, context):
        scene = context.scene
        camera = get_valid_scene_camera(scene, clear_invalid=True)
        if camera is None:
            return {'CANCELLED'}

        duplicate = camera.copy()
        duplicate.data = camera.data.copy()
        duplicate.name = f"{camera.name} Copy"
        duplicate.data.name = f"{camera.data.name} Copy"

        target_collection = camera.users_collection[0] if camera.users_collection else scene.collection
        target_collection.objects.link(duplicate)

        for selected_object in context.selected_objects:
            selected_object.select_set(False)
        duplicate.select_set(True)
        context.view_layer.objects.active = duplicate
        scene.camera = duplicate

        sync_scene_camera_state(scene, context=context)
        show_camera_in_current_view(context, duplicate)
        tag_view3d_redraws(context)
        self.report(
            {'INFO'},
            i18n.tr_report("Duplicated camera: {name}", name=duplicate.name),
        )
        return {'FINISHED'}


class BG_OT_RemoveSceneCamera(Operator):
    bl_idname = "camera.yl_cameraref_remove_scene_camera"
    bl_label = "Delete Active Camera"
    bl_description = "Delete the active camera."
    bl_translation_context = i18n.CONTEXT
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if get_valid_scene_camera(getattr(context, "scene", None)) is not None:
            return True
        cls.poll_message_set(i18n.tr_iface("No active camera"))
        return False

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        camera = get_valid_scene_camera(scene, clear_invalid=True)
        if camera is None:
            return {'CANCELLED'}

        shared_scenes = tuple(camera.users_scene)
        if len(shared_scenes) > 1:
            self.report(
                {'WARNING'},
                i18n.tr_report(
                    "Camera is used by multiple scenes and was not deleted."
                ),
            )
            return {'CANCELLED'}

        cameras = get_scene_cameras(scene)
        current_index = cameras.index(camera)
        remaining_cameras = [item for item in cameras if item != camera]
        if remaining_cameras:
            replacement_index = min(current_index, len(remaining_cameras) - 1)
            scene.camera = remaining_cameras[replacement_index]
        else:
            scene.camera = None

        camera_data = camera.data
        bpy.data.objects.remove(camera, do_unlink=True)
        if camera_data.users == 0:
            bpy.data.cameras.remove(camera_data)

        sync_scene_camera_state(scene, context=context)
        replacement_camera = get_valid_scene_camera(scene, clear_invalid=True)
        if replacement_camera is not None:
            show_camera_in_current_view(context, replacement_camera)
        tag_view3d_redraws(context)
        return {'FINISHED'}


class BG_PT_CameraSettingsPopover(Panel):
    bl_idname = "BG_PT_camera_settings_popover"
    bl_label = "Camera Settings"
    bl_translation_context = i18n.CONTEXT
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'

    @classmethod
    def poll(cls, context):
        return get_valid_scene_camera(getattr(context, "scene", None)) is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        camera = get_valid_scene_camera(scene, clear_invalid=True)
        if camera is None:
            layout.label(
                text="No active camera",
                text_ctxt=i18n.CONTEXT,
                icon='KEYTYPE_BREAKDOWN_VEC',
            )
            return

        camera_data = camera.data
        layout.prop(camera, "name", text="Name", text_ctxt=i18n.CONTEXT)
        layout.operator(
            BG_OT_DuplicateSceneCamera.bl_idname,
            text="Duplicate Camera",
            text_ctxt=i18n.CONTEXT,
            icon='DUPLICATE',
        )

        layout.separator()
        layout.label(text="Projection", text_ctxt=i18n.CONTEXT)
        projection_row = layout.row(align=True)
        projection_row.prop_enum(
            camera_data, "type", 'PERSP', text="Perspective", text_ctxt=i18n.CONTEXT
        )
        projection_row.prop_enum(
            camera_data, "type", 'ORTHO', text="Orthographic", text_ctxt=i18n.CONTEXT
        )
        if camera_data.type == 'ORTHO':
            layout.prop(
                camera_data, "ortho_scale", text="Ortho Scale", text_ctxt=i18n.CONTEXT
            )
        else:
            layout.prop(camera_data, "lens", text="Focal Length", text_ctxt=i18n.CONTEXT)

        layout.separator()
        layout.label(text="Clipping", text_ctxt=i18n.CONTEXT)
        clip_row = layout.row(align=True)
        clip_row.prop(camera_data, "clip_start", text="Start", text_ctxt=i18n.CONTEXT)
        clip_row.prop(camera_data, "clip_end", text="End", text_ctxt=i18n.CONTEXT)

        layout.separator()
        layout.label(text="Resolution", text_ctxt=i18n.CONTEXT)
        resolution_row = layout.row(align=True)
        resolution_row.prop(scene.render, "resolution_x", text="X")
        resolution_row.prop(scene.render, "resolution_y", text="Y")

        layout.separator()
        layout.prop(
            camera_data,
            "passepartout_alpha",
            text="Passepartout Opacity",
            text_ctxt=i18n.CONTEXT,
        )


CLASSES = (
    BG_OT_SelectSceneCamera,
    BG_MT_SceneCameras,
    BG_OT_DuplicateSceneCamera,
    BG_OT_RemoveSceneCamera,
    BG_PT_CameraSettingsPopover,
)
