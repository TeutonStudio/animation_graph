# animation_graph/UI/group_operator.py

import bpy
from bpy.types import Operator
from bpy.props import StringProperty


from ..Nodes.group_nodes import AnimGroupNode, ensure_group_io_nodes
from ..Core.node_tree import AnimNodeTree

def register():
    for c in _CLASSES: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)


def _get_space_node_editor(context):
    space = context.space_data
    return space if isinstance(space, bpy.types.SpaceNodeEditor) else None


def _find_node_by_name(tree, name):
    if not tree or not name:
        return None
    return tree.nodes.get(name)


def _tree_in_path(path, tree):
    return any(p.node_tree == tree for p in path)



def _sock_key(sock):
    """Stabiler Schlüssel: bevorzugt identifier, sonst name."""
    return getattr(sock, "identifier", None) or sock.name


def _interface_new_socket(tree, name, in_out, socket_type):
    # Blender 4+ / 5: tree.interface.new_socket(...)
    return tree.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)


def _interface_update(tree, context):
    # Blender kann da zickig sein je nach Version/Build.
    if hasattr(tree, "interface_update"):
        try:
            tree.interface_update(context)
            return
        except TypeError:
            tree.interface_update()
            return
    # Fallback: nichts, viele Builds aktualisieren trotzdem lazy.


# class ANIMGRAPH_OT_group_make(Operator):
#     bl_idname = "animgraph.group_make"
#     bl_label = "Gruppe erstellen"
#     bl_options = {'REGISTER', 'UNDO'}

#     group_name: bpy.props.StringProperty(name="Name", default="AnimGraphGroup")

#     @classmethod
#     def poll(cls, context):
#         space = context.space_data
#         if not space or space.type != 'NODE_EDITOR':
#             return False
#         tree = getattr(space, "edit_tree", None)
#         if not tree or getattr(tree, "bl_idname", None) != AnimNodeTree.bl_idname:
#             return False
#         # Mindestens ein selektierter Node (und nicht nur "leere" Auswahl)
#         return any(getattr(n, "select", False) for n in tree.nodes)

#     def execute(self, context):
#         space = context.space_data
#         src_tree = space.edit_tree

#         selected = [n for n in src_tree.nodes if n.select]
#         if not selected:
#             return {'CANCELLED'}

#         # Optional: Deine Group-IO Nodes nicht gruppieren (sonst baust du Chaos)
#         blocked = {"ANIMGRAPH_GroupInput", "ANIMGRAPH_GroupOutput"}
#         selected = [n for n in selected if n.bl_idname not in blocked]
#         if not selected:
#             self.report({'WARNING'}, "Keine gültigen Nodes für Gruppierung ausgewählt.")
#             return {'CANCELLED'}

#         # 1) Subtree erstellen
#         sub = bpy.data.node_groups.new(self.group_name, AnimNodeTree.bl_idname)
#         ensure_group_io_nodes(sub)

#         # IO Nodes im Subtree finden
#         gin = next((n for n in sub.nodes if n.bl_idname == "ANIMGRAPH_GroupInput"), None)
#         gout = next((n for n in sub.nodes if n.bl_idname == "ANIMGRAPH_GroupOutput"), None)
#         if not gin or not gout:
#             self.report({'ERROR'}, "Group IO Nodes konnten nicht erstellt werden.")
#             return {'CANCELLED'}

#         # 2) Nodes kopieren
#         node_map = {}
#         for n in selected:
#             nn = sub.nodes.new(n.bl_idname)
#             nn.location = n.location.copy()
#             nn.label = n.label
#             # Name-Kollisionen vermeiden: Blender macht sonst Stress
#             # nn.name = bpy.data.node_groups.new  # dummy to prevent accidental reuse? nope
#             node_map[n] = nn

#             # Wenn du Custom-Properties hast: hier explizit kopieren
#             # z.B. for k in n.keys(): nn[k] = n[k]

#         # 3) Interne Links kopieren (beide Enden selektiert)
#         for link in src_tree.links:
#             if link.from_node in node_map and link.to_node in node_map:
#                 fnode = node_map[link.from_node]
#                 tnode = node_map[link.to_node]

#                 fs_key = _sock_key(link.from_socket)
#                 ts_key = _sock_key(link.to_socket)

#                 fs = next((s for s in fnode.outputs if _sock_key(s) == fs_key), None)
#                 ts = next((s for s in tnode.inputs if _sock_key(s) == ts_key), None)
#                 if fs and ts:
#                     sub.links.new(fs, ts)

#         # 4) Boundary Links sammeln
#         incoming = []  # outside -> selected
#         outgoing = []  # selected -> outside
#         for link in list(src_tree.links):
#             a_sel = link.from_node in selected
#             b_sel = link.to_node in selected
#             if (not a_sel) and b_sel:
#                 incoming.append(link)
#             elif a_sel and (not b_sel):
#                 outgoing.append(link)

#         # 5) Interface-Sockets anlegen + im Subtree verkabeln
#         in_iface = {}   # (to_node, to_sock_key) -> iface socket
#         out_iface = {}  # (from_node, from_sock_key) -> iface socket

#         def ensure_iface_input(old_to_node, old_to_sock):
#             key = (old_to_node, _sock_key(old_to_sock))
#             if key in in_iface:
#                 return in_iface[key]
#             s = _interface_new_socket(
#                 sub,
#                 name=old_to_sock.name,
#                 in_out='INPUT',
#                 socket_type=old_to_sock.bl_idname,
#             )
#             in_iface[key] = s
#             return s

