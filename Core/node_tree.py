# animation_graph/Core/node_tree.py

import bpy
from . import sockets

def register(): bpy.utils.register_class(AnimNodeTree)
def unregister(): bpy.utils.unregister_class(AnimNodeTree)

class AnimNodeTree(bpy.types.NodeTree):
    """AnimGraph node tree."""

    bl_idname = "ANIMGRAPH_Tree"
    bl_label = "Animation Node Editor"
    bl_icon = "ARMATURE_DATA"
    bl_description = "Wird verwendet um eine Amatur Pose abhängig vom Zeitpunkt zu definieren"
    bl_use_group_interface = True

    dirty: bpy.props.BoolProperty(
        name="Dirty",
        description="Internal flag set when the node tree changed and needs re-evaluation",
        default=False,
        options={"HIDDEN"},
    )

    def interface_update(self, context):
        # 1) IO-Nodes im *gleichen* Tree (das ist der Tree dessen Interface gerade geändert wurde)
        for n in getattr(self, "nodes", []):
            if n.bl_idname == AnimGroupInputNode.bl_idname:
                try: n.sync_from_tree_interface()
                except Exception: pass
            elif n.bl_idname == AnimGroupOutputNode.bl_idname:
                try: n.sync_from_tree_interface()
                except Exception: pass

        # 2) Alle Group-Instanzen in *anderen* Trees, die diese node_tree benutzen
        #    (sonst aktualisiert sich deine Group-Node im Parent-Tree nie)
        for parent in bpy.data.node_groups:
            if getattr(parent, "bl_idname", None) != AnimNodeTree.bl_idname:
                continue

            touched = False
            for node in parent.nodes:
                if node.bl_idname == AnimGroupNode.bl_idname and node.node_tree == self:
                    try:
                        node.sync_sockets_from_subtree()
                        touched = True
                    except Exception: pass

            if touched:
                try: parent.update_tag()   # UI/Depsgraph refresh
                except Exception: pass


    def update(self):
        # Tree dirty markieren -> depsgraph handler bakes etc.
        self.dirty = True

        # RigInput Node-Ausgänge aktualisieren (optional)
        for n in getattr(self, "nodes", []): self.update_node(n)
        for l in getattr(self, "links", []): self.update_link(l)

    def update_node(self,n: bpy.types.Node): pass

    def update_link(self,l: bpy.types.NodeLink): 
        if not sockets.isValidLink(l):
            try: self.links.remove(l)
            except RuntimeError: pass
