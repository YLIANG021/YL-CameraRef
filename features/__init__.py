"""Feature modules."""

from . import adjust, background_images, camera_tools
from .camera import add_view_camera, camera_list

CLASSES = (
    *background_images.CLASSES,
    *adjust.CLASSES,
    *add_view_camera.CLASSES,
    *camera_list.CLASSES,
    *camera_tools.CLASSES,
)

__all__ = (
    "CLASSES",
    "add_view_camera",
    "camera_list",
    "camera_tools",
    "adjust",
    "background_images",
)
