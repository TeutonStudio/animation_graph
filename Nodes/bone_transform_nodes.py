# animation_graph/Nodes/bone_transform_node.py

import bpy
from bpy.types import Node
from bpy.props import EnumProperty
from mathutils import Vector, Euler, Matrix, Quaternion

from .Mixin import AnimGraphNodeMixin


# -----------------------------
# small utilities (module-local)
# -----------------------------
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

def _on_node_prop_update(self, context):
    try:
        self.update()
    except Exception:
        pass

    try:
        nt = getattr(self, "id_data", None)
        if nt:
            nt.update_tag()
            # some node trees need this to refresh socket UI properly
            if hasattr(nt, "interface_update"):
                nt.interface_update(context)
    except Exception:
        pass

    # force redraw of node editor areas
    try:
        if context and context.window and context.window.screen:
            for area in context.window.screen.areas:
                if area.type == "NODE_EDITOR":
                    area.tag_redraw()
    except Exception:
        pass



# -----------------------------
# nodes
# -----------------------------
class _BoneTransform(Node, AnimGraphNodeMixin):
    bl_icon = "CON_TRANSFORM"

    # NOTE: Blender property update callbacks must be functions, not methods-by-name.
    # You had: update=update_representation, but that symbol doesn't exist at class creation time.
    # We keep it simple: no update callback here, subclasses call self.update() in their own update methods.

    representation: EnumProperty(
        name="Representation",
        items=[
            ("COMPONENTS", "Components", "Output Position/Rotation/Scale"),
            ("MATRIX", "Matrix", "Output Matrix"),
        ],
        default="COMPONENTS",
        update=_on_node_prop_update,
    )

    apply_mode: EnumProperty(
        name="Apply",
        items=[
            ("TO", "To (Absolute)", "Use absolute transform"),
            ("DELTA", "Delta", "Use delta relative to start"),
        ],
        default="TO",
        update=_on_node_prop_update,
    )

    def update_representation(self, context): pass # overridden
    def update_mode(self, context): pass # overridden
    def _update_transform_socket(self, sockets):
        use_matrix = (self.representation == "MATRIX")

        for name in ("Translation", "Rotation", "Scale"):
            if name in sockets:
                sockets[name].hide = use_matrix
        if "Matrix" in sockets:
            sockets["Matrix"].hide = not use_matrix

    def init(self, context):
        self.inputs.new("NodeSocketBone","Bone")
        s = self.inputs.new("NodeSocketInt", "Start")
        d = self.inputs.new("NodeSocketInt", "Duration")
        try:
            s.default_value = 0
            d.default_value = 10
        except Exception: pass

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "representation", text="")
        col.prop(self, "apply_mode", text="")


