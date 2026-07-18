"""Optional camera tools panel."""

from bpy.types import Panel

from .. import i18n
from ..core.camera import get_active_camera_bg, get_valid_scene_camera
from ..features.camera_tools import dolly, perspective_depth, resolution
from ..features.camera_tools.context import (
    get_active_transform_target,
    get_perspective_view_camera,
    get_view_camera,
)


class IMAGE_SWITCHER_PT_CameraTools(Panel):
    bl_label = "CameraRef Tools"
    bl_translation_context = i18n.CONTEXT
    bl_idname = "IMAGE_SWITCHER_PT_cameraref_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'YL CameraRef'
    bl_order = 6

    @classmethod
    def poll(cls, context):
        scene = getattr(context, "scene", None)
        settings = getattr(scene, "yl_camera_tools", None)
        return bool(
            settings
            and settings.show_tools
            and get_valid_scene_camera(scene) is not None
        )

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.yl_camera_tools
        view_camera = get_view_camera(context)
        perspective_camera = get_perspective_view_camera(context)
        display_camera = view_camera or scene.camera
        active_bg = get_active_camera_bg(context)[2]
        has_reference_image = bool(
            active_bg
            and (getattr(active_bg, "image", None) or getattr(active_bg, "clip", None))
        )
        target = (
            get_active_transform_target(context, perspective_camera)
            if perspective_camera
            else None
        )

        header_controls_row = layout.row()
        header_controls_row.scale_y = 1.1
        header_controls_row.enabled = has_reference_image
        header_controls_row.prop(
            scene.bg_opacity_settings,
            "show_header_controls",
            text="Show Opacity in Header",
            text_ctxt=i18n.CONTEXT,
            icon='TOPBAR',
            toggle=True,
        )

        if perspective_camera is not None:
            depth_section = layout.column(align=True)
            depth_section.label(text="Object Depth", text_ctxt=i18n.CONTEXT)
            depth_row = depth_section.row()
            depth_row.enabled = target is not None
            depth_row.prop(
                settings,
                perspective_depth.PROP_DEPTH,
                text="Depth",
                text_ctxt=i18n.CONTEXT,
            )

            dolly_section = layout.column(align=True)
            dolly_header = dolly_section.row(align=True)
            dolly_header.label(text="Camera Dolly", text_ctxt=i18n.CONTEXT)
            if settings.keep_subject_framing:
                target_text = (
                    i18n.tr_iface("Target: {name}", name=target.name)
                    if target
                    else i18n.tr_iface("Target: Not Selected")
                )
                target_label = dolly_header.row(align=True)
                target_label.alignment = 'RIGHT'
                target_label.label(text=target_text, translate=False)
            dolly_row = dolly_section.row()
            dolly_row.enabled = not settings.keep_subject_framing or target is not None
            dolly_row.prop(
                settings,
                dolly.PROP_DOLLY,
                text="Distance",
                text_ctxt=i18n.CONTEXT,
            )

            dolly_section.prop(
                settings,
                "keep_subject_framing",
                text="Keep Subject Framing",
                text_ctxt=i18n.CONTEXT,
            )

        shift_section = layout.column(align=True)
        shift_section.label(text="Camera Shift", text_ctxt=i18n.CONTEXT)
        shift_row = shift_section.row(align=True)
        shift_row.enabled = display_camera is not None
        if display_camera is None:
            shift_row.label(text="No active camera", text_ctxt=i18n.CONTEXT)
        else:
            shift_row.prop(display_camera.data, "shift_x", text="X")
            shift_row.prop(display_camera.data, "shift_y", text="Y")

        resolution_section = layout.column(align=True)
        resolution_section.label(text="Render Resolution", text_ctxt=i18n.CONTEXT)
        resolution_row = resolution_section.row()
        resolution_row.enabled = resolution.get_reference_dimensions(context) is not None
        resolution_row.operator(
            resolution.BG_OT_UseReferenceImageSize.bl_idname,
            text="Match Reference",
            text_ctxt=i18n.CONTEXT,
        )


CLASSES = (IMAGE_SWITCHER_PT_CameraTools,)
