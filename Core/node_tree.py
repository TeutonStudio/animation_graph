# animation_graph/Core/node_tree.py

import bpy

def register(): bpy.utils.register_class(AnimNodeTree)
def unregister(): bpy.utils.unregister_class(AnimNodeTree)

validLinks = {
    "NodeSocketBone":[
        "NodeSocketBone"
    ],
    "NodeSocketInt":[
        "NodeSocketInt"
    ],
    "NodeSocketFloat":[
        "NodeSocketFloat",
        "NodeSocketInt",
    ],
    "NodeSocketVectorXYZ":[
        "NodeSocketVectorXYZ",
        "NodeSocketVector",
    ],
    "NodeSocketRotation":[
        "NodeSocketRotation",
        "NodeSocketVector",
    ],
    "NodeSocketVectorTranslation":[
        "NodeSocketVectorTranslation",
        "NodeSocketVector",
    ],
    "NodeSocketVector":[
        "NodeSocketVector",
        "NodeSocketVectorXYZ",
        "NodeSocketRotation",
        "NodeSocketVectorTranslation",
    ],
    "NodeSocketMatrix":[
        "NodeSocketMatrix",
    ],

}

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
        for n in getattr(self, "nodes", []): self.update_node(n)
        for l in getattr(self, "links", []): self.update_link(l)

    def update_node(self,n: bpy.types.Node): pass

    def update_link(self,l: bpy.types.NodeLink): 
        fs = l.from_socket
        ts = l.to_socket
        if not fs or not ts: return

        def validLink(str, von = fs,nach = ts):
            if von.bl_idname == nach.bl_idname: return True
            return von.bl_idname == str and nach.bl_idname in validLinks[str]
        valid = (
            validLink("NodeSocketBone") or
            validLink("NodeSocketInt") or
            validLink("NodeSocketFloat") or
            validLink("NodeSocketVectorXYZ") or
            validLink("NodeSocketRotation") or
            validLink("NodeSocketVectorTranslation") or
            validLink("NodeSocketVector") or
            validLink("NodeSocketMatrix") or
            False
        )

        if not valid:
            try: self.links.remove(l)
            except RuntimeError: pass
