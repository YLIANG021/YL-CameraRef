"""Create a camera while preserving the current viewport projection."""

import math
import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

from ... import i18n
from ...core.camera import sync_scene_camera_state


GEOMETRY_OBJECT_TYPES = {
    'MESH',
    'CURVE',
    'CURVES',
    'SURFACE',
    'META',
    'FONT',
    'VOLUME',
    'POINTCLOUD',
    'GREASEPENCIL',
}
CAMERA_FRAME_FILL = 0.9


def get_view_window_region(area):
    for region in area.regions:
        if region.type == 'WINDOW':
            return region
    return None


def get_render_aspect(scene):
    render = scene.render
    width = max(float(render.resolution_x) * float(render.pixel_aspect_x), 1.0)
    height = max(float(render.resolution_y) * float(render.pixel_aspect_y), 1.0)
    return width / height


def get_camera_sensor_fit(scene):
    return 'HORIZONTAL' if get_render_aspect(scene) >= 1.0 else 'VERTICAL'


def get_centered_camera_frame_size(region, scene):
    region_width = max(float(region.width), 1.0)
    region_height = max(float(region.height), 1.0)
    camera_aspect = get_render_aspect(scene)
    region_aspect = region_width / region_height

    if camera_aspect >= region_aspect:
        base_width = region_width
        base_height = region_width / camera_aspect
    else:
        base_height = region_height
        base_width = region_height * camera_aspect

    fit_factor = min(
        region_width / base_width,
        region_height / base_height,
    )
    zoom_factor = fit_factor * CAMERA_FRAME_FILL
    return base_width * zoom_factor, base_height * zoom_factor, zoom_factor


def camera_zoom_from_factor(zoom_factor):
    zoom = (math.sqrt(4.0 * max(float(zoom_factor), 1e-8)) - math.sqrt(2.0)) * 50.0
    return max(-30.0, min(zoom, 600.0))


def get_view_world_per_pixel(region, region_3d, depth_location, view_matrix):
    view_inverse = view_matrix.inverted()
    screen_origin = view3d_utils.location_3d_to_region_2d(
        region,
        region_3d,
        depth_location,
    )
    if screen_origin is None:
        raise ValueError(i18n.tr_report("Unable to measure the current viewport projection."))

    result = []
    for local_axis in (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0))):
        world_axis = view_inverse.to_quaternion() @ local_axis
        screen_axis = view3d_utils.location_3d_to_region_2d(
            region,
            region_3d,
            depth_location + world_axis,
        )
        if screen_axis is None:
            raise ValueError(i18n.tr_report("Unable to measure the current viewport projection."))
        pixels_per_world_unit = (screen_axis - screen_origin).length
        if pixels_per_world_unit <= 1e-8:
            raise ValueError(i18n.tr_report("The current viewport projection scale is invalid."))
        result.append(1.0 / pixels_per_world_unit)
    return result


def get_visible_geometry_depth_range(context, depth_location, camera_forward):
    depsgraph = context.evaluated_depsgraph_get()
    minimum_depth = None
    maximum_depth = None

    for source_object in context.visible_objects:
        if source_object.type not in GEOMETRY_OBJECT_TYPES:
            continue

        evaluated_object = source_object.evaluated_get(depsgraph)
        for corner in evaluated_object.bound_box:
            world_corner = evaluated_object.matrix_world @ Vector(corner)
            depth = (world_corner - depth_location).dot(camera_forward)
            minimum_depth = depth if minimum_depth is None else min(minimum_depth, depth)
            maximum_depth = depth if maximum_depth is None else max(maximum_depth, depth)

    if minimum_depth is None:
        return None
    return minimum_depth, maximum_depth


