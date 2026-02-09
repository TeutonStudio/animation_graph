# animation_graph/Core/node_tree.py

import bpy

def register(): 
    bpy.utils.register_class(AnimNodeTree)
    # global _ORIG_CONTEXT_DRAW
    # if _ORIG_CONTEXT_DRAW is None:
    #     _ORIG_CONTEXT_DRAW = bpy.types.NODE_MT_context_menu.draw
    # bpy.types.NODE_MT_context_menu.draw = animgraph_context_draw
def unregister(): 
    bpy.utils.unregister_class(AnimNodeTree)
    # global _ORIG_CONTEXT_DRAW
    # if _ORIG_CONTEXT_DRAW is not None:
    #     bpy.types.NODE_MT_context_menu.draw = _ORIG_CONTEXT_DRAW
    #     _ORIG_CONTEXT_DRAW = None

# _ORIG_CONTEXT_DRAW = None

# def animgraph_context_draw(self, context):
#     space = context.space_data
#     tree = getattr(space, "edit_tree", None)

#     # Nur unser Tree bekommt ein eigenes Menü
#     if tree and getattr(tree, "bl_idname", None) == AnimNodeTree.bl_idname:
#         layout = self.layout

#         # Ein paar Basisaktionen, damit das Menü nicht lächerlich leer ist
#         layout.operator("node.duplicate_move", text="Duplizieren")
#         layout.operator("node.delete", text="Löschen")
#         layout.separator()

#         # Hier ist der "ersetzte" Button:
#         layout.operator("animgraph.group_make", text="Gruppe erstellen", icon="NODETREE")
#         return

#     # Alles andere bleibt Blender-Standard
#     _ORIG_CONTEXT_DRAW(self, context)

def update_node(n: bpy.types.Node): pass

def update_link(l: bpy.types.NodeLinks): 
    fs = l.from_socket
    ts = l.to_socket
    if not fs or not ts: return

    def invalidLink(str,von = fs,nach = ts): return von.bl_idname == str and von.bl_idname != nach.bl_idname
    # Erlaubt ist NUR Bone -> Bone
    invalidBone = invalidLink("NodeSocketBone")
    if invalidBone:
        try: self.links.remove(l)
        except RuntimeError: pass

class AnimNodeTree(bpy.types.NodeTree):
    """AnimGraph node tree."""

    bl_idname = "ANIMGRAPH_Tree"
    bl_label = "Animation Node Editor"
    bl_icon = "ARMATURE_DATA"
    bl_use_group_interface = True
#    bl_description = "Wird verwendet um eine Amatur Pose abhängig vom Zeitpunkt zu definieren"

    def update(self):
        # Tree dirty markieren -> depsgraph handler bakes etc.
        self.dirty = True

        # RigInput Node-Ausgänge aktualisieren (optional)
        for n in getattr(self, "nodes", []): update_node(n)
        for l in getattr(self, "links", []): update_link(l)
