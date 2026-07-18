"""Class registry for the add-on lifecycle."""

import bpy

from .. import features, properties, ui

CLASSES = (
    *properties.CLASSES,
    *features.CLASSES,
    *ui.CLASSES,
)


def register_classes():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister_classes():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
