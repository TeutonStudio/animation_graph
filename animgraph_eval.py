# animation_graph/animgraph_eval.py

import bpy
from mathutils import Vector, Euler, Matrix, Quaternion
from bpy.app.handlers import persistent

from .Core.node_tree import AnimNodeTree

_RUNNING = False

# Cache: (tree_ptr, node_ptr, arm_obj_ptr, bone_name, start, duration) -> start_state
_CACHE = {}
_EVAL_CACHE = {}



# --------------------------------------------------------------------
# register / unregister
# --------------------------------------------------------------------

def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame_change)
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)

def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_on_frame_change)
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    _CACHE.clear()


# --------------------------------------------------------------------
# tiny socket helpers (MVP: follow single link, else default_value)
# --------------------------------------------------------------------

def _eval_socket(tree, sock, scene):
    if sock is None:
        return None

    if getattr(sock, "is_linked", False) and sock.links:
        link = sock.links[0]
        from_sock = link.from_socket
        from_node = from_sock.node

        _eval_node(tree, from_node, scene)  # <<< DAS fehlte komplett

        return getattr(from_sock, "default_value", None)

    return getattr(sock, "default_value", None)

def _eval_node(tree, node, scene):
    if node is None:
        return

    frame = float(scene.frame_current)
    key = (tree.as_pointer(), node.as_pointer(), frame)
    if _EVAL_CACHE.get(key):
        return
    _EVAL_CACHE[key] = True

    bl = getattr(node, "bl_idname", "")

    # ---- FloatMath
    if bl == "ANIMGRAPH_FloatMath":
        a = _socket_float(tree, node, "A", scene, 0.0)
        b = _socket_float(tree, node, "B", scene, 0.0)
        op = getattr(node, "operation", "ADD")

        r = 0.0
        try:
            if op == "ADD": r = a + b
            elif op == "SUBTRACT": r = a - b
            elif op == "MULTIPLY": r = a * b
            elif op == "DIVIDE": r = a / b if b != 0.0 else 0.0
            elif op == "POWER": r = a ** b
            elif op == "MINIMUM": r = min(a, b)
            elif op == "MAXIMUM": r = max(a, b)
        except Exception:
            r = 0.0

        out = node.outputs.get("Result")
        if out:
            out.default_value = float(r)
        return

    # ---- VectorMath
    if bl == "ANIMGRAPH_VectorMath":
        A = _socket_vector(tree, node, "A", scene, (0,0,0))
        B = _socket_vector(tree, node, "B", scene, (0,0,0))
        s = _socket_float(tree, node, "Scale", scene, 1.0)
        op = getattr(node, "operation", "ADD")

        out_v = node.outputs.get("Vector")
        out_f = node.outputs.get("Float")

        try:
            if op == "ADD":
                if out_v: out_v.default_value = (A + B)
            elif op == "SUBTRACT":
                if out_v: out_v.default_value = (A - B)
            elif op == "MULTIPLY":
                if out_v: out_v.default_value = Vector((A.x*B.x, A.y*B.y, A.z*B.z))
            elif op == "DOT":
                if out_f: out_f.default_value = float(A.dot(B))
            elif op == "CROSS":
                if out_v: out_v.default_value = A.cross(B)
            elif op == "SCALE":
                if out_v: out_v.default_value = (A * float(s))
            elif op == "LENGTH":
                if out_f: out_f.default_value = float(A.length)
            elif op == "NORMALIZE":
                if out_v: out_v.default_value = (A.normalized() if A.length > 0 else Vector((0,0,0)))
        except Exception:
            pass
        return

    # ---- CombineXYZ
    if bl == "ANIMGRAPH_CombineXYZ":
        x = _socket_float(tree, node, "X", scene, 0.0)
        y = _socket_float(tree, node, "Y", scene, 0.0)
        z = _socket_float(tree, node, "Z", scene, 0.0)
        out = node.outputs.get("Vector")
        if out:
            out.default_value = (float(x), float(y), float(z))
        return

    # ---- SeparateXYZ
    if bl == "ANIMGRAPH_SeparateXYZ":
        v = _socket_vector(tree, node, "Vector", scene, (0,0,0))
        ox = node.outputs.get("X"); oy = node.outputs.get("Y"); oz = node.outputs.get("Z")
        if ox: ox.default_value = float(v.x)
        if oy: oy.default_value = float(v.y)
        if oz: oz.default_value = float(v.z)
        return

    # ---- MatrixMultiply
    if bl == "ANIMGRAPH_MatrixMultiply":
        A = _socket_matrix(tree, node, "A", scene)
        B = _socket_matrix(tree, node, "B", scene)
        out = node.outputs.get("Result")
        if out and A is not None and B is not None:
            out.default_value = (A @ B)
        return

    # ---- ComposeMatrix / DecomposeMatrix (optional als nächstes)

def _socket_float(tree, node, name, scene, fallback=0.0):
    s = node.inputs.get(name) if node else None
    v = _eval_socket(tree, s, scene)
    try:
        return float(v)
    except Exception:
        return float(fallback)

