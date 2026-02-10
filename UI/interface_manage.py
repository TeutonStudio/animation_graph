#animation_graph/UI/interface_manage.py

import bpy
from ..Core.node_tree import AnimNodeTree
from ..Nodes.group_nodes import _iter_interface_sockets

_iface_cache = {}

def register():
    if _depsgraph_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_post)

def unregister():
    if _depsgraph_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_post)
    _iface_cache.clear()

def _iface_signature(tree: bpy.types.NodeTree):
    """Erzeuge eine stabile Signatur der Interface-Sockets (Input+Output)."""
    ins = _iter_interface_sockets(tree, want_in_out="INPUT")
    outs = _iter_interface_sockets(tree, want_in_out="OUTPUT")

    def pack(s):
        return (
            getattr(s, "in_out", None),
            getattr(s, "identifier", None) or getattr(s, "name", ""),
            getattr(s, "bl_socket_idname", None),
            getattr(s, "name", None),
        )

    return tuple(pack(s) for s in ins + outs)

def _sync_tree_nodes(tree: bpy.types.NodeTree):
    """Sync GroupInput/GroupOutput innerhalb des Subtrees."""
    for n in getattr(tree, "nodes", []):
        # Deine Node-Klassen: AnimGroupInputNode / AnimGroupOutputNode
        if getattr(n, "bl_idname", "") in {"ANIMGRAPH_GroupInput", "ANIMGRAPH_GroupOutput"}:
            try:
                n.sync_from_tree_interface()
            except Exception:
                pass

def _sync_group_instances_referencing(subtree: bpy.types.NodeTree):
    """Sync alle Group-Instanzen in allen AnimNodeTrees, die subtree referenzieren."""
    for host in bpy.data.node_groups:
        if getattr(host, "bl_idname", None) != AnimNodeTree.bl_idname:
            continue
        for n in getattr(host, "nodes", []):
            if getattr(n, "bl_idname", "") == "ANIMGRAPH_Group" and getattr(n, "node_tree", None) == subtree:
                try:
                    n.sync_sockets_from_subtree()
                except Exception:
                    pass

def _depsgraph_post(scene, depsgraph):
    # Prüfe alle AnimNodeTrees (deine Gruppen leben dort)
    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", None) != AnimNodeTree.bl_idname:
            continue

        sig = _iface_signature(tree)
        key = tree.as_pointer()

        if _iface_cache.get(key) != sig:
            _iface_cache[key] = sig

            # 1) IO Nodes im Tree selbst aktualisieren
            _sync_tree_nodes(tree)

            # 2) Instanz-Nodes in anderen Trees aktualisieren
            _sync_group_instances_referencing(tree)

            # Optional: Blender “anstoßen”, UI/Depsgraph zu refreshen
            try:
                tree.update_tag()
            except Exception:
                pass
