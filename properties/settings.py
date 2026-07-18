"""Scene properties for the add-on."""

from bpy.props import BoolProperty, FloatProperty, IntProperty
from bpy.types import PropertyGroup

from .. import i18n


class BG_AdjustRuntimeSettings(PropertyGroup):
    running: BoolProperty(
        options={'HIDDEN', 'SKIP_SAVE'},
        default=False,
    )
    reset_requested: BoolProperty(
        options={'HIDDEN', 'SKIP_SAVE'},
        default=False,
    )


def update_active_alpha(self, context):
    if self.is_updating:
        return

    from ..core.camera import apply_alpha_to_scene_cameras

    apply_alpha_to_scene_cameras(getattr(context, "scene", None), self.active_alpha)


def update_active_image_index(self, context):
    if self.is_updating:
        return

    from ..core.camera import get_camera_and_settings, sync_ui_alpha_from_active

    cam, settings = get_camera_and_settings(context)
    if not cam or not settings:
        return
    bg_images = cam.data.background_images
    total = len(bg_images)
    if total == 0:
        return

    index = min(settings.active_image_index, total - 1)
    self.is_updating = True
    try:
        for i, bg in enumerate(bg_images):
            bg.show_background_image = (i == index)
    finally:
        self.is_updating = False
    sync_ui_alpha_from_active(settings, context=context)


def update_opacity_enable(self, context):
    if self.is_updating:
        return

    from ..core.camera import apply_alpha_to_scene_cameras, get_active_camera_bg

    cam, settings, active_bg = get_active_camera_bg(context)
    if not cam:
        return

    try:
        self.is_updating = True
        if self.enable_control:
            cam.data.show_background_images = True
            if active_bg:
                active_bg.show_background_image = True
                self.active_alpha = self.stored_opacity
                apply_alpha_to_scene_cameras(getattr(context, "scene", None), self.active_alpha)
        else:
            if active_bg:
                self.stored_opacity = self.active_alpha
            cam.data.show_background_images = False
    finally:
        self.is_updating = False


class BG_Opacity_Settings(PropertyGroup):
    is_updating: BoolProperty(
        options={'HIDDEN', 'SKIP_SAVE'},
        default=False,
    )
    enable_control: BoolProperty(
        name="Enable Control",
        translation_context=i18n.CONTEXT,
        default=True,
        update=update_opacity_enable,
    )
    show_header_controls: BoolProperty(
        name="Show Opacity in Header",
        description="Show the reference opacity control in the 3D View header",
        translation_context=i18n.CONTEXT,
        default=False,
    )
    active_alpha: FloatProperty(
        name="Opacity",
        translation_context=i18n.CONTEXT,
        default=1.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
        update=update_active_alpha,
    )
    stored_opacity: FloatProperty(
        name="Stored Opacity",
        translation_context=i18n.CONTEXT,
        default=1.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )
    active_image_index: IntProperty(
        name="Active Image Index",
        translation_context=i18n.CONTEXT,
        default=0,
        min=0,
        update=update_active_image_index,
    )
