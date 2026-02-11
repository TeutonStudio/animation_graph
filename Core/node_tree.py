# animation_graph/Core/node_tree.py

import bpy

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

    def update(self):
        # Tree dirty markieren -> depsgraph handler bakes etc.
        self.dirty = True

        # RigInput Node-Ausgänge aktualisieren (optional)
        for n in getattr(self, "nodes", []): self.update_node(n)
        for l in getattr(self, "links", []): self.update_link(l)

    def update_node(self,n: bpy.types.Node): pass

    def update_link(self,l: bpy.types.NodeLink): 
        if isValidLink(l):
            try: self.links.remove(l)
            except RuntimeError: pass

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
def isValidLink(l: bpy.types.NodeLink) -> bool:
    vn = l.from_socket.bl_idname
    zn = l.to_socket.bl_idname
    return zn in validLinks[vn] or vn == zn


