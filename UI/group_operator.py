# animation_graph/UI/group_operator.py

import bpy
from bpy.types import Operator
from bpy.props import StringProperty


def register():
    for c in _CLASSES: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)


def _get_space_node_editor(context):
    space = context.space_data
    return space if isinstance(space, bpy.types.SpaceNodeEditor) else None

# TODO implementieren
class ANIMGRAPH_OT_make_group(Operator):
    bl_idname = "animgraph.make_group"
    bl_label = "Enter AnimGraph Group"

    # TODO Selektierte Nodes ermitteln
    # TODO Selektierte Nodes in neuen AnimNodeTree
    # TODO verbindungen von selektierten zu unselektierten Node als Ein- und AusgangsSocket des neuen AnimNodeTree definieren
    # TODO AnimNodeGroup mit neuem AnimNodeTree erstellen
    # TODO Verbindungen von unselektierten zu Selektierten Node an AnimNodeGroup verlegen


class ANIMGRAPH_OT_enter_group(Operator):
    """Enter AnimGraph group tree and update breadcrumbs."""
    bl_idname = "animgraph.enter_group"
    bl_label = "Enter AnimGraph Group"

    node_name: bpy.props.StringProperty()

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space: return {'CANCELLED'}

        tree = space.edit_tree  # aktuell editierter Tree (readonly)
        node = tree.nodes.get(self.node_name) if tree else None
        if not node or not getattr(node, "node_tree", None):
            return {'CANCELLED'}

        subgroup = node.node_tree

        if len(space.path) == 0: space.path.start(tree) 
        space.path.append(subgroup, node=node)
        space.node_tree = subgroup

        return {'FINISHED'}

# TODO implementieren 
class ANIMGRAPH_OT_exit_group(Operator):
    """Exit to parent AnimGraph group."""
    bl_idname = "animgraph.exit_group"
    bl_label = "Exit AnimGraph Group"
    # bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space or len(space.path) == 0:
            return {'CANCELLED'}

        # Wenn wir nur Root haben: nichts zu poppen
        if len(space.path) == 1:
            return {'CANCELLED'}

        space.path.pop()

        # Letzten Tree als aktiven Edit-Tree setzen
        last = space.path[-1].node_tree
        space.node_tree = last
        return {'FINISHED'}

_CLASSES = [
    ANIMGRAPH_OT_enter_group,
    # ANIMGRAPH_OT_exit_group,
]
