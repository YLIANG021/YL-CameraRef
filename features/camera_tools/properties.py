"""Runtime settings for the optional camera tools panel."""

import bpy

from ... import i18n


def update_dolly_value(self, context):
    from .dolly import update_camera_dolly

    update_camera_dolly(self, context)


def update_depth_value(self, context):
    from .perspective_depth import update_camera_depth

    update_camera_depth(self, context)


class BG_CameraToolsSettings(bpy.types.PropertyGroup):
    show_tools: bpy.props.BoolProperty(
        name="Show CameraRef Tools",
        translation_context=i18n.CONTEXT,
        default=False,
        options={'SKIP_SAVE'},
    )
    keep_subject_framing: bpy.props.BoolProperty(
        name="Keep Subject Framing",
        description="Adjust focal length while dollying to preserve the selected subject's framing",
        translation_context=i18n.CONTEXT,
        default=False,
        options={'SKIP_SAVE'},
    )
    dolly_value: bpy.props.FloatProperty(
        name="Distance",
        description="Move the camera forward or backward along its viewing axis",
        translation_context=i18n.CONTEXT,
        default=0.0,
        precision=3,
        options={'SKIP_SAVE'},
        update=update_dolly_value,
    )
    dolly_previous: bpy.props.FloatProperty(
        options={'HIDDEN', 'SKIP_SAVE'},
        default=0.0,
    )
    depth_value: bpy.props.FloatProperty(
        name="Depth",
        description="Move the selected object in depth without changing its camera-view framing",
        translation_context=i18n.CONTEXT,
        default=0.0,
        precision=3,
        options={'SKIP_SAVE'},
        update=update_depth_value,
    )
    depth_previous: bpy.props.FloatProperty(
        options={'HIDDEN', 'SKIP_SAVE'},
        default=0.0,
    )


CLASSES = (BG_CameraToolsSettings,)
