# SPDX-License-Identifier: GPL-3.0-or-later

"""YL CameraRef extension entry point."""

from .core.lifecycle import register, unregister

__all__ = (
    "register",
    "unregister",
)
