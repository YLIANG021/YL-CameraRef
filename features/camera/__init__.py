"""Camera workflow operators."""

from . import add_view_camera, camera_list

CLASSES = (
    *add_view_camera.CLASSES,
    *camera_list.CLASSES,
)

__all__ = (
    "CLASSES",
    "add_view_camera",
    "camera_list",
)
