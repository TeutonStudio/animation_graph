# animation_graph/Nodes/group_nodes.py

import bpy
from bpy.types import NodeGroupInput, NodeGroupOutput
from collections import Counter

from .Mixin import AnimGraphNodeMixin


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
        if self.node_tree: ensure_group_io_nodes(self.node_tree)
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
        sub = self.node_tree

        if not sub or getattr(sub, "bl_idname", None) != "AnimNodeTree":
            self.inputs.clear()
            self.outputs.clear()
            return

        # bpy.data.node_groups.get(self.node_tree.name) == self.node_tree (sollte)
        # self.node_tree.name == self.name ??

        iface_inputs = _iter_interface_sockets(sub, want_in_out="INPUT")
        iface_outputs = _iter_interface_sockets(sub, want_in_out="OUTPUT")

        _sync_node_sockets(self.inputs, iface_inputs)
        _sync_node_sockets(self.outputs, iface_outputs)


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

def add_node(tree: bpy.types.NodeTree, node_type: str):
    ctx = bpy.context

    win = ctx.window
    if not win: return False

    scr = win.screen
    if not scr: return False

    for area in scr.areas:
        if area.type != 'NODE_EDITOR': continue

        space = area.spaces.active
        if not space or space.type != 'NODE_EDITOR': continue

        # ganz wichtig: wir müssen den NodeTree setzen, in den wir einfügen wollen
        prev_tree = space.node_tree
        space.node_tree = tree

        try:
            for region in area.regions:
                if region.type != 'WINDOW': continue

                with ctx.temp_override(window=win, screen=scr, area=area, region=region, space_data=space):
                    bpy.ops.node.add_node(type=node_type, use_transform=False)
                return True
        finally:
            # restore, sonst “leakst” du UI state
            space.node_tree = prev_tree

    return False

def ensure_group_io_nodes(subtree: bpy.types.NodeTree):
    if not subtree or getattr(subtree, "bl_idname", None) != "AnimNodeTree":
        return

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
        before = {n.as_pointer() for n in subtree.nodes}
        add_node(subtree, "NodeGroupInput")
        after = [n for n in subtree.nodes if n.as_pointer() not in before]
        # pick the created one (fallback: first GROUP_INPUT)
        n_in = next((n for n in after if getattr(n, "type", None) == "GROUP_INPUT"), None) or find_group_input()

    # 2) ensure output
    n_out = find_group_output()
    if n_out is None:
        before = {n.as_pointer() for n in subtree.nodes}
        add_node(subtree, "NodeGroupOutput")
        after = [n for n in subtree.nodes if n.as_pointer() not in before]
        n_out = next((n for n in after if getattr(n, "type", None) == "GROUP_OUTPUT"), None) or find_group_output()

    # 3) position them sensibly
    if n_in is not None: n_in.location = (-300.0, 0.0)
    if n_out is not None: n_out.location = (300.0, 0.0)

# TODO evaluation reparieren
