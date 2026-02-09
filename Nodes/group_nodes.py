# animation_graph/Nodes/group_nodes.py

import bpy
from ..Core.node_tree import AnimNodeTree
from .Mixin import AnimGraphNodeMixin


def _sync_node_sockets(sock_list, iface_sockets):
    try: sock_list.clear()
    except Exception: return

    for s in iface_sockets:
        bl_socket_idname = getattr(s, "bl_socket_idname", None)
        name = getattr(s, "name", None)
        if bl_socket_idname and name:
            try: sock_list.new(bl_socket_idname, name)
            except Exception: pass

def _iter_interface_sockets(ntree, want_in_out=None):
    """
    Rekursiv Interface-Sockets aus ntree.interface.items_tree sammeln.
    want_in_out: "INPUT" | "OUTPUT" | None
    """
    iface = getattr(ntree, "interface", None)
    if iface is None:
        return []

    def walk(items):
        for it in items:
            # In Blender 4/5 sind das i.d.R. NodeTreeInterfaceSocket Items
            if it.__class__.__name__.endswith("Socket"):
                if want_in_out is None or getattr(it, "in_out", None) == want_in_out:
                    yield it
            child = getattr(it, "items", None)
            if child:
                yield from walk(child)

    try:
        return list(walk(iface.items_tree))
    except Exception:
        return []


class _GroupNode(bpy.types.NodeCustomGroup, AnimGraphNodeMixin):
    @classmethod
    def poll(cls, ntree): return getattr(ntree, "bl_idname", None) == AnimNodeTree.bl_idname


class AnimGroupNode(_GroupNode):
    """AnimGraph group instance node."""

    bl_idname = "ANIMGRAPH_Group"
    bl_label = "Group"
    bl_icon = "NODETREE"

    def init(self, context):
        if self.node_tree is None:
            self.node_tree = bpy.data.node_groups.new(
                name="AnimGraphGroup",
                type=AnimNodeTree.bl_idname,
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
        sub = self.node_tree

        if not sub or getattr(sub, "bl_idname", None) != AnimNodeTree.bl_idname:
            self.inputs.clear()
            self.outputs.clear()
            return

        iface_inputs = _iter_interface_sockets(sub, want_in_out="INPUT")
        iface_outputs = _iter_interface_sockets(sub, want_in_out="OUTPUT")

        _sync_node_sockets(self.inputs, iface_inputs)
        _sync_node_sockets(self.outputs, iface_outputs)


class _GroupSocketNode(_GroupNode):
    socket_1 = None
    socket_2 = None

    def init(self, context):
        self.sync_from_tree_interface()

    def update(self):
        self.sync_from_tree_interface()

    def sync_from_tree_interface(self):
        tree = self.id_data
        if not tree or getattr(tree, "bl_idname", None) != AnimNodeTree.bl_idname:
            return

        iface_sockets = _iter_interface_sockets(tree, want_in_out=self.socket_1)
        if not iface_sockets:
            return

        target_list = self.outputs if self.socket_2 == "OUTPUTS" else self.inputs
        _sync_node_sockets(target_list, iface_sockets)


class AnimGroupInputNode(_GroupSocketNode):
    """Group Input node (interface INPUT → node OUTPUTS)."""
    bl_idname = "ANIMGRAPH_GroupInput"
    bl_label = "Group Input"
    bl_icon = "IMPORT"

    socket_1 = "INPUT"
    socket_2 = "OUTPUTS"


class AnimGroupOutputNode(_GroupSocketNode):
    """Group Output node (interface OUTPUT → node INPUTS)."""
    bl_idname = "ANIMGRAPH_GroupOutput"
    bl_label = "Group Output"
    bl_icon = "EXPORT"

    socket_1 = "OUTPUT"
    socket_2 = "INPUTS"


def ensure_group_io_nodes(subtree):
    if not subtree or getattr(subtree, "bl_idname", None) != AnimNodeTree.bl_idname:
        return

    has_in = any(n.bl_idname == "ANIMGRAPH_GroupInput" for n in subtree.nodes)
    has_out = any(n.bl_idname == "ANIMGRAPH_GroupOutput" for n in subtree.nodes)

    if not has_in:
        n = subtree.nodes.new("ANIMGRAPH_GroupInput")
        n.location = (-300, 0)

    if not has_out:
        n = subtree.nodes.new("ANIMGRAPH_GroupOutput")
        n.location = (300, 0)