#         def ensure_iface_output(old_from_node, old_from_sock):
#             key = (old_from_node, _sock_key(old_from_sock))
#             if key in out_iface:
#                 return out_iface[key]
#             s = _interface_new_socket(
#                 sub,
#                 name=old_from_sock.name,
#                 in_out='OUTPUT',
#                 socket_type=old_from_sock.bl_idname,
#             )
#             out_iface[key] = s
#             return s

#         # 6) Group-Instanz im Source-Tree erstellen
#         gnode = src_tree.nodes.new(AnimGroupNode.bl_idname)
#         gnode.location = selected[0].location.copy()
#         gnode.node_tree = sub

#         ensure_group_io_nodes(sub)
#         _interface_update(sub, context)
#         # AnimGroupNode macht in update/init sein eigenes Socket-Sync, aber wir stoßen es an:
#         try:
#             gnode.sync_sockets_from_subtree()
#         except Exception:
#             pass

#         # Helfer: Sockets auf Instanz/IO-Nodes per Name finden
#         def find_inst_input(name):
#             return next((s for s in gnode.inputs if s.name == name), None)

#         def find_inst_output(name):
#             return next((s for s in gnode.outputs if s.name == name), None)

#         def find_gin_output(name):
#             return next((s for s in gin.outputs if s.name == name), None)

#         def find_gout_input(name):
#             return next((s for s in gout.inputs if s.name == name), None)

#         # 7) Incoming rewiring
#         for link in incoming:
#             old_from_sock = link.from_socket
#             old_to_node = link.to_node
#             old_to_sock = link.to_socket

#             iface_sock = ensure_iface_input(old_to_node, old_to_sock)
#             _interface_update(sub, context)
#             try:
#                 gnode.sync_sockets_from_subtree()
#             except Exception:
#                 pass

#             # Alte Verbindung entfernen
#             try:
#                 src_tree.links.remove(link)
#             except RuntimeError:
#                 pass

#             # outside -> group instance input
#             inst_in = find_inst_input(iface_sock.name)
#             if inst_in:
#                 src_tree.links.new(old_from_sock, inst_in)

#             # inside group: GroupInput output -> copied node input
#             gin_out = find_gin_output(iface_sock.name)
#             copied_to_node = node_map.get(old_to_node)
#             if gin_out and copied_to_node:
#                 tgt_in = next((s for s in copied_to_node.inputs if _sock_key(s) == _sock_key(old_to_sock)), None)
#                 if tgt_in:
#                     sub.links.new(gin_out, tgt_in)

#         # 8) Outgoing rewiring
#         for link in outgoing:
#             old_from_node = link.from_node
#             old_from_sock = link.from_socket
#             old_to_sock = link.to_socket

#             iface_sock = ensure_iface_output(old_from_node, old_from_sock)
#             _interface_update(sub, context)
#             try:
#                 gnode.sync_sockets_from_subtree()
#             except Exception:
#                 pass

#             # Alte Verbindung entfernen
#             try:
#                 src_tree.links.remove(link)
#             except RuntimeError:
#                 pass

#             # group instance output -> outside
#             inst_out = find_inst_output(iface_sock.name)
#             if inst_out:
#                 src_tree.links.new(inst_out, old_to_sock)

#             # inside group: copied node output -> GroupOutput input
#             copied_from = node_map.get(old_from_node)
#             gout_in = find_gout_input(iface_sock.name)
#             if copied_from and gout_in:
#                 src_out = next((s for s in copied_from.outputs if _sock_key(s) == _sock_key(old_from_sock)), None)
#                 if src_out:
#                     sub.links.new(src_out, gout_in)

#         # 9) Alte Nodes löschen
#         for n in selected:
#             try:
#                 src_tree.nodes.remove(n)
#             except RuntimeError:
#                 pass

#         # 10) Selektionszustand
#         for n in src_tree.nodes:
#             n.select = False
#         gnode.select = True
#         src_tree.nodes.active = gnode

#         return {'FINISHED'}


class ANIMGRAPH_OT_enter_group(Operator):
    """Enter AnimGraph group tree and update breadcrumbs."""
    bl_idname = "animgraph.enter_group"
    bl_label = "Enter AnimGraph Group"
    # bl_options = {'REGISTER', 'UNDO'}

    node_name: bpy.props.StringProperty()

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space: return {'CANCELLED'}

        tree = space.edit_tree  # aktuell editierter Tree (readonly)
        node = tree.nodes.get(self.node_name) if tree else None
        if not node or not getattr(node, "node_tree", None):
            return {'CANCELLED'}

        subgroup = node.node_tree

        # Root setzen, falls Path leer ist (oder inkonsistent)
        if len(space.path) == 0: space.path.start(tree)   # Root = aktueller Tree

        # In die Gruppe navigieren (Breadcrumb erzeugt)
        space.path.append(subgroup, node=node)

        # Editor auf Subtree schalten
        space.node_tree = subgroup

        return {'FINISHED'}


class ANIMGRAPH_OT_exit_group(Operator):
    """Exit to parent AnimGraph group."""
    bl_idname = "animgraph.exit_group"
    bl_label = "Exit AnimGraph Group"
    # bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space or len(space.path) == 0:
            return {'CANCELLED'}

        # Wenn wir nur Root haben: nichts zu poppen
        if len(space.path) == 1:
            return {'CANCELLED'}

        space.path.pop()

        # Letzten Tree als aktiven Edit-Tree setzen
        last = space.path[-1].node_tree
        space.node_tree = last
        return {'FINISHED'}

_CLASSES = [
    ANIMGRAPH_OT_enter_group,
    # ANIMGRAPH_OT_exit_group,
    # ANIMGRAPH_OT_group_make,
]
