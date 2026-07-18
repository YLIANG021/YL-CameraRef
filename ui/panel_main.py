"""Main Reference Images panel."""

from bpy.types import Panel

from .. import i18n
from ..core.camera import get_active_camera_bg
from ..features import adjust
from ..features.background_images import (
    BG_OT_AddImage,
    BG_OT_RemoveImage,
    BG_OT_ResetAdjust,
    BG_OT_ToggleDepth,
    BG_OT_ToggleEnable,
    BG_PT_ImageSettingsPopover,
)
from ..features.camera.add_view_camera import BG_OT_NewCameraFromView
from ..features.camera.camera_list import (
    BG_MT_SceneCameras,
    BG_OT_RemoveSceneCamera,
    BG_PT_CameraSettingsPopover,
    get_scene_cameras,
)


class IMAGE_SWITCHER_PT_Panel(Panel):
    bl_label = "YL CameraRef"
    bl_translation_context = i18n.CONTEXT
    bl_idname = "IMAGE_SWITCHER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'YL CameraRef'
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        cam, settings, active_bg = get_active_camera_bg(context)
        scene_cameras = get_scene_cameras(context.scene)

        if not scene_cameras:
            create_row = layout.row()
            create_row.scale_y = 1.5
            create_row.operator(
                BG_OT_NewCameraFromView.bl_idname,
                text="Add Camera from View",
                text_ctxt=i18n.CONTEXT,
                icon='ADD',
            )
            layout.label(
                text="No cameras in scene",
                text_ctxt=i18n.CONTEXT,
                icon='KEYTYPE_BREAKDOWN_VEC',
            )
            return

        camera_row = layout.row(align=True)
        camera_row.scale_y = 1.1
        if cam:
            camera_row.menu(
                BG_MT_SceneCameras.bl_idname,
                text=cam.name,
                translate=False,
                icon='CAMERA_DATA',
            )
        else:
            camera_row.menu(
                BG_MT_SceneCameras.bl_idname,
                text="Select Camera",
                text_ctxt=i18n.CONTEXT,
                icon='CAMERA_DATA',
            )
        camera_row.operator(BG_OT_NewCameraFromView.bl_idname, text="", icon='ADD')

        if cam:
            camera_row.operator(BG_OT_RemoveSceneCamera.bl_idname, text="", icon='REMOVE')
            camera_row.popover(
                panel=BG_PT_CameraSettingsPopover.bl_idname,
                text="",
                icon='PREFERENCES',
            )

        if not cam:
            layout.label(
                text="Select a camera or create one from the current view.",
                text_ctxt=i18n.CONTEXT,
                icon='KEYTYPE_BREAKDOWN_VEC',
            )
            return

        layout.row().label(text="Reference Images", text_ctxt=i18n.CONTEXT)

        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator(BG_OT_AddImage.bl_idname, text="Add", text_ctxt=i18n.CONTEXT)
        row.operator(BG_OT_RemoveImage.bl_idname, text="Remove", text_ctxt=i18n.CONTEXT)

        runtime = adjust.get_adjust_runtime(context)
        is_running = bool(runtime and runtime.running)
        has_reference_image = bool(
            active_bg
            and (getattr(active_bg, "image", None) or getattr(active_bg, "clip", None))
        )
        adjust_button = row.row(align=True)
        adjust_button.enabled = has_reference_image and adjust.is_camera_view(context)
        adjust_button.operator(
            adjust.VIEW3D_OT_yl_cameraref_adjust_reference.bl_idname,
            text="Adjust",
            text_ctxt=i18n.CONTEXT,
            depress=is_running,
        )
        image_settings = row.row(align=True)
        image_settings.enabled = active_bg is not None
        if is_running:
            image_settings.operator(BG_OT_ResetAdjust.bl_idname, text="", icon='FILE_REFRESH')
        else:
            image_settings.popover(
                panel=BG_PT_ImageSettingsPopover.bl_idname,
                text="",
                icon='PREFERENCES',
            )

        layout.template_list(
            "BG_UL_BackgroundImages",
            "",
            cam.data,
            "background_images",
            settings,
            "active_image_index",
            rows=4,
        )

        main_box = layout.box()
        is_controllable = bool(active_bg)

        control_row = main_box.row(align=True)
        control_row.scale_y = 1.2
        if not is_controllable:
            control_row.enabled = False

        control_row.operator(
            BG_OT_ToggleEnable.bl_idname,
            text="",
            icon='OUTLINER_OB_IMAGE' if settings.enable_control else 'PANEL_CLOSE',
            depress=settings.enable_control,
        )

        if settings.enable_control:
            control_row.prop(
                settings,
                "active_alpha",
                text="Opacity",
                text_ctxt=i18n.CONTEXT,
                slider=True,
            )
        else:
            disabled_row = control_row.row()
            disabled_row.enabled = False
            disabled_row.prop(
                settings,
                "stored_opacity",
                text="Opacity",
                text_ctxt=i18n.CONTEXT,
                slider=True,
            )

        if is_controllable and settings.enable_control:
            main_box.label(text="Image Layer", text_ctxt=i18n.CONTEXT)
            depth_row = main_box.row()
            depth_row.scale_y = 1.1
            depth_icon = 'SORT_ASC' if active_bg.display_depth == 'FRONT' else 'SORT_DESC'
            depth_text = "Front" if active_bg.display_depth == 'FRONT' else "Back"
            depth_row.operator(
                BG_OT_ToggleDepth.bl_idname,
                text=depth_text,
                text_ctxt=i18n.CONTEXT,
                icon=depth_icon,
            )

        camera_tool_settings = context.scene.yl_camera_tools
        layout.separator(factor=0.65)
        layout.prop(
            camera_tool_settings,
            "show_tools",
            text="Show CameraRef Tools",
            text_ctxt=i18n.CONTEXT,
        )


CLASSES = (
    IMAGE_SWITCHER_PT_Panel,
)
