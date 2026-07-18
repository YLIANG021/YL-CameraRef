import bpy
import gpu
import blf
import math
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils

from .. import i18n
from ..core.camera import get_active_camera_bg

WM_PROP_RUNTIME = "yl_cameraref_runtime"
_active_adjust_operator = None


def is_camera_view(context):
    area = getattr(context, "area", None)
    space = getattr(context, "space_data", None)
    region_3d = getattr(space, "region_3d", None)
    return bool(area and area.type == 'VIEW_3D' and region_3d and region_3d.view_perspective == 'CAMERA')


def get_adjust_runtime(context):
    wm = getattr(context, "window_manager", None)
    return getattr(wm, WM_PROP_RUNTIME, None) if wm is not None else None


def stop_active_adjust(context=None):
    operator = _active_adjust_operator
    if operator is not None:
        operator._exit(context or bpy.context)
        return

    runtime = get_adjust_runtime(context or bpy.context)
    if runtime is None:
        return
    runtime.reset_requested = False
    runtime.running = False


class VIEW3D_OT_yl_cameraref_adjust_reference(bpy.types.Operator):
    bl_idname = "view3d.yl_cameraref_adjust_reference"
    bl_label = "Adjust Reference"
    bl_description = "Interactively move, scale, and rotate the active reference"
    bl_translation_context = i18n.CONTEXT
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if not is_camera_view(context):
            cls.poll_message_set("Switch to Camera View to adjust the reference image")
            return False
        active_bg = get_active_camera_bg(context)[2]
        source = (
            getattr(active_bg, "image", None) or getattr(active_bg, "clip", None)
            if active_bg is not None
            else None
        )
        if source is None:
            cls.poll_message_set(i18n.tr_iface("Select a camera with a reference image."))
            return False
        return True

    def invoke(self, context, event):
        global _active_adjust_operator

        runtime = get_adjust_runtime(context)
        if runtime is None:
            return {'CANCELLED'}
        if runtime.running:
            stop_active_adjust(context)
            return {'FINISHED'}

        cam = context.scene.camera
        if not cam or not cam.data.background_images:
            self.report({'WARNING'}, i18n.tr_report("Select a camera with a reference image."))
            return {'CANCELLED'}

        bg_images = cam.data.background_images
        settings = getattr(context.scene, 'bg_opacity_settings', None)
        active_index = settings.active_image_index if settings else 0
        active_index = max(0, min(active_index, len(bg_images) - 1))
        if settings and settings.active_image_index != active_index:
            settings.active_image_index = active_index

        self.camera = cam
        self.bg_index = active_index
        self.bg = bg_images[active_index]
        self._camera_pointer = cam.as_pointer()
        self._bg_pointer = self.bg.as_pointer()
        source = getattr(self.bg, "image", None) or getattr(self.bg, "clip", None)
        self._source_pointer = source.as_pointer() if source else None
        self.action = None
        self.action_source = None
        self.axis_lock = None
        self.start_mx = 0
        self.start_my = 0
        self.start_offset = (0.0, 0.0)
        self.start_scale = 1.0
        self.start_rotation = 0.0
        self.last_shift = event.shift
        self.last_ctrl = event.ctrl
        self._cached_bounds = None
        self._cached_region_origin = None
        self._start_bounds = None
        self._transform_center = None
        self._start_mouse_distance = 1.0
        self._start_mouse_angle = 0.0
        self._is_navigating = False
        self._history = [self._capture_state()]

        # Pixel-to-offset calibration is measured in _reset_start.
        self._px_to_offset_x = 0.001
        self._px_to_offset_y = 0.001

        try:
            self.shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
            self.is_polyline = True
        except ValueError:
            self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            self.is_polyline = False

        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, (), 'WINDOW', 'POST_PIXEL'
        )
        runtime.reset_requested = False
        runtime.running = True
        _active_adjust_operator = self
        context.window_manager.modal_handler_add(self)
        self._tag_all_viewports(context)
        return {'RUNNING_MODAL'}

    def _exit(self, context):
        global _active_adjust_operator

        runtime = get_adjust_runtime(context)
        if runtime is not None:
            runtime.reset_requested = False
            runtime.running = False
        if hasattr(self, "_draw_handle") and self._draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
        if _active_adjust_operator is self:
            _active_adjust_operator = None
        self._tag_all_viewports(context)

    def _tag_all_viewports(self, context):
        screen = getattr(context, "screen", None)
        if screen is None:
            return
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    def _target_is_valid(self, context):
        """The modal tool never silently changes the camera or image it edits."""
        try:
            scene = getattr(context, "scene", None)
            cam = getattr(scene, "camera", None)
            if cam is None or cam.as_pointer() != self._camera_pointer:
                return False

            bg_images = cam.data.background_images
            if not (0 <= self.bg_index < len(bg_images)):
                return False
            if bg_images[self.bg_index].as_pointer() != self._bg_pointer:
                return False

            source = getattr(bg_images[self.bg_index], "image", None) or getattr(
                bg_images[self.bg_index], "clip", None
            )
            source_pointer = source.as_pointer() if source else None
            if source_pointer != self._source_pointer:
                return False

            settings = getattr(scene, "bg_opacity_settings", None)
            return settings is None or settings.active_image_index == self.bg_index
        except (AttributeError, ReferenceError, RuntimeError):
            return False

    def _stop_for_target_change(self, context):
        self._exit(context)
        self.report(
            {'INFO'},
            i18n.tr_report(
                "Adjustment stopped because the camera or reference image changed."
            ),
        )
        return {'FINISHED'}

    def _rebase_after_external_reset(self, context):
        self.action = None
        self.action_source = None
        self.axis_lock = None
        self._start_bounds = None
        self._transform_center = None
        self._history = [self._capture_state()]
        self._tag_all_viewports(context)

    def _capture_state(self):
        return (
            float(self.bg.offset[0]),
            float(self.bg.offset[1]),
            float(self.bg.scale),
            float(self.bg.rotation),
        )

    def _apply_state(self, state):
        offset_x, offset_y, scale, rotation = state
        self.bg.offset[0] = offset_x
        self.bg.offset[1] = offset_y
        self.bg.scale = scale
        self.bg.rotation = rotation

    def _commit_history(self):
        state = self._capture_state()
        if state != self._history[-1]:
            self._history.append(state)

    def _undo_last_action(self, context):
        if len(self._history) > 1:
            self._history.pop()
            self._apply_state(self._history[-1])
        self._tag_all_viewports(context)

    def _finish_action(self, context, commit=False):
        if commit:
            self._commit_history()
        self.action = None
        self.action_source = None
        self.axis_lock = None
        self._start_bounds = None
        self._transform_center = None
        self._tag_all_viewports(context)

    def _cancel_action(self, context):
        if self.action == 'MOVE':
            self.bg.offset[0] = self.start_offset[0]
            self.bg.offset[1] = self.start_offset[1]
        elif self.action == 'SCALE':
            self.bg.scale = self.start_scale
        elif self.action == 'ROTATE':
            self.bg.rotation = self.start_rotation
        self._finish_action(context)

    def _start_action(self, action, event, context, source='KEYBOARD'):
        self.action = action
        self.action_source = source
        if action != 'MOVE':
            self.axis_lock = None
        self._reset_start(event, context)
        self._tag_all_viewports(context)

    def get_camera_bounds(self, region, rv3d, cam, scene):
        try:
            frame = cam.data.view_frame(scene=scene)
            frame_world = [cam.matrix_world @ corner for corner in frame]
            points = []
            for corner in frame_world:
                p2d = view3d_utils.location_3d_to_region_2d(region, rv3d, corner)
                if p2d is None:
                    return None
                points.append((p2d.x, p2d.y))
            return points
        except Exception:
            return None

    def _get_active_region_rv3d(self, context):
        """Return the active camera-view 3D viewport region and RV3D."""
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                rv3d = space.region_3d if space else None
                if not rv3d or rv3d.view_perspective != 'CAMERA':
                    continue
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return region, rv3d
        return None, None

    def _find_camera_region_at_mouse(self, context, mouse_x, mouse_y):
        for area in context.screen.areas:
            if not (area.x <= mouse_x <= area.x + area.width and area.y <= mouse_y <= area.y + area.height):
                continue
            if area.type != 'VIEW_3D':
                return None, None, None
            space = area.spaces.active
            rv3d = space.region_3d if space else None
            if not rv3d or rv3d.view_perspective != 'CAMERA':
                return None, None, None
            for region in area.regions:
                if region.type == 'WINDOW':
                    if region.x <= mouse_x <= region.x + region.width and region.y <= mouse_y <= region.y + region.height:
                        return area, region, rv3d
            return None, None, None
        return None, None, None

    def _is_view3d_window_at_mouse(self, context, mouse_x, mouse_y):
        for area in context.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            if not (area.x <= mouse_x <= area.x + area.width and area.y <= mouse_y <= area.y + area.height):
                continue
            for region in area.regions:
                if region.type == 'WINDOW' and region.x <= mouse_x <= region.x + region.width and region.y <= mouse_y <= region.y + region.height:
                    return True
        return False

    def _is_view3d_ui_at_mouse(self, context, mouse_x, mouse_y):
        for area in context.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            if not (area.x <= mouse_x <= area.x + area.width and area.y <= mouse_y <= area.y + area.height):
                continue
            for region in area.regions:
                if region.type == 'UI' and region.x <= mouse_x <= region.x + region.width and region.y <= mouse_y <= region.y + region.height:
                    return True
        return False

    def _calc_bounds_tuple(self, region, rv3d, cam, scene):
        points = self.get_camera_bounds(region, rv3d, cam, scene)
        if not points:
            return None
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        return (min_x, max_x, min_y, max_y)

    def _get_bg_source_aspect(self, fallback_aspect):
        source = getattr(self.bg, "image", None) or getattr(self.bg, "clip", None)
        if source is None:
            return max(float(fallback_aspect), 1e-6)

        size = getattr(source, "size", None)
        if not size or len(size) < 2 or size[0] <= 0 or size[1] <= 0:
            return max(float(fallback_aspect), 1e-6)

        display_aspect = getattr(source, "display_aspect", (1.0, 1.0))
        aspect_x = max(float(display_aspect[0]), 1e-6)
        aspect_y = max(float(display_aspect[1]), 1e-6)
        return (float(size[0]) * aspect_x) / (float(size[1]) * aspect_y)

    def _calibrate_px_to_offset(self, context, event=None):
        """
        Calibrate offset movement from the on-screen camera width.

        Blender background-image offsets feel closest to width-normalized
        movement on both axes, so one shared baseline keeps extreme aspect
        ratios from moving too quickly on either axis.
        """
        cam = context.scene.camera
        bounds = None
        region_origin = None

        if event is not None:
            _, region, rv3d = self._find_camera_region_at_mouse(context, event.mouse_x, event.mouse_y)
            if region is not None and rv3d is not None:
                bounds = self._calc_bounds_tuple(region, rv3d, cam, context.scene)
                region_origin = (region.x, region.y)

        if bounds is None and self._cached_bounds is not None:
            bounds = self._cached_bounds
            region_origin = self._cached_region_origin

        if bounds is None:
            region, rv3d = self._get_active_region_rv3d(context)
            if region is not None and rv3d is not None:
                bounds = self._calc_bounds_tuple(region, rv3d, cam, context.scene)
                region_origin = (region.x, region.y)

        if bounds is None:
            self._px_to_offset_x = 0.001
            self._px_to_offset_y = 0.001
            self._transform_center = (self.start_mx, self.start_my)
            return

        self._start_bounds = bounds
        min_x, max_x, min_y, max_y = bounds
        cam_w = max(max_x - min_x, 1.0)
        cam_h = max(max_y - min_y, 1.0)

        image_aspect = self._get_bg_source_aspect(cam_w / cam_h)

        # Blender maps X offset to camera-frame width and Y offset to that same
        # width divided by image aspect. Background-image scale is unrelated.
        self._px_to_offset_x = 1.0 / cam_w
        self._px_to_offset_y = image_aspect / cam_w

        origin_x, origin_y = region_origin or (0.0, 0.0)
        image_center_x = (min_x + max_x) * 0.5 + self.start_offset[0] * cam_w
        image_center_y = (min_y + max_y) * 0.5 + self.start_offset[1] * cam_w / image_aspect
        self._transform_center = (
            origin_x + image_center_x,
            origin_y + image_center_y,
        )

    def draw_callback(self):
        context = bpy.context
        if not self._target_is_valid(context):
            return
        scene = context.scene
        cam = self.camera

        area = context.area
        region = context.region
        space = context.space_data

        if not area or area.type != 'VIEW_3D':
            return
        if not region or region.type != 'WINDOW':
            return

        rv3d = getattr(space, "region_3d", None)
        if not rv3d or rv3d.view_perspective != 'CAMERA':
            return

        points = self.get_camera_bounds(region, rv3d, cam, scene)
        if not points:
            return

        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        self._cached_bounds = (min_x, max_x, min_y, max_y)
        self._cached_region_origin = (region.x, region.y)

        alpha_main = 0.15 if self.action else 1.0

        self.draw_gpu_rect(region, points, alpha_main)
        mode_color = (1.0, 0.9, 0.1, 1.0) if self.action else (0.8, 0.8, 0.8, 0.9)
        if self.action == 'MOVE':
            if self.axis_lock:
                hud_text = i18n.tr_iface(
                    "Move {axis}: {x:.3f}, {y:.3f}",
                    axis=self.axis_lock,
                    x=self.bg.offset[0],
                    y=self.bg.offset[1],
                )
            else:
                hud_text = i18n.tr_iface(
                    "Move: {x:.3f}, {y:.3f}",
                    x=self.bg.offset[0],
                    y=self.bg.offset[1],
                )
        elif self.action == 'SCALE':
            hud_text = i18n.tr_iface("Scale: {value:.3f}", value=self.bg.scale)
        elif self.action == 'ROTATE':
            hud_text = i18n.tr_iface(
                "Rotation: {value:.1f} deg",
                value=math.degrees(self.bg.rotation),
            )
        else:
            hud_text = i18n.tr_iface("Mode: Idle")
        hud_x = min_x + 16
        hud_y = max_y - 31
        hud_width = max(max_x - min_x - 32, 104)
        self.draw_hud_text(
            region,
            hud_text,
            x=hud_x,
            y=hud_y,
            color=mode_color,
            size=21,
            max_width=hud_width,
        )

        shortcut_color = (0.9, 0.95, 1.0, 0.9)
        shortcut_lines = (
            i18n.tr_iface("LMB/G Move | S Scale | R Rotate"),
            i18n.tr_iface("X/Y Lock | Shift Fine | Ctrl Snap"),
            i18n.tr_iface("RMB/Esc Exit"),
        )
        for line_index, text in enumerate(shortcut_lines, start=1):
            self.draw_hud_text(
                region,
                text,
                x=hud_x,
                y=hud_y - line_index * 26,
                color=shortcut_color,
                size=17,
                max_width=hud_width,
            )

    def draw_gpu_rect(self, region, points, alpha_outer):
        loop_pts = points + [points[0]]
        batch_outer = batch_for_shader(self.shader, 'LINE_STRIP', {"pos": loop_pts})

        gpu.state.blend_set('ALPHA')
        try:
            self.shader.bind()
            if self.is_polyline:
                self.shader.uniform_float("viewportSize", (region.width, region.height))
                self.shader.uniform_float("lineWidth", 2.5)
                self.shader.uniform_float("color", (1.0, 0.9, 0.1, alpha_outer))
                batch_outer.draw(self.shader)
            else:
                gpu.state.line_width_set(2.5)
                self.shader.uniform_float("color", (1.0, 0.9, 0.1, alpha_outer))
                batch_outer.draw(self.shader)
        finally:
            if not self.is_polyline:
                gpu.state.line_width_set(1.0)
            gpu.state.blend_set('NONE')

    def draw_hud_text(
        self,
        region,
        text,
        x=20,
        y=80,
        color=(1, 1, 1, 0.8),
        size=16,
        max_width=None,
    ):
        font_id = 0
        blf.size(font_id, size)
        if max_width:
            text_width, _ = blf.dimensions(font_id, text)
            if text_width > max_width:
                fitted_size = max(9, int(size * max_width / text_width))
                blf.size(font_id, fitted_size)
        blf.color(font_id, *color)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, text)

    def modal(self, context, event):
        runtime = get_adjust_runtime(context)
        if runtime is None or not runtime.running:
            self._exit(context)
            return {'FINISHED'}

        if not self._target_is_valid(context):
            return self._stop_for_target_change(context)

        if runtime.reset_requested:
            runtime.reset_requested = False
            self._rebase_after_external_reset(context)

        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._exit(context)
            return {'FINISHED'}

        if event.type in {'LEFTMOUSE', 'MOUSEMOVE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and self._is_view3d_ui_at_mouse(context, event.mouse_x, event.mouse_y):
            if self.action and event.type == 'LEFTMOUSE':
                if self.action_source == 'MOUSE' and event.value == 'RELEASE':
                    self._finish_action(context, commit=True)
                elif event.value == 'PRESS':
                    self._cancel_action(context)
            return {'PASS_THROUGH'}

        if event.type == 'MIDDLEMOUSE':
            self._is_navigating = event.value != 'RELEASE'
            self._tag_all_viewports(context)
            return {'PASS_THROUGH'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'NDOF_MOTION'}:
            self._tag_all_viewports(context)
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE' and self._is_navigating:
            self._tag_all_viewports(context)
            return {'PASS_THROUGH'}

        if event.type == 'Z' and event.ctrl and event.value == 'PRESS':
            if self.action:
                self._cancel_action(context)
            else:
                self._undo_last_action(context)
            return {'RUNNING_MODAL'}

        if self.action and (event.shift != self.last_shift or event.ctrl != self.last_ctrl):
            self._reset_start(event, context)

        if event.value == 'PRESS':
            if event.type == 'G':
                self._start_action('MOVE', event, context)
                return {'RUNNING_MODAL'}
            if event.type == 'S':
                self._start_action('SCALE', event, context)
                return {'RUNNING_MODAL'}
            if event.type == 'R':
                self._start_action('ROTATE', event, context)
                return {'RUNNING_MODAL'}

        if self.action == 'MOVE' and event.value == 'PRESS':
            if event.type == 'X':
                self.axis_lock = 'X' if self.axis_lock != 'X' else None
                self._reset_start(event, context)
                self._tag_all_viewports(context)
                return {'RUNNING_MODAL'}
            elif event.type == 'Y':
                self.axis_lock = 'Y' if self.axis_lock != 'Y' else None
                self._reset_start(event, context)
                self._tag_all_viewports(context)
                return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE':
            if self.action_source == 'MOUSE' and event.value == 'RELEASE':
                self._finish_action(context, commit=True)
                return {'RUNNING_MODAL'}
            if self.action and self.action_source == 'KEYBOARD' and event.value == 'PRESS':
                self._finish_action(context, commit=True)
                return {'RUNNING_MODAL'}
            if not self.action and event.value == 'PRESS' and self._is_view3d_window_at_mouse(context, event.mouse_x, event.mouse_y):
                self._start_action('MOVE', event, context, source='MOUSE')
                return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE' and self.action:
            self._apply_transform(event)
            self._tag_all_viewports(context)
            return {'RUNNING_MODAL'}

        # Keep the 3D View dedicated to reference-image adjustment while this modal tool is active.
        if self._is_view3d_window_at_mouse(context, event.mouse_x, event.mouse_y):
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def _reset_start(self, event, context):
        self.start_mx = event.mouse_x
        self.start_my = event.mouse_y
        self.start_offset = (self.bg.offset[0], self.bg.offset[1])
        self.start_scale = self.bg.scale
        self.start_rotation = self.bg.rotation
        self.last_shift = event.shift
        self.last_ctrl = event.ctrl
        # Store the new drag start and recalibrate the movement scale.
        self._calibrate_px_to_offset(context, event)
        center_x, center_y = self._transform_center
        center_dx = self.start_mx - center_x
        center_dy = self.start_my - center_y
        self._start_mouse_distance = max(math.hypot(center_dx, center_dy), 1.0)
        self._start_mouse_angle = math.atan2(center_dy, center_dx)

    def _apply_transform(self, event):
        mult = 0.1 if event.shift else 1.0
        mouse_dx = event.mouse_x - self.start_mx
        mouse_dy = event.mouse_y - self.start_my

        if self.action == 'MOVE':
            vx = mouse_dx * self._px_to_offset_x * mult if self.axis_lock != 'Y' else 0.0
            vy = mouse_dy * self._px_to_offset_y * mult if self.axis_lock != 'X' else 0.0
            nx = self.start_offset[0] + vx
            ny = self.start_offset[1] + vy
            if event.ctrl:
                nx = round(nx * 10) / 10
                ny = round(ny * 10) / 10
            self.bg.offset[0] = nx
            self.bg.offset[1] = ny

        elif self.action == 'SCALE':
            center_x, center_y = self._transform_center
            distance = math.hypot(event.mouse_x - center_x, event.mouse_y - center_y)
            ratio = distance / self._start_mouse_distance
            ratio = 1.0 + (ratio - 1.0) * mult
            ns = max(0.001, self.start_scale * ratio)
            if event.ctrl:
                ns = max(0.1, round(ns * 10) / 10)
            self.bg.scale = ns

        elif self.action == 'ROTATE':
            center_x, center_y = self._transform_center
            angle = math.atan2(event.mouse_y - center_y, event.mouse_x - center_x)
            angle_delta = math.atan2(
                math.sin(angle - self._start_mouse_angle),
                math.cos(angle - self._start_mouse_angle),
            )
            rotation = self.start_rotation - angle_delta * mult
            if event.ctrl:
                snap = math.radians(5.0)
                rotation = round(rotation / snap) * snap
            self.bg.rotation = rotation


CLASSES = (
    VIEW3D_OT_yl_cameraref_adjust_reference,
)
