"""Shared helpers for the Aize 3D asset pipeline.

Runs inside Blender (4.5 LTS, headless):  blender -b --factory-startup -P <script> -- <args>
Cycles on the CPU only (deterministic, no GPU/GL needed), colours come from the design tokens so a token
change re-colours the 3D assets.  Conventions (identical for every asset, see assets3d/README.md):

  * world units are arbitrary "u"; +Z is up, +Y is "forward / up the screen at yaw 0", origin = point on the ground
  * yaw is measured CLOCKWISE seen from above, like a compass bearing relative to the camera's up-the-screen axis
  * camera pitch is measured from nadir (0 = top-down, 60 = looking towards the horizon) like MapLibre's `pitch`
  * the camera looks at the world origin, so the ground anchor of every sprite is the exact centre of the frame
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
TOKENS_PATH = os.path.join(REPO, "design", "tokens", "aize-purple.tokens.json")


# --------------------------------------------------------------------------------------- colour / tokens
def tokens():
    with open(TOKENS_PATH) as fh:
        return json.load(fh)


def _s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(h, mul=1.0, alpha=1.0):
    """'#RRGGBB' (sRGB) -> linear RGBA tuple for Blender colour sockets."""
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (_s2l(r) * mul, _s2l(g) * mul, _s2l(b) * mul, alpha)


def script_args():
    """Arguments after the lone '--' on the Blender command line."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


# --------------------------------------------------------------------------------------- scene / render
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def setup_render(res_x, res_y=None, samples=64, transparent=True, denoise=True, seed=0):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.seed = seed
    cy.use_animated_seed = False
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.01
    cy.adaptive_min_samples = 16
    cy.use_denoising = denoise
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except Exception:  # pragma: no cover - build without OIDN
        pass
    cy.max_bounces = 6
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 4
    cy.transmission_bounces = 2
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 4
    cy.sample_clamp_indirect = 4.0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    r = sc.render
    r.resolution_x = res_x
    r.resolution_y = res_y or res_x
    r.resolution_percentage = 100
    r.film_transparent = transparent
    r.filter_size = 1.5
    im = r.image_settings
    im.file_format = "PNG"
    im.color_mode = "RGBA"
    im.color_depth = "8"
    im.compression = 9
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.display_settings.display_device = "sRGB"
    return sc


