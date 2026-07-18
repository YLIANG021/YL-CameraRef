"""Context queries shared by camera tools."""

from ..adjust import is_camera_view


def get_view_camera(context):
    if not is_camera_view(context):
        return None

    space = getattr(context, "space_data", None)
    scene = getattr(context, "scene", None)
    camera = getattr(space, "camera", None) or getattr(scene, "camera", None)
    if camera is None or camera.type != 'CAMERA':
        return None
    return camera


def get_perspective_view_camera(context):
    camera = get_view_camera(context)
    if camera is None or camera.data.type != 'PERSP':
        return None
    return camera


def get_active_transform_target(context, camera):
    if getattr(context, "mode", None) != 'OBJECT':
        return None

    target = getattr(context, "active_object", None)
    if target is None or target == camera or not target.select_get():
        return None
    if target.library is not None and target.override_library is None:
        return None
    return target