class DefineBoneTransform(_BoneTransform):
    bl_idname = "DefineBoneTransform"
    bl_label = "Transform Bone"

    interpolation: EnumProperty(
        name="Interpolation",
        items=[
            ("CONSTANT", "Constant", "Jump at end"),
            ("LINEAR", "Linear", "Linear transition"),
            ("BEZIER", "Bezier", "Smooth (with easing)"),
        ],
        default="BEZIER",
    )

    easing: EnumProperty(
        name="Easing",
        items=[
            ("AUTO", "Auto", "Default (Ease In/Out-ish)"),
            ("EASE_IN", "Ease In", "Slow start, then faster"),
            ("EASE_OUT", "Ease Out", "Fast start, then slower"),
            ("EASE_IN_OUT", "Ease In/Out", "Slow start & end"),
        ],
        default="AUTO",
    )

    def update_representation(self, context): self.update()
    def update_mode(self, context): self.update()

    def init(self, context):
        super().init(context)

        p = self.inputs.new("NodeSocketVectorTranslation", "Translation")
        r = self.inputs.new("NodeSocketRotation", "Rotation")
        sc = self.inputs.new("NodeSocketVectorXYZ", "Scale")
        try:
            p.default_value = (0.0, 0.0, 0.0)
            r.default_value = (0.0, 0.0, 0.0)
            sc.default_value = (1.0, 1.0, 1.0)
        except Exception:
            pass

        m = self.inputs.new("NodeSocketMatrix", "Matrix")
        try:
            m.default_value = (
                (1.0, 0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            )
        except Exception:
            pass

        self.outputs.new("NodeSocketInt", "End")
        self.update()

    def update(self):
        self._update_transform_socket({s.name: s for s in getattr(self, "inputs", [])})

    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)
        layout.separator()
        col = layout.column(align=True)
        col.prop(self, "interpolation")
        col.prop(self, "easing")

    def evaluate(self, tree, scene, ctx):
        arm_ob, bone_name = self.socket_bone_ref("Bone")
        if not arm_ob or arm_ob.type != "ARMATURE" or not bone_name:
            return

        pbone = arm_ob.pose.bones.get(bone_name)
        if not pbone:
            return

        # deterministisch: alles als int frames
        start = int(self.socket_int(tree, "Start", scene, ctx, 0))
        duration = int(self.socket_int(tree, "Duration", scene, ctx, 10))
        frame = int(scene.frame_current)

        end_value = start + max(0, duration)

        # UI output (optional)
        out_end = self.outputs.get("End")
        if out_end:
            try:
                out_end.default_value = int(end_value)
            except Exception:
                pass

        # RUNTIME output (das ist der eigentliche Fix)
        # Andere Nodes lesen diesen Wert aus ctx.values, nicht aus default_value.
        self.set_output_value(ctx, "End", int(end_value))

        cache_key = (
            tree.as_pointer(),
            self.as_pointer(),
            arm_ob.as_pointer(),
            bone_name,
            start,
            duration,
        )

        if frame < start:
            ctx.pose_cache.pop(cache_key, None)
            return

        # time -> [0..1]
        if duration <= 0:
            t = 1.0
        else:
            t = (frame - start) / float(duration)
            if t < 0.0: t = 0.0
            if t > 1.0: t = 1.0

        f = _interp_factor(t,
                           getattr(self, "interpolation", "BEZIER"),
                           getattr(self, "easing", "AUTO"))

        state = ctx.pose_cache.get(cache_key)
        if state is None:
            state = _capture_start_pose(pbone)
            ctx.pose_cache[cache_key] = state

        rep = getattr(self, "representation", "COMPONENTS")
        mode = getattr(self, "apply_mode", "TO")

        if rep == "MATRIX":
            m_in = self.socket_matrix(tree, "Matrix", scene, ctx, None)
            if m_in is None:
                ctx.touched_armatures.add(arm_ob)
                return

            m_t = m_in if mode == "TO" else (state["mat"] @ m_in)
            try:
                loc_t, rot_t_q, scale_t = m_t.decompose()
            except Exception:
                ctx.touched_armatures.add(arm_ob)
                return

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

            ctx.touched_armatures.add(arm_ob)
            return

        # COMPONENTS
        pos = self.socket_vector(tree, "Translation", scene, ctx, (0.0, 0.0, 0.0))
        rot_e = self.socket_vector(tree, "Rotation", scene, ctx, (0.0, 0.0, 0.0))
        scl = self.socket_vector(tree, "Scale", scene, ctx, (1.0, 1.0, 1.0))

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

        ctx.touched_armatures.add(arm_ob)


