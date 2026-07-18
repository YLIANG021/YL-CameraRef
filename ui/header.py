"""3D View header controls."""

import bpy

from ..core.camera import get_active_camera_bg


def is_header_mode_allowed(context):
    mode = getattr(context, "mode", "")
    return mode == 'OBJECT' or mode == 'SCULPT' or mode.startswith('EDIT_')


def draw_header_opacity_controls(self, context):
    scene = getattr(context, "scene", None)
    settings = getattr(scene, "bg_opacity_settings", None)
    if not settings or not settings.show_header_controls:
        return
    if not is_header_mode_allowed(context):
        return

    _, _, active_bg = get_active_camera_bg(context)
    source = (
        getattr(active_bg, "image", None) or getattr(active_bg, "clip", None)
        if active_bg is not None
        else None
    )
    if source is None:
        return

    layout = self.layout
    slider_row = layout.row(align=True)
    slider_row.scale_x = 1.05
    if settings.enable_control:
        slider_row.prop(settings, "active_alpha", text="", slider=True)
    else:
        slider_row.enabled = False
        slider_row.prop(settings, "stored_opacity", text="", slider=True)


def register_header():
    bpy.types.VIEW3D_HT_header.append(draw_header_opacity_controls)


def unregister_header():
    bpy.types.VIEW3D_HT_header.remove(draw_header_opacity_controls)
