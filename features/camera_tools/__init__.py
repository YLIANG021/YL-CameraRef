"""Optional camera workflow tools."""

import bpy
from bpy.props import PointerProperty

from . import dolly, perspective_depth, resolution
from .properties import BG_CameraToolsSettings, CLASSES as PROPERTY_CLASSES


CLASSES = (
    *PROPERTY_CLASSES,
    *resolution.CLASSES,
)


def register_properties():
    bpy.types.Scene.yl_camera_tools = PointerProperty(type=BG_CameraToolsSettings)


def unregister_properties():
    if hasattr(bpy.types.Scene, "yl_camera_tools"):
        del bpy.types.Scene.yl_camera_tools


__all__ = (
    "CLASSES",
    "dolly",
    "perspective_depth",
    "register_properties",
    "resolution",
    "unregister_properties",
)