class ReadBoneTransform(_BoneTransform):
    bl_idname = "ReadBoneTransform"
    bl_label = "Bone Transform"

    def update_representation(self, context): self.update()
    def update_mode(self, context): self.update()
    def init(self, context):
        super().init(context)

        # Optional "End" input for DELTA UI (kept, even if we don't frame-sample).
        # self.inputs.new("NodeSocketInt", "End")

        # Outputs
        self.outputs.new("NodeSocketVectorTranslation", "Translation")
        self.outputs.new("NodeSocketRotation", "Rotation")
        self.outputs.new("NodeSocketVectorXYZ", "Scale")
        self.outputs.new("NodeSocketMatrix", "Matrix")
        self.outputs.new("NodeSocketFloat", "Length")

        self.update()

    def update(self):
        ins = {s.name: s for s in getattr(self, "inputs", [])}
        outs = {s.name: s for s in getattr(self, "outputs", [])}

        self._update_transform_socket(outs)

        use_delta = (getattr(self, "apply_mode", "TO") == "DELTA")
        if "Duration" in ins: ins["Duration"].hide = not use_delta

    def evaluate(self, tree, scene, ctx):
        arm_ob, bone_name = self.socket_bone_ref("Bone")
        if not arm_ob or arm_ob.type != "ARMATURE" or not bone_name: return

        pbone = arm_ob.pose.bones.get(bone_name)
        if not pbone: return

        # Bone length (rest bone)
        out_len = self.outputs.get("Length")
        if out_len:
            try:
                b = pbone.bone
                out_len.default_value = float((b.tail_local - b.head_local).length)
            except Exception: pass

        mode = getattr(self, "apply_mode", "TO")
        rep = getattr(self, "representation", "COMPONENTS")

        # Read current pose state
        cur_loc = pbone.location.copy()
        cur_scale = pbone.scale.copy()

        if pbone.rotation_mode == "QUATERNION": cur_rot_q = pbone.rotation_quaternion.copy()
        else: cur_rot_q = pbone.rotation_euler.to_quaternion()

        cur_mat = pbone.matrix_basis.copy()

        if mode == "DELTA":
            # Capture "start" pose once at/after Start (no frame-jumping)
            start = self.socket_int(tree, "Start", scene, ctx, int(scene.frame_current))
            frame = int(scene.frame_current)

            cache_key = (
                tree.as_pointer(),
                self.as_pointer(),
                arm_ob.as_pointer(),
                bone_name,
                int(start),
            )

            if frame < start:
                ctx.pose_cache.pop(cache_key, None)
                return

            state = ctx.pose_cache.get(cache_key)
            if state is None:
                state = _capture_start_pose(pbone)
                ctx.pose_cache[cache_key] = state

            # Translation delta
            cur_loc = cur_loc - state["loc"]

            # Scale delta (avoid div by 0)
            s0 = state["scale"]
            cur_scale = Vector((
                (cur_scale.x / s0.x) if abs(s0.x) > 1e-8 else 1.0,
                (cur_scale.y / s0.y) if abs(s0.y) > 1e-8 else 1.0,
                (cur_scale.z / s0.z) if abs(s0.z) > 1e-8 else 1.0,
            ))

            # Rotation delta: q_delta = q_start^-1 * q_cur
            if state["rot_mode"] == "QUATERNION": start_q = Quaternion(state["rot"])
            else: start_q = Euler(state["rot"]).to_quaternion()

            cur_rot_q = start_q.inverted() @ cur_rot_q

            # Matrix delta (approx): M_delta = M_start^-1 * M_cur
            try: cur_mat = state["mat"].inverted() @ cur_mat
            except Exception: pass

        # Write outputs
        if rep == "MATRIX":
            out_m = self.outputs.get("Matrix")
            if out_m: out_m.default_value = cur_mat
            return

        # COMPONENTS
        out_t = self.outputs.get("Translation")
        out_r = self.outputs.get("Rotation")
        out_s = self.outputs.get("Scale")

        if out_t: out_t.default_value = (cur_loc.x, cur_loc.y, cur_loc.z)

        if out_s: out_s.default_value = (cur_scale.x, cur_scale.y, cur_scale.z)

        if out_r:
            try:
                e = cur_rot_q.to_euler("XYZ")
                out_r.default_value = (e.x, e.y, e.z)
            except Exception:
                out_r.default_value = (0.0, 0.0, 0.0)