def _socket_vector(tree, node, name, scene, fallback=(0,0,0)):
    s = node.inputs.get(name) if node else None
    v = _eval_socket(tree, s, scene)
    try:
        return Vector(v)
    except Exception:
        return Vector(fallback)

def _socket_matrix(tree, node, name, scene):
    s = node.inputs.get(name) if node else None
    v = _eval_socket(tree, s, scene)
    if v is None:
        return None
    try:
        return Matrix(v)
    except Exception:
        return None


# --------------------------------------------------------------------
# Bone socket extraction (NodeSocketBone: armature_obj + bone_name)
# --------------------------------------------------------------------

def _socket_bone_ref(node, socket_name="Bone"):
    """
    Returns (arm_obj, bone_name) from NodeSocketBone.
    Works for linked and unlinked sockets.
    """
    s = node.inputs.get(socket_name) if node else None
    if not s:
        return (None, "")

    # linked: take from source socket
    if getattr(s, "is_linked", False) and s.links:
        from_sock = s.links[0].from_socket
        arm = getattr(from_sock, "armature_obj", None)
        bone = getattr(from_sock, "bone_name", "") or ""
        return (arm, bone)

    # unlinked: take from the socket itself
    arm = getattr(s, "armature_obj", None)
    bone = getattr(s, "bone_name", "") or ""
    return (arm, bone)

def _socket_bone(node, socket_name="Bone", fallback=""):
    """
    Compatibility wrapper: returns only bone_name.
    """
    _arm, bone = _socket_bone_ref(node, socket_name)
    return bone or fallback


# --------------------------------------------------------------------
# interpolation
# --------------------------------------------------------------------

def _apply_easing(t, easing):
    if easing in {"AUTO", "EASE_IN_OUT"}:
        return t * t * (3.0 - 2.0 * t)  # smoothstep
    if easing == "EASE_IN":
        return t * t
    if easing == "EASE_OUT":
        u = 1.0 - t
        return 1.0 - (u * u)
    return t

def _interp_factor(t, interpolation, easing):
    if interpolation == "CONSTANT":
        return 1.0 if t >= 1.0 else 0.0
    if interpolation == "LINEAR":
        return t
    return _apply_easing(t, easing)


# --------------------------------------------------------------------
# pose capture / rotation mixing
# --------------------------------------------------------------------

def _capture_start_pose(pbone):
    rot_mode = pbone.rotation_mode
    if rot_mode == "QUATERNION":
        rot = pbone.rotation_quaternion.copy()
    else:
        rot = pbone.rotation_euler.copy()
    return {
        "loc": pbone.location.copy(),
        "scale": pbone.scale.copy(),
        "rot_mode": rot_mode,
        "rot": rot,
        "mat": pbone.matrix_basis.copy(),
    }

def _rotation_target_from_euler(state, rot_vec, mode):
    e = Euler((rot_vec.x, rot_vec.y, rot_vec.z), "XYZ")
    if state["rot_mode"] == "QUATERNION":
        dq = e.to_quaternion()
        return dq if mode == "TO" else (Quaternion(state["rot"]) @ dq)

    if mode == "TO":
        return e
    sr = state["rot"]
    return Euler((sr.x + e.x, sr.y + e.y, sr.z + e.z), sr.order)

def _mix_rotation(state, rot_target, f):
    if state["rot_mode"] == "QUATERNION":
        return Quaternion(state["rot"]).slerp(Quaternion(rot_target), f)

    sr = state["rot"]
    tr = rot_target
    return Euler((
        (1.0 - f) * sr.x + f * tr.x,
        (1.0 - f) * sr.y + f * tr.y,
        (1.0 - f) * sr.z + f * tr.z,
    ), sr.order)


# --------------------------------------------------------------------
# tree utilities
# --------------------------------------------------------------------

def _iter_animtrees():
    for ng in bpy.data.node_groups:
        if getattr(ng, "bl_idname", "") == AnimNodeTree.bl_idname:
            yield ng

def _find_nodes(tree, bl_idname):
    return [n for n in getattr(tree, "nodes", []) if getattr(n, "bl_idname", "") == bl_idname]

def _find_transform_nodes(tree):
    return _find_nodes(tree, "ANIMGRAPH_DefineBoneTransform")

def _cache_key(tree, node, arm_ob, bone_name, start, duration):
    return (tree.as_pointer(), node.as_pointer(), arm_ob.as_pointer(), bone_name, float(start), float(duration))


# --------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------

def _eval_read_nodes(tree, arm_ob):
    for rn in _find_nodes(tree, "ANIMGRAPH_ReadBoneTransform"):
        r_arm, r_bone = _socket_bone_ref(rn, "Bone")
        if not r_arm or r_arm.type != "ARMATURE" or not r_bone:
            continue
        if r_arm != arm_ob:
            continue

        rpb = r_arm.pose.bones.get(r_bone)
        if not rpb:
            continue

        out_len = rn.outputs.get("Length")
        if out_len:
            try:
                b = rpb.bone
                out_len.default_value = (b.tail_local - b.head_local).length
            except Exception:
                pass


