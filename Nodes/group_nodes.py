# animation_graph/Nodes/group_nodes.py

import bpy
from .Mixin import AnimGraphNodeMixin
from ..Core.node_tree import AnimNodeTree


def _sync_node_sockets(sock_list, iface_sockets): pass
# def _sync_node_sockets(sock_list, iface_sockets):
#     want = []
#     for s in iface_sockets:
#         socket_type = getattr(s, "socket_type", None) or getattr(s, "bl_socket_idname", None)
#         ident = getattr(s, "identifier", None) or getattr(s, "name", None)
#         name  = getattr(s, "name", None)
#         if socket_type and ident and name:
#             want.append((ident, socket_type, name))

#     # existing by name (NodeSocket identifier ist nicht sauber setzbar, daher meist über name matchen)
#     existing = {sock.name: sock for sock in sock_list}

#     # remove sockets not wanted (by name)
#     want_names = {name for (_, _, name) in want}
#     for sock in list(sock_list):
#         if sock.name not in want_names:
#             try:
#                 sock_list.remove(sock)
#             except Exception:
#                 pass

#     # add missing + ensure type
#     existing = {sock.name: sock for sock in sock_list}
#     for ident, socket_type, name in want:
#         sock = existing.get(name)
#         if sock is None:
#             try:
#                 sock_list.new(socket_type, name)
#             except Exception:
#                 pass
#         else:
#             # wenn Typ nicht passt: neu erzeugen
#             if getattr(sock, "bl_idname", None) != socket_type:
#                 try:
#                     sock_list.remove(sock)
#                     sock_list.new(socket_type, name)
#                 except Exception:
#                     pass


def _iter_interface_sockets(ntree, want_in_out=None):
    iface = getattr(ntree, "interface", None)
    if iface is None: return []

    def walk(items):
        for it in items:
            # Interface sockets haben in_out + socket_type
            if hasattr(it, "in_out") and hasattr(it, "socket_type"):
                if want_in_out is None or it.in_out == want_in_out:
                    yield it
            child = getattr(it, "items", None)
            if child:
                yield from walk(child)

    try: return list(walk(iface.items_tree))
    except Exception: return []


class AnimGroupNode(bpy.types.NodeCustomGroup, AnimGraphNodeMixin):
    """AnimGraph group instance node."""

    bl_idname = "ANIMGRAPH_Group"
    bl_label = "Group"
    bl_icon = "NODETREE"

    @classmethod
    def poll(cls, ntree): return getattr(ntree, "bl_idname", None) == AnimNodeTree.bl_idname
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


class _GroupSocketNode(bpy.types.Node, AnimGraphNodeMixin):
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

        target_list = self.outputs if self.socket_2 == "OUTPUTS" else self.inputs

        # WICHTIG: auch bei leer -> clear
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
    
    has_in = any(n.bl_idname == AnimGroupInputNode.bl_idname for n in subtree.nodes)
    has_out = any(n.bl_idname == AnimGroupOutputNode.bl_idname for n in subtree.nodes)

    if not has_in:
        n = subtree.nodes.new(AnimGroupInputNode.bl_idname)
        n.location = (-300, 0)

    if not has_out:
        n = subtree.nodes.new(AnimGroupOutputNode.bl_idname)
        n.location = (300, 0)
    