def render_to(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# --------------------------------------------------------------------------------------- world / lights
def set_world_gradient(horizon_hex, zenith_hex, strength=0.6, ground_hex=None):
    """Vertical gradient environment: soft ambient light + something to reflect in glossy paint."""
    w = bpy.data.worlds.new("AizeWorld")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    maprng = nt.nodes.new("ShaderNodeMapRange")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], maprng.inputs["Value"])
    maprng.inputs["From Min"].default_value = -0.2
    maprng.inputs["From Max"].default_value = 1.0
    nt.links.new(maprng.outputs["Result"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = hex_rgba(ground_hex or horizon_hex)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = hex_rgba(zenith_hex)
    mid = ramp.color_ramp.elements.new(0.35)
    mid.color = hex_rgba(horizon_hex)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bpy.context.scene.world = w
    return w


def add_area_light(name, from_dir, energy, size, color=(1.0, 1.0, 1.0), dist=14.0, shape="SQUARE", shadow=True):
    """Area light placed `dist` away from the origin, in direction `from_dir` (vector pointing TOWARD the light)."""
    d = Vector(from_dir).normalized()
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    ld.shape = shape
    ld.color = color
    ld.use_shadow = shadow
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = d * dist
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return ob


# Rig parameters.  `key` shades the object (lateral, so facets separate clearly); `shadow_key` is where the key sits while the
# ground-shadow layer is rendered (more overhead -> a compact, natural contact shadow).  Overridable for experiments with
# AIZE_RIG='{"key":[x,y,z],"ambient":0.4,...}'.
RIG = {"key": [-0.95, 0.35, 1.0], "shadow_key": [-0.42, 0.40, 1.0], "key_energy": 1250.0, "ambient": 0.40, "fill": 260.0, "rim": 300.0}
RIG.update(json.loads(os.environ.get("AIZE_RIG", "{}")))
KEY_DIR = tuple(RIG["key"])


def aim_light(ob, direction, dist=14.0):
    d = Vector(direction).normalized()
    ob.location = d * dist
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


def key_for_shadow(on):
    """Move the key light to the shadow direction (on=True) or back to the shading direction."""
    k = bpy.data.objects.get("Key")
    if k is not None:
        aim_light(k, RIG["shadow_key"] if on else RIG["key"])


def studio_rig(scale=1.0):
    """UI-convention lighting: key from the upper-left so the ground shadow falls to the lower right; a soft camera-side
    fill and a rim light keep the camera-facing sides readable.  Only the key casts the ground shadow, so there is exactly
    one shadow direction across every Aize asset."""
    tk = tokens()["color"]
    set_world_gradient(horizon_hex=tk["neutral"]["100"], zenith_hex="#FFFFFF", ground_hex=tk["neutral"]["300"], strength=RIG["ambient"] * scale)
    add_area_light("Key", RIG["key"], RIG["key_energy"] * scale, 5.0, color=(1.0, 0.975, 0.95))
    add_area_light("Fill", (0.25, -1.0, 0.50), RIG["fill"] * scale, 7.0, color=(0.94, 0.95, 1.0), shadow=False)
    add_area_light("Rim", (0.85, 0.30, 0.40), RIG["rim"] * scale, 3.0, color=(1.0, 0.96, 1.0), shadow=False)


def add_ground_catcher(size=60.0):
    """Invisible ground that only receives the objects' shadows (RGBA: black with partial alpha)."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    me = bpy.data.meshes.new("Ground")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Ground", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.is_shadow_catcher = True
    return ob


def add_camera(pitch_deg, half_extent, dist_factor=28.0, anchor_y=0.5):
    """Near-orthographic perspective camera (long lens, like a billboard seen from MapLibre's far-away camera).
    The world origin is the exact centre of the frame; `half_extent` is the half-width of the frame at the origin."""
    th = math.radians(pitch_deg)
    dist = half_extent * dist_factor
    cam = bpy.data.cameras.new("Cam")
    cam.sensor_fit = "VERTICAL"
    cam.angle = 2.0 * math.atan(half_extent / dist)
    cam.shift_y = anchor_y - 0.5          # lens shift: puts the world origin at `anchor_y` of the frame height measured from the top
    cam.clip_start = dist * 0.05
    cam.clip_end = dist * 3.0
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0.0, -dist * math.sin(th), dist * math.cos(th))
    ob.rotation_euler = (th, 0.0, 0.0)
    bpy.context.scene.camera = ob
    return ob


def set_camera_pitch(cam_ob, pitch_deg):
    th = math.radians(pitch_deg)
    dist = cam_ob.location.length
    cam_ob.location = (0.0, -dist * math.sin(th), dist * math.cos(th))
    cam_ob.rotation_euler = (th, 0.0, 0.0)


# --------------------------------------------------------------------------------------- materials
def make_material(name, color_hex, rough=0.4, metal=0.0, coat=0.0, coat_rough=0.06, spec=0.5, emit_hex=None, emit_strength=0.0, mul=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]

    def put(socket, value):
        try:
            b.inputs[socket].default_value = value
        except KeyError:
            pass

    put("Base Color", hex_rgba(color_hex, mul))
    put("Roughness", rough)
    put("Metallic", metal)
    put("Coat Weight", coat)
    put("Coat Roughness", coat_rough)
    put("Specular IOR Level", spec)
    if emit_hex:
        put("Emission Color", hex_rgba(emit_hex))
        put("Emission Strength", emit_strength)
    return m


# --------------------------------------------------------------------------------------- mesh helpers
def mesh_object(name, bm, material=None, parent=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if material is not None:
        ob.data.materials.append(material)
    if parent is not None:
        ob.parent = parent
    return ob


def add_modifier(ob, kind, name=None, **props):
    m = ob.modifiers.new(name or kind.title(), kind)
    for k, v in props.items():
        setattr(m, k, v)
    return m


def bake_modifiers(ob):
    """Evaluate the modifier stack into plain mesh data (keeps materials)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def smooth_by_angle(ob, angle_deg=32.0):
    """Smooth shading, hard where the dihedral angle exceeds `angle_deg` (4.1+ semantics: sharp edges + smooth faces)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    lim = math.radians(angle_deg)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim)
    bm.to_mesh(ob.data)
    bm.free()


def empty(name, location=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = location
    return ob


# --------------------------------------------------------------------------------------- export
def export_glb(objects, path):
    """Binary glTF with baked modifiers and PBR materials (for an optional real-time path / design review)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )


def descendants(root):
    out = [root]
    for c in root.children:
        out += descendants(c)
    return out


def mesh_bounds(objects):
    """(min, max) world-space corners over the evaluated meshes (for framing)."""
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objects:
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            w = o.matrix_world @ v.co
            lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
        ev.to_mesh_clear()
    return lo, hi


def mesh_radius_height(objects):
    """(R, H): max horizontal distance from the world origin and max height over all evaluated vertices."""
    dg = bpy.context.evaluated_depsgraph_get()
    R = H = 0.0
    for o in objects:
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        for v in me.vertices:
            w = mw @ v.co
            R = max(R, math.hypot(w.x, w.y))
            H = max(H, w.z)
        ev.to_mesh_clear()
    return R, H


def frame_half_extent(R, H, shadow_margin=0.0):
    """Half-width (world units, at the origin plane) of a SQUARE frame, centred on the origin, that contains the object
    at every yaw and every pitch in [0, 60]: screen x = x' (|x'| <= R); screen y = y'*cos(p) + z*sin(p) whose maximum
    over p is sqrt(R^2 + H^2) when atan(H/R) <= 60 deg.  The shadow margin is added on top."""
    return math.sqrt(R * R + H * H) + shadow_margin


def shadow_pass(objects, ground, on):
    """on=True : objects become holdouts, ground is visible  -> render contains ONLY the ground shadow (alpha)
       on=False: objects visible, ground hidden               -> render contains ONLY the object (alpha-clean)"""
    for o in objects:
        o.is_holdout = bool(on)
    ground.hide_render = not on