def _apply_define_bone_transform(tree, node, scene):
    """
    Applies node result to pose, but does NOT call update_tag and does NOT touch _RUNNING.
    Returns affected armature object or None.
    """
    arm_ob, bone_name = _socket_bone_ref(node, "Bone")
    if not arm_ob or arm_ob.type != "ARMATURE" or not bone_name:
        return None

    pbone = arm_ob.pose.bones.get(bone_name)
    if not pbone:
        return None

    start = _socket_float(tree, node, "Start", scene, 0.0)
    duration = _socket_float(tree, node, "Duration", scene, 10.0)
    frame = float(scene.frame_current)

    # Node output "End" (UI)
    out_end = node.outputs.get("End")
    if out_end:
        try:
            out_end.default_value = float(start + max(0.0, duration))
        except Exception:
            pass

    # time -> factor
    if duration <= 0.0:
        t = 1.0 if frame >= start else 0.0
    else:
        t = (frame - start) / duration
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)

    f = _interp_factor(t, getattr(node, "interpolation", "BEZIER"), getattr(node, "easing", "AUTO"))

    # cache start pose
    key = _cache_key(tree, node, arm_ob, bone_name, start, duration)
    if frame < start:
        _CACHE.pop(key, None)
        return None

    state = _CACHE.get(key)
    if state is None:
        state = _capture_start_pose(pbone)
        _CACHE[key] = state

    rep = getattr(node, "representation", "COMPONENTS")
    mode = getattr(node, "apply_mode", "TO")

    # Update read nodes (MVP)
    _eval_read_nodes(tree, arm_ob)

    if rep == "MATRIX":
        m_in = _socket_matrix(tree, node, "Matrix", scene)
        if m_in is None:
            return arm_ob

        m_t = m_in if mode == "TO" else (state["mat"] @ m_in)
        loc_t, rot_t_q, scale_t = m_t.decompose()

        # start rot as quat
        if state["rot_mode"] == "QUATERNION":
            start_q = Quaternion(state["rot"])
        else:
            start_q = Euler(state["rot"]).to_quaternion()

        rot_q = start_q.slerp(rot_t_q, f)
        loc = state["loc"].lerp(loc_t, f)
        scale = state["scale"].lerp(scale_t, f)

        pbone.location = loc
        pbone.scale = scale
        pbone.rotation_mode = "QUATERNION"
        pbone.rotation_quaternion = rot_q
        return arm_ob

    # COMPONENTS
    pos = _socket_vector(tree, node, "Position", scene, (0, 0, 0))
    rot_e = _socket_vector(tree, node, "Rotation", scene, (0, 0, 0))
    scl = _socket_vector(tree, node, "Scale", scene, (1, 1, 1))

    if mode == "TO":
        loc_t = pos
        scale_t = scl
        rot_t = _rotation_target_from_euler(state, rot_e, mode="TO")
    else:
        loc_t = state["loc"] + pos
        scale_t = Vector((
            state["scale"].x * scl.x,
            state["scale"].y * scl.y,
            state["scale"].z * scl.z,
        ))
        rot_t = _rotation_target_from_euler(state, rot_e, mode="DELTA")

    loc = state["loc"].lerp(loc_t, f)
    scale = state["scale"].lerp(scale_t, f)
    rot = _mix_rotation(state, rot_t, f)

    pbone.location = loc
    pbone.scale = scale

    if state["rot_mode"] == "QUATERNION":
        pbone.rotation_mode = "QUATERNION"
        pbone.rotation_quaternion = rot
    else:
        pbone.rotation_mode = state["rot_mode"]
        pbone.rotation_euler = rot

    return arm_ob


def _evaluate_tree(tree, scene, touched_armatures):
    for n in _find_transform_nodes(tree):
        arm = _apply_define_bone_transform(tree, n, scene)
        if arm: touched_armatures.add(arm)



# --------------------------------------------------------------------
# handlers (file-wide)
# --------------------------------------------------------------------

@persistent
def _on_frame_change(scene, depsgraph):
    global _RUNNING
    if _RUNNING:
        return

    _RUNNING = True
    try:
        _EVAL_CACHE.clear()
        touched = set()

        for tree in _iter_animtrees():
            _evaluate_tree(tree, scene, touched)

        # Einmal pro Armature updaten, nicht pro Node
        for arm_ob in touched:
            arm_ob.update_tag(refresh={"DATA"})

    finally:
        _RUNNING = False



@persistent
def _on_depsgraph_update(scene, depsgraph):
    if _RUNNING:
        return

    for area in bpy.context.screen.areas:
        if area.type == 'NODE_EDITOR':
            space = area.spaces.active
            if space.edit_tree and space.edit_tree.bl_idname == "ANIMGRAPH_Tree":
                space.overlay.show_context_path = True
    for tree in _iter_animtrees():
        if getattr(tree, "dirty", False):
            tree.dirty = False

            # Optional redraw
            scr = bpy.context.screen
            if scr:
                for area in scr.areas:
                    if area.type == "VIEW_3D":
                        area.tag_redraw()
