# animation_graph/Nodes/helpers.py

import bpy
from bpy.types import NodeTree
from bpy.props import PointerProperty, EnumProperty, BoolProperty

class AnimGraphNodeMixin:
    @classmethod
    def poll(cls, ntree): return hasattr(ntree, "nodes")

# def _enum_bones_from_tree(self, context):
#     nt = getattr(self, "id_data", None)  # NodeTree, zu dem der Node gehört
#     ob = getattr(nt, "rig_object", None) if nt else None

#     if not ob or ob.type != "ARMATURE":
#         return [("", "<No Rig set>", "Set Rig in RigGraph Settings")]

#     bones = ob.data.bones
#     if not bones:
#         return [("", "<No Bones>", "Armature has no bones")]

#     return [(b.name, b.name, "") for b in bones]

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

def _sync_node_sockets(sock_list, iface_sockets):
    try:
        sock_list.clear()
    except Exception:
        return

    for s in iface_sockets:
        bl_socket_idname = getattr(s, "bl_socket_idname", None)
        name = getattr(s, "name", None)
        if bl_socket_idname and name:
            try: sock_list.new(bl_socket_idname, name)
            except Exception:
                pass

def _active_armature(context):
    ob = context.active_object
    if ob and ob.type == "ARMATURE":
        return ob.data
    return None
