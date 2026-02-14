# animation_graph/Nodes/group_nodes.py

import bpy
from collections import Counter
from types import SimpleNamespace

from .Mixin import AnimGraphNodeMixin

_SOCKET_SYNC_GUARDS = set()
_ENSURE_IO_GUARDS = set()

class AnimNodeGroup(bpy.types.NodeCustomGroup, AnimGraphNodeMixin):
    """AnimGraph group instance node."""

    bl_idname = "AnimNodeGroup"
    bl_label = "Group"
    bl_icon = "NODETREE"

    @classmethod
    def poll(cls, ntree): return getattr(ntree, "bl_idname", None) == "AnimNodeTree"
    def init(self, context):
        if self.node_tree is None:
            self.node_tree = bpy.data.node_groups.new(
                name="AnimGraphGroup",
                type="AnimNodeTree",
            )

        ensure_group_io_nodes(self.node_tree)
        self.sync_sockets_from_subtree()

    def update(self):
        if self.node_tree:
            ensure_group_io_nodes(self.node_tree)
        self.sync_sockets_from_subtree()

    def draw_buttons(self, context, layout):
        layout.template_ID(self, "node_tree", new="node.new_node_tree")

        row = layout.row(align=True)
        op = row.operator(
            "animgraph.enter_group",
            text="Enter",
            icon="FULLSCREEN_ENTER",
        )
        op.node_name = self.name

    def sync_sockets_from_subtree(self):
        node_key = _guard_key(self)
        if node_key in _SOCKET_SYNC_GUARDS:
            return
        _SOCKET_SYNC_GUARDS.add(node_key)

        sub = self.node_tree
        try:
            if not sub or getattr(sub, "bl_idname", None) != "AnimNodeTree":
                self.inputs.clear()
                self.outputs.clear()
                return

            iface_inputs = _iter_interface_sockets(sub, want_in_out="INPUT")
            iface_outputs = _iter_interface_sockets(sub, want_in_out="OUTPUT")

            _sync_node_sockets(self.inputs, iface_inputs)
            _sync_node_sockets(self.outputs, iface_outputs)
        finally:
            _SOCKET_SYNC_GUARDS.discard(node_key)

    def evaluate(self, tree, scene, ctx):
        sub = self.node_tree
        if not sub or getattr(sub, "bl_idname", None) != "AnimNodeTree":
            return

        stack = getattr(ctx, "eval_stack", None)
        if stack is None:
            stack = set()
            ctx.eval_stack = stack

        frame_key = self._frame_key(tree, scene)

        # Guard against recursive group re-entry across nested sub-contexts.
        group_guard = ("GROUP_EVAL", self.as_pointer(), frame_key)
        if group_guard in stack:
            return
        stack.add(group_guard)

        try:
            # Evaluate group contents in an isolated runtime scope so multiple
            # instances of the same subtree do not share per-frame cache/values.
            sub_ctx = _make_sub_context(ctx)

            _push_group_inputs_to_subtree(
                group_node=self,
                parent_tree=tree,
                subtree=sub,
                scene=scene,
                parent_ctx=ctx,
                sub_ctx=sub_ctx,
            )

            # Tick side-effect transform nodes explicitly, like top-level tree eval.
            _evaluate_subtree_terminal_nodes(sub, scene, sub_ctx)

            _pull_group_outputs_from_subtree(
                group_node=self,
                subtree=sub,
                scene=scene,
                parent_ctx=ctx,
                sub_ctx=sub_ctx,
            )
        finally:
            stack.discard(group_guard)


def _evaluate_subtree_terminal_nodes(subtree, scene, sub_ctx):
    for node in getattr(subtree, "nodes", []):
        bl_idname = getattr(node, "bl_idname", "")
        if bl_idname not in {"DefineBoneTransform", "AnimNodeGroup"}:
            continue

        if hasattr(node, "eval_upstream"):
            try:
                node.eval_upstream(subtree, scene, sub_ctx)
            except Exception:
                pass
            continue

        fn = getattr(node, "evaluate", None)
        if callable(fn):
            try:
                fn(subtree, scene, sub_ctx)
            except Exception:
                pass

