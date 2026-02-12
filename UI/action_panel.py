# animation_graph/UI/action_panel.py

import bpy

def register():
    for c in _CLASSES: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)

class ANIMGRAPH_PT_action_binding(bpy.types.Panel):
    bl_label = "AnimationNodes"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_category = "Action"

    @classmethod
    def poll(cls, context):
        obj = getattr(context, "object", None)
        ad = getattr(obj, "animation_data", None) if obj else None
        return bool(getattr(ad, "action", None))

    def draw(self, context):
        layout = self.layout
        obj = context.object
        action = obj.animation_data.action

        layout.label(text=f"Action: {action.name}")
        layout.template_ID(action, "animgraph_tree", new="node.new_node_tree")

_CLASSES = [
    ANIMGRAPH_PT_action_binding,
]
