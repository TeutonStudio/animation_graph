# animation_graph/Nodes/group_nodes.py

import bpy
from bpy.types import NodeGroupInput, NodeGroupOutput

from .Mixin import AnimGraphNodeMixin


def _sync_node_sockets(sock_list, iface_sockets):
    want = []
    for s in iface_sockets:
        socket_type = getattr(s, "socket_type", None) or getattr(s, "bl_socket_idname", None)
        ident = getattr(s, "identifier", None) or getattr(s, "name", None)
        name  = getattr(s, "name", None)
        if socket_type and ident and name:
            want.append((ident, socket_type, name))

    # existing by name (NodeSocket identifier ist nicht sauber setzbar, daher meist über name matchen)
    existing = {sock.name: sock for sock in sock_list}

    # remove sockets not wanted (by name)
    want_names = {name for (_, _, name) in want}
    for sock in list(sock_list):
        if sock.name not in want_names:
            try:
                sock_list.remove(sock)
            except Exception:
                pass

    # add missing + ensure type
    existing = {sock.name: sock for sock in sock_list}
    for ident, socket_type, name in want:
        sock = existing.get(name)
        if sock is None:
            try:
                sock_list.new(socket_type, name)
            except Exception:
                pass
        else:
            # wenn Typ nicht passt: neu erzeugen
            if getattr(sock, "bl_idname", None) != socket_type:
                try:
                    sock_list.remove(sock)
                    sock_list.new(socket_type, name)
                except Exception:
                    pass


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

        iface_inputs = []
        iface_outputs = []
        for i in self.node_tree.interface.items_tree:
            if i.item_type == 'SOCKET':
                liste = iface_inputs.append if i.in_out == 'INPUT' else iface_outputs.append
                liste(i)
        
        self.inputs.clear()
        self.outputs.clear()
        for i in iface_inputs: self.inputs.new(i.bl_socket_idname,i.name)
        for i in iface_outputs: self.outputs.new(i.bl_socket_idname,i.name)
        # iface_inputs = _iter_interface_sockets(sub, want_in_out="INPUT")
        # iface_outputs = _iter_interface_sockets(sub, want_in_out="OUTPUT")

        # _sync_node_sockets(self.inputs, iface_inputs)
        # _sync_node_sockets(self.outputs, iface_outputs)


# class _GroupSocketNode(bpy.types.Node, AnimGraphNodeMixin):
#     socket_1 = None
#     socket_2 = None

#     def init(self, context):
#         self.sync_from_tree_interface()

#     def update(self):
#         self.sync_from_tree_interface()

#     def sync_from_tree_interface(self):
#         tree = self.id_data
#         if not tree or getattr(tree, "bl_idname", None) != "AnimNodeTree":
#             return

#         iface_sockets = _iter_interface_sockets(tree, want_in_out=self.socket_1)

#         target_list = self.outputs if self.socket_2 == "OUTPUTS" else self.inputs

#         # WICHTIG: auch bei leer -> clear
#         _sync_node_sockets(target_list, iface_sockets)


# class AnimGroupInputNode(_GroupSocketNode, bpy.types.NodeGroupInput):
#     """Group Input node (interface INPUT → node OUTPUTS)."""
#     bl_idname = "ANIMGRAPH_GroupInput"
#     bl_label = "Group Input"
#     bl_icon = "IMPORT"

#     socket_1 = "INPUT"
#     socket_2 = "OUTPUTS"


# class AnimGroupOutputNode(_GroupSocketNode, bpy.types.NodeGroupOutput):
#     """Group Output node (interface OUTPUT → node INPUTS)."""
#     bl_idname = "ANIMGRAPH_GroupOutput"
#     bl_label = "Group Output"
#     bl_icon = "EXPORT"

#     socket_1 = "OUTPUT"
#     socket_2 = "INPUTS"


def add_node(tree: bpy.types.NodeTree, node_type: str):
    ctx = bpy.context

    win = ctx.window
    if not win:
        return False

    scr = win.screen
    if not scr:
        return False

    for area in scr.areas:
        if area.type != 'NODE_EDITOR':
            continue

        space = area.spaces.active
        if not space or space.type != 'NODE_EDITOR':
            continue

        # ganz wichtig: wir müssen den NodeTree setzen, in den wir einfügen wollen
        prev_tree = space.node_tree
        space.node_tree = tree

        try:
            for region in area.regions:
                if region.type != 'WINDOW':
                    continue

                with ctx.temp_override(window=win, screen=scr, area=area, region=region, space_data=space):
                    bpy.ops.node.add_node(type=node_type, use_transform=False)
                return True
        finally:
            # restore, sonst “leakst” du UI state
            space.node_tree = prev_tree

    return False



def ensure_group_io_nodes(subtree: bpy.types.NodeTree):
    if not subtree or getattr(subtree, "bl_idname", None) != "AnimNodeTree": return 

    has_in  = any(getattr(n, "type", None) == "GROUP_INPUT"  for n in subtree.nodes)
    has_out = any(getattr(n, "type", None) == "GROUP_OUTPUT" for n in subtree.nodes)

    if not has_in: add_node(subtree, "NodeGroupInput")
    if not has_out: add_node(subtree, "NodeGroupOutput")