def position_orthographic_camera(
    context,
    region_3d,
    space,
    camera_matrix,
    camera_data,
    depth_location,
    camera_forward,
):
    clip_start = max(float(space.clip_start), 1e-4)
    depth_range = get_visible_geometry_depth_range(
        context,
        depth_location,
        camera_forward,
    )

    if depth_range is None:
        margin = max(camera_data.ortho_scale * 0.02, clip_start * 2.0, 0.01)
        backoff = max(float(region_3d.view_distance), camera_data.ortho_scale * 2.0, margin)
        farthest_depth = backoff + margin
    else:
        minimum_depth, maximum_depth = depth_range
        depth_span = max(maximum_depth - minimum_depth, 0.0)
        margin = max(depth_span * 0.05, camera_data.ortho_scale * 0.02, clip_start * 2.0)
        backoff = max(float(region_3d.view_distance), -minimum_depth + margin, margin)
        farthest_depth = maximum_depth + backoff + margin

    current_backoff = (depth_location - camera_matrix.translation).dot(camera_forward)
    camera_matrix.translation -= camera_forward * (backoff - current_backoff)
    camera_data.clip_start = clip_start
    camera_data.clip_end = max(float(space.clip_end), farthest_depth, clip_start * 2.0)


class BG_OT_NewCameraFromView(bpy.types.Operator):
    bl_idname = "view3d.yl_cameraref_add_camera_from_view"
    bl_label = "Add Camera from View"
    bl_description = "Create a new camera matching the current 3D View"
    bl_translation_context = i18n.CONTEXT
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        is_available = (
            context.area is not None
            and context.area.type == 'VIEW_3D'
            and context.space_data is not None
            and getattr(context.space_data, "region_3d", None) is not None
            and get_view_window_region(context.area) is not None
        )
        if not is_available:
            cls.poll_message_set("Open a 3D View to create a camera from the current view")
        return is_available

    def execute(self, context):
        scene = context.scene
        rd = context.space_data.region_3d
        space = context.space_data
        window_region = get_view_window_region(context.area)
        previous_scene_camera = scene.camera
        previous_view_camera = getattr(space, "camera", None)
        previous_active_object = context.view_layer.objects.active
        previous_selected_objects = list(context.selected_objects)
        previous_view_perspective = rd.view_perspective
        previous_view_camera_zoom = rd.view_camera_zoom
        previous_view_camera_offset = rd.view_camera_offset[:]

        is_perspective = bool(rd.is_perspective)
        depth_location = rd.view_location.copy()
        view_matrix = rd.view_matrix.copy()
        view_inverse = view_matrix.inverted()
        camera_matrix = view_inverse.to_quaternion().to_matrix().to_4x4()
        camera_matrix.translation = view_inverse.translation
        world_per_pixel_x, world_per_pixel_y = get_view_world_per_pixel(
            window_region,
            rd,
            depth_location,
            view_matrix,
        )
        camera_frame_width, camera_frame_height, zoom_factor = get_centered_camera_frame_size(
            window_region,
            scene,
        )
        sensor_fit = get_camera_sensor_fit(scene)
        camera = None
        camera_data = None

        try:
            camera_data = bpy.data.cameras.new("Camera")
            camera_data.passepartout_alpha = 0.8
            camera = bpy.data.objects.new("Camera", camera_data)
            target_collection = getattr(context, "collection", None) or scene.collection
            target_collection.objects.link(camera)

            for selected_object in context.selected_objects:
                selected_object.select_set(False)
            camera.select_set(True)
            context.view_layer.objects.active = camera

            scene.camera = camera
            space.camera = camera

            if is_perspective:
                camera_data.type = 'PERSP'
                camera_data.sensor_fit = sensor_fit

                camera_position = camera_matrix.translation
                camera_forward = -(camera_matrix.to_3x3() @ Vector((0.0, 0.0, 1.0)))
                camera_forward.normalize()
                depth = abs((depth_location - camera_position).dot(camera_forward))
                if sensor_fit == 'HORIZONTAL':
                    frame_world_size = world_per_pixel_x * camera_frame_width
                    sensor_size = camera_data.sensor_width
                else:
                    frame_world_size = world_per_pixel_y * camera_frame_height
                    sensor_size = camera_data.sensor_height
                if depth > 1e-8 and frame_world_size > 1e-8:
                    field_of_view = 2.0 * math.atan(frame_world_size / (2.0 * depth))
                    camera_data.lens = sensor_size / (2.0 * math.tan(field_of_view * 0.5))
                else:
                    camera_data.lens = space.lens
            else:
                camera_data.type = 'ORTHO'
                # AUTO may choose different axes for the viewport and render.
                # Use one explicit axis for both viewplanes and scale to match it.
                camera_data.sensor_fit = sensor_fit
                frame_world_size = (
                    world_per_pixel_x * camera_frame_width
                    if sensor_fit == 'HORIZONTAL'
                    else world_per_pixel_y * camera_frame_height
                )
                camera_data.ortho_scale = max(
                    frame_world_size,
                    1e-6,
                )
                camera_forward = -(camera_matrix.to_3x3() @ Vector((0.0, 0.0, 1.0)))
                camera_forward.normalize()
                position_orthographic_camera(
                    context,
                    rd,
                    space,
                    camera_matrix,
                    camera_data,
                    depth_location,
                    camera_forward,
                )

            camera.matrix_world = camera_matrix

            if previous_view_perspective != 'CAMERA':
                smooth_view = context.preferences.view.smooth_view
                try:
                    context.preferences.view.smooth_view = 0
                    with context.temp_override(
                        window=context.window,
                        area=context.area,
                        region=window_region,
                        space_data=space,
                    ):
                        result = bpy.ops.view3d.view_camera()
                    if result != {'FINISHED'}:
                        raise RuntimeError(i18n.tr_report("Unable to enter the new camera view."))
                finally:
                    context.preferences.view.smooth_view = smooth_view

            rd.view_camera_zoom = camera_zoom_from_factor(zoom_factor)
            rd.view_camera_offset = (0.0, 0.0)
            sync_scene_camera_state(scene, context=context)
            context.view_layer.update()
            context.area.tag_redraw()
        except (RuntimeError, ValueError) as exc:
            space.camera = previous_view_camera
            scene.camera = previous_scene_camera
            rd.view_perspective = previous_view_perspective
            rd.view_camera_zoom = previous_view_camera_zoom
            rd.view_camera_offset = previous_view_camera_offset
            if camera is not None and camera.name in bpy.data.objects:
                bpy.data.objects.remove(camera, do_unlink=True)
            if camera_data is not None and camera_data.name in bpy.data.cameras:
                bpy.data.cameras.remove(camera_data)
            for selected_object in previous_selected_objects:
                if selected_object.name in context.view_layer.objects:
                    selected_object.select_set(True)
            if (
                previous_active_object is not None
                and previous_active_object.name in context.view_layer.objects
            ):
                context.view_layer.objects.active = previous_active_object
            self.report(
                {'WARNING'},
                i18n.tr_report("Failed to create camera from view: {error}", error=exc),
            )
            return {'CANCELLED'}

        self.report({'INFO'}, i18n.tr_report("Camera created from view."))
        return {'FINISHED'}


def draw_camera_from_view_menu(self, context):
    self.layout.operator(
        BG_OT_NewCameraFromView.bl_idname,
        text="Camera from View",
        text_ctxt=i18n.CONTEXT,
        icon='OUTLINER_OB_CAMERA',
    )


def get_camera_add_menu_type():
    return getattr(bpy.types, "VIEW3D_MT_camera_add", bpy.types.VIEW3D_MT_add)


def register_menu():
    get_camera_add_menu_type().append(draw_camera_from_view_menu)


def unregister_menu():
    try:
        get_camera_add_menu_type().remove(draw_camera_from_view_menu)
    except RuntimeError:
        pass


CLASSES = (
    BG_OT_NewCameraFromView,
)
