# animation_graph/Core/node_tree.py

import bpy

def register(): bpy.utils.register_class(AnimNodeTree)
def unregister(): bpy.utils.unregister_class(AnimNodeTree)

def update_node(n: bpy.types.Node): pass

def update_link(l: bpy.types.NodeLink): 
    fs = l.from_socket
    ts = l.to_socket
    if not fs or not ts: return

    def invalidLink(str,von = fs,nach = ts): return von.bl_idname == str and von.bl_idname != nach.bl_idname

    invalid = (
        invalidLink("NodeSocketBone") or
        invalidLink("NodeSocketInt") or
        invalidLink("NodeSocketFloat") or
        invalidLink("NodeSocketVectorXYZ") or
        invalidLink("NodeSocketRotation") or
        invalidLink("NodeSocketTranslation") or
        invalidLink("NodeSocketMatrix")
    )

    if invalid:
        try:
            # tree muss rein, sonst gibt's kein self
            (tree or l.id_data).links.remove(l)
        except RuntimeError:
            pass

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

    def update(self):
        # Tree dirty markieren -> depsgraph handler bakes etc.
        self.dirty = True

        # RigInput Node-Ausgänge aktualisieren (optional)
        for n in getattr(self, "nodes", []): update_node(n)
        for l in getattr(self, "links", []): update_link(l)