def _guard_key(rna):
    try:
        return int(rna.as_pointer())
    except Exception:
        return id(rna)



def _iter_interface_sockets(subtree, want_in_out):
    iface = getattr(subtree, "interface", None)
    if iface is None:
        return []

    sockets = []
    try:
        for item in iface.items_tree:
            if getattr(item, "item_type", None) != "SOCKET":
                continue
            if getattr(item, "in_out", None) != want_in_out:
                continue
            sockets.append(item)
    except Exception:
        return []
    return sockets


def _iface_socket_signature(iface_sock):
    name = getattr(iface_sock, "name", "") or ""
    socket_idname = (
        getattr(iface_sock, "bl_socket_idname", None)
        or getattr(iface_sock, "socket_type", None)
        or ""
    )
    if not name or not socket_idname:
        return None
    return (name, socket_idname)


def _node_socket_signature(sock):
    return (getattr(sock, "name", ""), getattr(sock, "bl_idname", ""))


def _sync_node_sockets(node_sockets, iface_sockets):
    desired = []
    for iface_sock in iface_sockets:
        sig = _iface_socket_signature(iface_sock)
        if sig is not None:
            desired.append(sig)

    current = [_node_socket_signature(sock) for sock in node_sockets]
    if current == desired:
        return

    # Remove only stale/mismatched sockets (including duplicates).
    keep_budget = Counter(desired)
    to_remove = []
    for sock in list(node_sockets):
        sig = _node_socket_signature(sock)
        if keep_budget.get(sig, 0) > 0:
            keep_budget[sig] -= 1
            continue
        to_remove.append(sock)

    for sock in to_remove:
        try:
            node_sockets.remove(sock)
        except Exception:
            pass

    # Create only the missing sockets.
    missing = Counter(desired)
    for sock in node_sockets:
        sig = _node_socket_signature(sock)
        if missing.get(sig, 0) > 0:
            missing[sig] -= 1

    for (name, socket_idname), count in missing.items():
        for _ in range(count):
            try:
                node_sockets.new(socket_idname, name)
            except Exception:
                pass

    # Reorder to match interface order without recreating.
    for target_idx, wanted_sig in enumerate(desired):
        found_idx = None
        for idx, sock in enumerate(node_sockets):
            if idx < target_idx:
                continue
            if _node_socket_signature(sock) == wanted_sig:
                found_idx = idx
                break
        if found_idx is None or found_idx == target_idx:
            continue
        try:
            node_sockets.move(found_idx, target_idx)
        except Exception:
            pass


def _make_sub_context(parent_ctx):
    pose_cache = getattr(parent_ctx, "pose_cache", None)
    if pose_cache is None:
        pose_cache = {}

    touched_armatures = getattr(parent_ctx, "touched_armatures", None)
    if touched_armatures is None:
        touched_armatures = set()

    eval_stack = getattr(parent_ctx, "eval_stack", None)
    if eval_stack is None:
        eval_stack = set()

    return SimpleNamespace(
        eval_cache=set(),
        pose_cache=pose_cache,
        touched_armatures=touched_armatures,
        values={},
        # Shared stack keeps recursion guards effective across nested groups.
        eval_stack=eval_stack,
    )


def _group_input_nodes(tree):
    return [n for n in getattr(tree, "nodes", []) if getattr(n, "type", "") == "GROUP_INPUT"]


def _active_group_output_node(tree):
    outputs = [n for n in getattr(tree, "nodes", []) if getattr(n, "type", "") == "GROUP_OUTPUT"]
    if not outputs:
        return None
    for node in outputs:
        if getattr(node, "is_active_output", False):
            return node
    return outputs[0]


def _is_bone_socket(sock):
    return getattr(sock, "bl_idname", "") == "NodeSocketBone"


