#animation_graph/UI/interface_manage.py
import bpy
from ..Core.node_tree import AnimNodeTree
from ..Nodes.group_nodes import _iter_interface_sockets

_iface_cache = {}
_timer_running = False

def register():
    global _timer_running
    if not _timer_running:
        _timer_running = True
        bpy.app.timers.register(_timer_tick, persistent=True)

def unregister():
    global _timer_running
    _timer_running = False
    _iface_cache.clear()
    # Timer deregistriert sich selbst, weil _timer_tick None zurückgibt.

def _iface_signature(tree: bpy.types.NodeTree):
    ins = _iter_interface_sockets(tree, want_in_out="INPUT")
    outs = _iter_interface_sockets(tree, want_in_out="OUTPUT")

    def pack(s):
        return (
            getattr(s, "in_out", None),
            getattr(s, "identifier", None) or getattr(s, "name", ""),
            # HIER: socket_type, nicht bl_socket_idname
            getattr(s, "socket_type", None) or getattr(s, "bl_socket_idname", None),
            getattr(s, "name", None),
        )
    return tuple(pack(s) for s in ins + outs)


def _sync_tree_nodes(tree: bpy.types.NodeTree):
    for n in getattr(tree, "nodes", []):
        if getattr(n, "bl_idname", "") in {"ANIMGRAPH_GroupInput", "ANIMGRAPH_GroupOutput"}:
            try:
                n.sync_from_tree_interface()
            except Exception:
                pass

def _sync_group_instances_referencing(subtree: bpy.types.NodeTree):
    for host in bpy.data.node_groups:
        if getattr(host, "bl_idname", None) != AnimNodeTree.bl_idname:
            continue
        for n in getattr(host, "nodes", []):
            if getattr(n, "bl_idname", "") == "ANIMGRAPH_Group" and getattr(n, "node_tree", None) == subtree:
                try:
                    n.sync_sockets_from_subtree()
                except Exception:
                    pass

def _timer_tick():
    global _timer_running
    if not _timer_running:
        return None  # stop timer

    changed_any = False

    for tree in bpy.data.node_groups:
        if getattr(tree, "bl_idname", None) != AnimNodeTree.bl_idname:
            continue

        sig = _iface_signature(tree)
        key = tree.as_pointer()

        if _iface_cache.get(key) != sig:
            _iface_cache[key] = sig
            changed_any = True

            _sync_tree_nodes(tree)
            _sync_group_instances_referencing(tree)

            try:
                tree.update_tag()
            except Exception:
                pass

    # UI redraw anstoßen (sonst siehst du es manchmal erst nach Klickerei)
    if changed_any:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == "NODE_EDITOR":
                    area.tag_redraw()

    return 0.25  # alle 250ms prüfen
