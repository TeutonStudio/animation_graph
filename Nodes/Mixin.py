# animation_graph/Nodes/Mixin.py

import bpy
from mathutils import Vector, Matrix

class AnimGraphNodeMixin:
    """
    Minimaler Evaluations-Mixin:
    - Upstream Evaluation (single-link MVP)
    - Typed socket getter: int/float/vector/matrix
    - Bone socket resolver (linked/unlinked)
    """

    @classmethod
    def poll(cls, ntree):
        return hasattr(ntree, "nodes")

    # -----------------------------
    # evaluation plumbing
    # -----------------------------
    def eval_upstream(self, tree, scene, ctx):
        """
        Ensures this node is evaluated once per frame.
        ctx needs: ctx.eval_cache (set)
        """
        key = (tree.as_pointer(), self.as_pointer(), float(scene.frame_current))
        if key in ctx.eval_cache:
            return
        ctx.eval_cache.add(key)

        fn = getattr(self, "evaluate", None)
        if callable(fn):
            fn(tree, scene, ctx)

    def eval_socket(self, tree, sock, scene, ctx):
        """
        Follow first link, evaluate upstream node, return default_value.
        """
        if sock is None:
            return None

        if getattr(sock, "is_linked", False) and sock.links:
            link = sock.links[0]
            from_sock = link.from_socket
            from_node = from_sock.node

            if hasattr(from_node, "eval_upstream"):
                from_node.eval_upstream(tree, scene, ctx)
            else:
                # Node without mixin, can't evaluate upstream
                pass

            return getattr(from_sock, "default_value", None)

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
    # bone socket helpers
    # -----------------------------
    def socket_bone_ref(self, socket_name="Bone"):
        """
        Returns (arm_obj, bone_name) from NodeSocketBone, linked or unlinked.
        """
        s = self.inputs.get(socket_name) if self else None
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

    def socket_bone(self, socket_name="Bone", fallback=""):
        arm, bone = self.socket_bone_ref(socket_name)
        return bone or fallback
