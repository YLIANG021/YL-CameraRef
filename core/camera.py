"""Camera and background-image state helpers."""

import bpy


def get_valid_scene_camera(scene, clear_invalid=False):
    if not scene:
        return None

    cam = getattr(scene, "camera", None)
    if cam is None:
        return None

    try:
        cam_name = cam.name
        cam_type = cam.type
        cam_data = cam.data
    except ReferenceError:
        if clear_invalid:
            try:
                scene.camera = None
            except ReferenceError:
                pass
        return None

    scene_camera = scene.objects.get(cam_name)
    if cam_name not in bpy.data.objects or scene_camera != cam:
        if clear_invalid:
            scene.camera = None
        return None

    if cam_type != 'CAMERA' or not cam_data:
        return None

    return cam


def get_camera_and_settings(context):
    if isinstance(context, dict):
        scene = context.get('scene')
    else:
        scene = getattr(context, 'scene', None)

    cam = get_valid_scene_camera(scene, clear_invalid=True)
    if not scene or not cam:
        return None, None
    return cam, scene.bg_opacity_settings


def get_active_camera_bg(context):
    cam, settings = get_camera_and_settings(context)
    if not cam or not settings:
        return None, None, None
    bg_images = cam.data.background_images
    if not bg_images:
        return cam, settings, None
    index = min(settings.active_image_index, len(bg_images) - 1)
    if index < 0:
        return cam, settings, None
    return cam, settings, bg_images[index]


def apply_alpha_to_scene_cameras(scene, alpha):
    cam = get_valid_scene_camera(scene, clear_invalid=True)
    if not cam:
        return

    for bg in cam.data.background_images:
        if bg.alpha != alpha:
            bg.alpha = alpha


def sync_ui_alpha_from_active(settings, context=None):
    if context is None:
        context = bpy.context
    _, _, active_bg = get_active_camera_bg(context)
    if not active_bg:
        return

    settings.is_updating = True
    try:
        settings.active_alpha = active_bg.alpha
    finally:
        settings.is_updating = False


def sync_scene_camera_state(scene, context=None):
    """Synchronize scene-level controls after the active camera changes."""
    if not scene:
        return

    cam = get_valid_scene_camera(scene, clear_invalid=True)
    if not cam:
        return

    settings = getattr(scene, "bg_opacity_settings", None)
    if settings is None:
        return

    bg_images = cam.data.background_images
    cam.data.show_background_images = settings.enable_control
    if not bg_images:
        return

    visible_index = next(
        (index for index, bg in enumerate(bg_images) if bg.show_background_image),
        None,
    )
    active_index = (
        visible_index
        if visible_index is not None
        else min(settings.active_image_index, len(bg_images) - 1)
    )

    settings.is_updating = True
    try:
        settings.active_image_index = active_index
        settings.active_alpha = bg_images[active_index].alpha
        for index, bg in enumerate(bg_images):
            bg.show_background_image = index == active_index
    finally:
        settings.is_updating = False
