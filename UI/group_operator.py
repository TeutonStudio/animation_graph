# animation_graph/UI/group_operator.py

import bpy
from bpy.props import StringProperty
from bpy.types import Operator, NodeTree


_DEBUG_PATHS = False


def register():
    for c in _CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(_CLASSES):
        bpy.utils.unregister_class(c)


def _debug_log(*parts):
    if _DEBUG_PATHS:
        print("[animgraph:path]", *parts)


def _get_space_node_editor(context):
    space = getattr(context, "space_data", None)
    return space if isinstance(space, bpy.types.SpaceNodeEditor) else None


def _is_animgraph_tree(tree):
    return getattr(tree, "bl_idname", None) == "AnimNodeTree"


def _path_len(space):
    path = getattr(space, "path", None)
    return len(path) if path is not None else 0


def _path_tree(space, index):
    try:
        return getattr(space.path[index], "node_tree", None)
    except Exception:
        return None


def _current_tree_from_space(space):
    path = getattr(space, "path", None)
    if path and len(path):
        tail_tree = _path_tree(space, -1)
        if _is_animgraph_tree(tail_tree):
            return tail_tree

    edit_tree = getattr(space, "edit_tree", None)
    if _is_animgraph_tree(edit_tree):
        return edit_tree

    node_tree = getattr(space, "node_tree", None)
    if _is_animgraph_tree(node_tree):
        return node_tree

    return None


def _reset_path_to_root(space, tree):
    if not _is_animgraph_tree(tree):
        return None

    path = getattr(space, "path", None)
    if path is None:
        return None

    for _ in range(len(path)):
        try:
            path.pop()
        except Exception:
            break

    try:
        path.start(tree)
    except Exception:
        return None

    if getattr(space, "node_tree", None) is not tree:
        try:
            space.node_tree = tree
        except Exception:
            pass

    _debug_log("reset_root", getattr(tree, "name", None))
    return _current_tree_from_space(space)


def _ensure_root_path(space, tree):
    if not _is_animgraph_tree(tree):
        return None

    path = getattr(space, "path", None)
    if path is None:
        return None

    if len(path) == 0:
        current_tree = getattr(space, "edit_tree", None)
        if not _is_animgraph_tree(current_tree):
            current_tree = tree
        return _reset_path_to_root(space, current_tree)

    root_tree = _path_tree(space, 0)
    tail_tree = _path_tree(space, -1)
    edit_tree = getattr(space, "edit_tree", None)

    path_is_stale = (
        not _is_animgraph_tree(root_tree)
        or root_tree != tree
        or not _is_animgraph_tree(tail_tree)
        or (edit_tree is not None and not _is_animgraph_tree(edit_tree))
        or (_is_animgraph_tree(edit_tree) and edit_tree != tail_tree)
    )

    if path_is_stale:
        return _reset_path_to_root(space, tree)

    return tail_tree


def _append_tree_to_path(space, tree, node):
    if not _is_animgraph_tree(tree):
        return None

    try:
        space.path.append(tree, node=node)
    except Exception:
        return None

    current_tree = _current_tree_from_space(space)
    if current_tree == tree:
        return current_tree

    root_tree = _path_tree(space, 0)
    if _is_animgraph_tree(root_tree):
        _reset_path_to_root(space, root_tree)
    return None


def _pop_path(space):
    if _path_len(space) <= 1:
        return _current_tree_from_space(space)

    try:
        space.path.pop()
    except Exception:
        return None

    current_tree = _current_tree_from_space(space)
    tail_tree = _path_tree(space, -1)
    if current_tree == tail_tree and _is_animgraph_tree(tail_tree):
        return current_tree

    entries = []
    for item in getattr(space, "path", []):
        item_tree = getattr(item, "node_tree", None)
        if not _is_animgraph_tree(item_tree):
            continue
        entries.append((item_tree, getattr(item, "node", None)))

    if not entries:
        root_tree = getattr(space, "node_tree", None)
        return _reset_path_to_root(space, root_tree) if _is_animgraph_tree(root_tree) else None

    root_tree, _ = entries[0]
    current_tree = _reset_path_to_root(space, root_tree)
    if current_tree is None:
        return None

    for child_tree, child_node in entries[1:]:
        current_tree = _append_tree_to_path(space, child_tree, child_node)
        if current_tree is None:
            return None

    return current_tree


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

    node_name: StringProperty()

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space:
            return {'CANCELLED'}

        root_tree = getattr(space, "node_tree", None)
        if not _is_animgraph_tree(root_tree):
            self.report({'WARNING'}, "AnimGraph groups can only be opened in an AnimNodeTree editor.")
            return {'CANCELLED'}

        if _ensure_root_path(space, root_tree) is None:
            self.report({'WARNING'}, "Could not initialize AnimGraph breadcrumbs.")
            return {'CANCELLED'}

        parent_tree = _current_tree_from_space(space)
        if not _is_animgraph_tree(parent_tree):
            self.report({'WARNING'}, "Current editor tree is not a valid AnimGraph tree.")
            return {'CANCELLED'}

        node = getattr(parent_tree, "nodes", None)
        node = node.get(self.node_name) if node else None
        if node is None:
            self.report({'WARNING'}, "AnimGraph group node not found in the current tree.")
            return {'CANCELLED'}

        subgroup: NodeTree | None = getattr(node, "node_tree", None)
        if not _is_animgraph_tree(subgroup):
            self.report({'WARNING'}, "AnimGraph group node has no valid subgroup tree.")
            return {'CANCELLED'}

        if subgroup == parent_tree:
            self.report({'WARNING'}, "Cannot enter a group that points to the current tree.")
            return {'CANCELLED'}

        # try:
        # except Exception:
        if subgroup is None:
            self.report({'WARNING'}, "Could not ensure AnimGraph group input/output nodes.")
            return {'CANCELLED'}
        else:
            from ..Nodes.group_node import ensure_group_io_nodes
            ensure_group_io_nodes(subgroup)

        if _append_tree_to_path(space, subgroup, node) is None:
            self.report({'WARNING'}, "Could not enter AnimGraph subgroup.")
            return {'CANCELLED'}

        return {'FINISHED'}


class ANIMGRAPH_OT_exit_group(Operator):
    """Exit to parent AnimGraph group."""

    bl_idname = "animgraph.exit_group"
    bl_label = "Exit AnimGraph Group"

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space:
            return {'CANCELLED'}

        root_tree = getattr(space, "node_tree", None)
        if not _is_animgraph_tree(root_tree):
            self.report({'WARNING'}, "AnimGraph groups can only be exited in an AnimNodeTree editor.")
            return {'CANCELLED'}

        if _ensure_root_path(space, root_tree) is None:
            self.report({'WARNING'}, "Could not restore a valid AnimGraph breadcrumb path.")
            return {'CANCELLED'}

        if _path_len(space) <= 1:
            return {'CANCELLED'}

        if _pop_path(space) is None:
            self.report({'WARNING'}, "Could not exit AnimGraph subgroup.")
            return {'CANCELLED'}

        return {'FINISHED'}


_CLASSES = [
    ANIMGRAPH_OT_enter_group,
    ANIMGRAPH_OT_exit_group,
]