def _read_bone_socket_value(tree, sock, scene, ctx):
    if sock is None:
        return (None, "")

    if getattr(sock, "is_linked", False) and sock.links:
        from_sock = sock.links[0].from_socket
        from_node = getattr(from_sock, "node", None)
        if from_node is not None and hasattr(from_node, "eval_upstream"):
            try:
                from_node.eval_upstream(tree, scene, ctx)
            except Exception:
                pass
        return (
            getattr(from_sock, "armature_obj", None),
            getattr(from_sock, "bone_name", "") or "",
        )

    return (
        getattr(sock, "armature_obj", None),
        getattr(sock, "bone_name", "") or "",
    )


def _write_bone_socket_value(sock, arm_obj, bone_name):
    if sock is None:
        return
    try:
        sock.armature_obj = arm_obj
    except Exception:
        pass
    try:
        sock.bone_name = bone_name or ""
    except Exception:
        pass


def _push_group_inputs_to_subtree(group_node, parent_tree, subtree, scene, parent_ctx, sub_ctx):
    input_nodes = _group_input_nodes(subtree)
    if not input_nodes:
        return

    for group_input in input_nodes:
        for idx, sub_out in enumerate(getattr(group_input, "outputs", [])):
            parent_in = group_node.inputs[idx] if idx < len(group_node.inputs) else None
            if parent_in is None:
                continue

            if _is_bone_socket(parent_in) or _is_bone_socket(sub_out):
                arm_obj, bone_name = _read_bone_socket_value(parent_tree, parent_in, scene, parent_ctx)
                _write_bone_socket_value(sub_out, arm_obj, bone_name)
                sub_ctx.values[(group_input.as_pointer(), sub_out.name)] = (arm_obj, bone_name)
                continue

            value = group_node.eval_socket(parent_tree, parent_in, scene, parent_ctx)
            if hasattr(sub_out, "default_value"):
                try:
                    sub_out.default_value = value
                except Exception:
                    pass
            sub_ctx.values[(group_input.as_pointer(), sub_out.name)] = value


def _pull_group_outputs_from_subtree(group_node, subtree, scene, parent_ctx, sub_ctx):
    group_output = _active_group_output_node(subtree)
    if group_output is None:
        return

    for idx, parent_out in enumerate(getattr(group_node, "outputs", [])):
        sub_in = group_output.inputs[idx] if idx < len(group_output.inputs) else None
        if sub_in is None:
            continue

        if _is_bone_socket(parent_out) or _is_bone_socket(sub_in):
            arm_obj, bone_name = _read_bone_socket_value(subtree, sub_in, scene, sub_ctx)
            _write_bone_socket_value(parent_out, arm_obj, bone_name)
            group_node.set_output_value(parent_ctx, parent_out.name, (arm_obj, bone_name))
            continue

        value = group_node.eval_socket(subtree, sub_in, scene, sub_ctx)
        if hasattr(parent_out, "default_value"):
            try:
                parent_out.default_value = value
            except Exception:
                pass
        group_node.set_output_value(parent_ctx, parent_out.name, value)

def ensure_group_io_nodes(subtree: bpy.types.NodeTree):
    if not subtree or getattr(subtree, "bl_idname", None) != "AnimNodeTree":
        return

    tree_key = _guard_key(subtree)
    if tree_key in _ENSURE_IO_GUARDS:
        return
    _ENSURE_IO_GUARDS.add(tree_key)

    try:
        # Helper: find existing
        def find_group_input():
            for n in subtree.nodes:
                if getattr(n, "type", None) == "GROUP_INPUT":
                    return n
            return None

        def find_group_output():
            for n in subtree.nodes:
                if getattr(n, "type", None) == "GROUP_OUTPUT":
                    return n
            return None

        # 1) ensure input
        n_in = find_group_input()
        if n_in is None:
            try:
                n_in = subtree.nodes.new("NodeGroupInput")
            except Exception:
                n_in = find_group_input()

        # 2) ensure output
        n_out = find_group_output()
        if n_out is None:
            try:
                n_out = subtree.nodes.new("NodeGroupOutput")
            except Exception:
                n_out = find_group_output()

        # 3) position them sensibly
        if n_in is not None:
            n_in.location = (-300.0, 0.0)
        if n_out is not None:
            n_out.location = (300.0, 0.0)
    finally:
        _ENSURE_IO_GUARDS.discard(tree_key)
