# animation_graph/Core/node_tree.py

import bpy

from . import sockets
from .helper_methoden import (
    _on_action_tree_changed,
    _poll_animgraph_tree,
    find_action_input_slot,
    initialize_action_tree_binding,
    interface_socket_identifier,
    interface_socket_type,
    iter_interface_sockets,
    socket_kind,
    sync_actions_for_tree,
)


def register(): 
    for c in _CLASSES: bpy.utils.register_class(c)
    bpy.types.Action.animgraph_tree = bpy.props.PointerProperty(
        name="Animation Graph",
        description="AnimGraph node tree used when this Action is active",
        type=AnimNodeTree,
        poll=_poll_animgraph_tree,
        update=_on_action_tree_changed,
    )
def unregister(): 
    if hasattr(bpy.types.Action, "animgraph_tree"):
        del bpy.types.Action.animgraph_tree
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)

class AnimNodeTree(bpy.types.NodeTree):
    """AnimGraph node tree."""

    bl_idname = "AnimNodeTree"
    bl_label = "Animation Node Editor"
    bl_icon = "ARMATURE_DATA"
    bl_description = "Wird verwendet um eine Amatur Pose abhängig vom Zeitpunkt zu definieren"
    bl_use_group_interface = True

    def update(self):
        # RigInput Node-Ausgänge aktualisieren (optional)
        for n in getattr(self, "nodes", []): self.update_node(n)
        for l in getattr(self, "links", []): self.update_link(l)
        try: sync_actions_for_tree(self)
        except Exception: pass

    def update_node(self,n: bpy.types.Node): pass

    def update_link(self,l: bpy.types.NodeLink): 
        try:
            is_valid = sockets.isValidLink(l)
        except Exception:
            is_valid = False
        if not is_valid:
            try: self.links.remove(l)
            except RuntimeError: pass

    def interface_update(self, context):
        # 1) IO-Nodes im *gleichen* Tree (das ist der Tree dessen Interface gerade geändert wurde)
        for n in getattr(self, "nodes", []):
            if n.bl_idname == "NodeGroupInput":
                try: n.sync_from_tree_interface()
                except Exception: pass
            elif n.bl_idname == "NodeGroupOutput":
                try: n.sync_from_tree_interface()
                except Exception: pass

        # 2) Alle Group-Instanzen in *anderen* Trees, die diese node_tree benutzen
        #    (sonst aktualisiert sich deine Group-Node im Parent-Tree nie)
        for parent in bpy.data.node_groups:
            if getattr(parent, "bl_idname", None) != "AnimNodeTree":
                continue

            touched = False
            for node in parent.nodes:
                if node.bl_idname == "AnimNodeGroup" and node.node_tree == self:
                    try:
                        node.sync_sockets_from_subtree()
                        touched = True
                    except Exception: pass

            if touched:
                try: parent.update_tag()   # UI/Depsgraph refresh
                except Exception: pass

        # 3) Action-Panel Inputs für alle Actions aktualisieren, die diesen Tree verwenden
        try: sync_actions_for_tree(self)
        except Exception: pass


_CLASSES = [
    AnimNodeTree,
    sockets.NodeSocketBone
]
