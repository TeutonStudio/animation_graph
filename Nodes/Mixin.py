# animation_graph/Nodes/Mixin.py

import bpy
from mathutils import Vector, Matrix

class AnimGraphNodeMixin:
    """
    Evaluations-Mixin (single-link MVP, aber deterministisch):
    - Upstream Evaluation (einmal pro Frame)
    - Runtime-Value Propagation über ctx.values statt socket.default_value
    - Typed socket getter: int/float/vector/matrix
    """

    @classmethod
    def poll(cls, ntree):
        return hasattr(ntree, "nodes")

    # -----------------------------
    # internal helpers
    # -----------------------------
    def _scene_time_key(self, scene):
        # Include subframe to distinguish evaluation at the same integer frame.
        try:
            return round(float(getattr(scene, "frame_current_final")), 6)
        except Exception:
            try:
                base = float(getattr(scene, "frame_current", 0.0))
                sub = float(getattr(scene, "frame_subframe", 0.0))
                return round(base + sub, 6)
            except Exception:
                return 0.0

    def _frame_key(self, tree, scene):
        return (tree.as_pointer(), self._scene_time_key(scene))

    def _out_key(self, sock_name: str):
        # Schlüssel, unter dem Outputs im ctx.values landen
        return (self.as_pointer(), sock_name)

    def _ensure_ctx_runtime(self, ctx):
        # pro Frame neu: ctx.values; persistent: pose_cache etc.
        if not hasattr(ctx, "values") or ctx.values is None:
            ctx.values = {}
        if not hasattr(ctx, "eval_cache") or ctx.eval_cache is None:
            ctx.eval_cache = set()
        if not hasattr(ctx, "eval_stack") or ctx.eval_stack is None:
            ctx.eval_stack = set()

    def set_output_value(self, ctx, sock_name: str, value):
        self._ensure_ctx_runtime(ctx)
        ctx.values[self._out_key(sock_name)] = value

    def get_output_value(self, ctx, node_ptr: int, sock_name: str, fallback=None):
        self._ensure_ctx_runtime(ctx)
        return ctx.values.get((node_ptr, sock_name), fallback)

    # -----------------------------
    # evaluation plumbing
    # -----------------------------
    def eval_upstream(self, tree, scene, ctx):
        """
        Ensures this node is evaluated once per frame.
        ctx needs: ctx.eval_cache (set), ctx.values (dict)
        """
        self._ensure_ctx_runtime(ctx)

        frame_key = self._frame_key(tree, scene)
        key = (self.as_pointer(), frame_key)
        if key in ctx.eval_cache:
            return

        # Protect direct eval_upstream callers that bypass eval_socket guards.
        guard = ("UPSTREAM_EVAL", self.as_pointer(), frame_key)
        if guard in ctx.eval_stack:
            return
        ctx.eval_stack.add(guard)

        ctx.eval_cache.add(key)

        try:
            fn = getattr(self, "evaluate", None)
            if callable(fn):
                fn(tree, scene, ctx)
        finally:
            ctx.eval_stack.discard(guard)

    def eval_socket(self, tree, sock, scene, ctx):
        """
        Follow first link, evaluate upstream node, then read runtime output from ctx.values.
        Falls back to default_value only if unlinked.
        """
        self._ensure_ctx_runtime(ctx)

        if sock is None:
            return None

        if getattr(sock, "is_linked", False) and sock.links:
            link = sock.links[0]
            from_sock = link.from_socket
            from_node = from_sock.node

            # recursion guard (cycles kill determinism)
            guard = (tree.as_pointer(), from_node.as_pointer(), self._scene_time_key(scene))
            if guard in ctx.eval_stack:
                return getattr(from_sock, "default_value", None)  # last resort
            ctx.eval_stack.add(guard)
            try:
                if hasattr(from_node, "eval_upstream"):
                    from_node.eval_upstream(tree, scene, ctx)
                # Runtime-Wert lesen (nicht default_value!)
                return ctx.values.get((from_node.as_pointer(), from_sock.name),
                                      getattr(from_sock, "default_value", None))
            finally:
                ctx.eval_stack.discard(guard)

        # unlinked: UI default
        return getattr(sock, "default_value", None)

    # -----------------------------
    # typed socket helpers
    # -----------------------------
    def _in(self, name):
        return self.inputs.get(name) if self else None

    def socket_int(self, tree, name, scene, ctx, fallback=0):
        v = self.eval_socket(tree, self._in(name), scene, ctx)
        try:
            return int(v)
        except Exception:
            try:
                return int(float(v))
            except Exception:
                return int(fallback)

    def socket_float(self, tree, name, scene, ctx, fallback=0.0):
        v = self.eval_socket(tree, self._in(name), scene, ctx)
        try:
            return float(v)
        except Exception:
            return float(fallback)

    def socket_vector(self, tree, name, scene, ctx, fallback=(0.0, 0.0, 0.0)):
        v = self.eval_socket(tree, self._in(name), scene, ctx)
        try:
            return Vector(v)
        except Exception:
            return Vector(fallback)

    def socket_matrix(self, tree, name, scene, ctx, fallback=None):
        v = self.eval_socket(tree, self._in(name), scene, ctx)
        if v is None:
            return fallback
        try:
            return Matrix(v)
        except Exception:
            return fallback

    # -----------------------------
    # bone socket helpers (unverändert)
    # -----------------------------
    def socket_bone_ref(self, socket_name="Bone"):
        s = self.inputs.get(socket_name) if self else None
        if not s:
            return (None, "")

        if getattr(s, "is_linked", False) and s.links:
            from_sock = s.links[0].from_socket
            arm = getattr(from_sock, "armature_obj", None)
            bone = getattr(from_sock, "bone_name", "") or ""
            return (arm, bone)

        arm = getattr(s, "armature_obj", None)
        bone = getattr(s, "bone_name", "") or ""
        return (arm, bone)

    def socket_bone(self, socket_name="Bone", fallback=""):
        arm, bone = self.socket_bone_ref(socket_name)
        return bone or fallback
