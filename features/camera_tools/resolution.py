"""Render-resolution helpers based on the active reference image."""

from bpy.types import Operator

from ... import i18n
from ...core.camera import get_active_camera_bg


def get_reference_dimensions(context):
    active_bg = get_active_camera_bg(context)[2]
    if active_bg is None:
        return None

    source = getattr(active_bg, "image", None) or getattr(active_bg, "clip", None)
    size = getattr(source, "size", None) if source else None
    if not size or len(size) < 2:
        return None

    width, height = int(size[0]), int(size[1])
    if width <= 0 or height <= 0:
        return None
    return width, height


class BG_OT_UseReferenceImageSize(Operator):
    bl_idname = "camera.yl_cameraref_match_reference_resolution"
    bl_label = "Match Reference Resolution"
    bl_description = "Set the render resolution to the active reference image dimensions"
    bl_translation_context = i18n.CONTEXT
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if get_reference_dimensions(context) is not None:
            return True
        cls.poll_message_set(i18n.tr_iface("Select a camera with a reference image."))
        return False

    def execute(self, context):
        width, height = get_reference_dimensions(context)
        render = context.scene.render
        render.resolution_x = width
        render.resolution_y = height
        render.resolution_percentage = 100
        render.pixel_aspect_x = 1.0
        render.pixel_aspect_y = 1.0
        self.report(
            {'INFO'},
            i18n.tr_report(
                "Render resolution set to {width} x {height}.",
                width=width,
                height=height,
            ),
        )
        return {'FINISHED'}


CLASSES = (
    BG_OT_UseReferenceImageSize,
)
