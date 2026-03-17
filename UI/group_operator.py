# animation_graph/UI/group_operator.py

import bpy
from bpy.props import IntProperty, StringProperty
from bpy.types import Operator, Panel, NodeTree


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


def _get_space_node_editor(context):
    space = getattr(context, "space_data", None)
    return space if isinstance(space, bpy.types.SpaceNodeEditor) else None


def _is_animgraph_tree(tree):
    return getattr(tree, "bl_idname", None) == "AnimNodeTree"


def _rna_key(rna):
    if rna is None:
        return None
    try:
        return int(rna.as_pointer())
    except Exception:
        return id(rna)


def _same_rna(a, b):
    return _rna_key(a) == _rna_key(b)


def _path_len(space):
    path = getattr(space, "path", None)
    return len(path) if path is not None else 0


def _path_tree(space, index):
    try:
        return getattr(space.path[index], "node_tree", None)
    except Exception:
        return None


def _path_node(space, index):
    try:
        return getattr(space.path[index], "node", None)
    except Exception:
        return None


def _get_root_animgraph_tree(space):
    root_tree = getattr(space, "node_tree", None)
    return root_tree if _is_animgraph_tree(root_tree) else None


def _get_current_animgraph_tree(space):
    edit_tree = getattr(space, "edit_tree", None)
    if _is_animgraph_tree(edit_tree):
        return edit_tree

    tail_tree = _path_tree(space, -1)
    if _is_animgraph_tree(tail_tree):
        return tail_tree

    return _get_root_animgraph_tree(space)


def _collect_path_entries(space):
    path = getattr(space, "path", None)
    if path is None:
        return None

    entries = []
    try:
        items = list(path)
    except Exception:
        return None

    for item in items:
        tree = getattr(item, "node_tree", None)
        if not _is_animgraph_tree(tree):
            return None
        entries.append((tree, getattr(item, "node", None)))
    return entries


def _clear_path(space):
    path = getattr(space, "path", None)
    if path is None:
        return False

    while len(path):
        try:
            path.pop()
        except Exception:
            return False
    return True


def _find_path_steps(tree, target_tree, visited):
    if _same_rna(tree, target_tree):
        return []

    tree_key = _rna_key(tree)
    if tree_key in visited:
        return None

    next_visited = set(visited)
    next_visited.add(tree_key)

    for node in getattr(tree, "nodes", []):
        if getattr(node, "bl_idname", None) != "AnimNodeGroup":
            continue

        subtree = getattr(node, "node_tree", None)
        if not _is_animgraph_tree(subtree):
            continue
        if _same_rna(subtree, tree):
            continue

        child_steps = _find_path_steps(subtree, target_tree, next_visited)
        if child_steps is not None:
            return [(subtree, node)] + child_steps

    return None


def _build_path_entries(root_tree, target_tree):
    if not _is_animgraph_tree(root_tree):
        return None

    target_tree = target_tree if _is_animgraph_tree(target_tree) else root_tree
    child_steps = _find_path_steps(root_tree, target_tree, set())
    if child_steps is None:
        if not _same_rna(root_tree, target_tree):
            return None
        child_steps = []

    return [(root_tree, None)] + child_steps


def _path_entries_match(left_entries, right_entries):
    if not left_entries or not right_entries:
        return False
    if len(left_entries) != len(right_entries):
        return False

    for (left_tree, left_node), (right_tree, right_node) in zip(left_entries, right_entries):
        if not _same_rna(left_tree, right_tree):
            return False
        if not _same_rna(left_node, right_node):
            return False
    return True


def _apply_path_entries(space, entries):
    if not entries or not _is_animgraph_tree(entries[0][0]):
        return None

    path = getattr(space, "path", None)
    if path is None:
        return None

    if not _clear_path(space):
        return None

    try:
        path.start(entries[0][0])
    except Exception:
        return None

    for tree, node in entries[1:]:
        try:
            path.append(tree, node=node)
        except Exception:
            _apply_root_fallback(space, entries[0][0])
            return None

    current_tree = _get_current_animgraph_tree(space)
    expected_tree = entries[-1][0]
    if not _same_rna(current_tree, expected_tree):
        _apply_root_fallback(space, entries[0][0])
        return None
    return current_tree


def _apply_root_fallback(space, root_tree):
    if not _is_animgraph_tree(root_tree):
        return None
    if not _clear_path(space):
        return None
    try:
        space.path.start(root_tree)
    except Exception:
        return None
    return _get_current_animgraph_tree(space)


def _ensure_root_path(space, tree):
    if not _is_animgraph_tree(tree):
        return None

    current_tree = _get_current_animgraph_tree(space)
    if not _is_animgraph_tree(current_tree):
        current_tree = tree

    rebuilt_entries = _build_path_entries(tree, current_tree)
    if rebuilt_entries is None:
        rebuilt_entries = [(tree, None)]

    entries = _collect_path_entries(space)
    if _path_entries_match(entries, rebuilt_entries):
        return current_tree

    return _apply_path_entries(space, rebuilt_entries)


def _path_contains_tail(space, subtree, node):
    if _path_len(space) == 0:
        return False
    return _same_rna(_path_tree(space, -1), subtree) and _same_rna(_path_node(space, -1), node)


def _append_tree_to_path(space, tree, node):
    if not _is_animgraph_tree(tree):
        return None

    if _path_contains_tail(space, tree, node):
        return _get_current_animgraph_tree(space)

    try:
        space.path.append(tree, node=node)
    except Exception:
        return None

    current_tree = _get_current_animgraph_tree(space)
    return current_tree if _same_rna(current_tree, tree) else None


def _pop_path(space):
    entries = _collect_path_entries(space)
    if not entries:
        return None
    if len(entries) <= 1:
        return entries[0][0]
    return _apply_path_entries(space, entries[:-1])


def _jump_to_path_index(space, path_index):
    entries = _collect_path_entries(space)
    if not entries:
        return None
    if path_index < 0 or path_index >= len(entries):
        return None
    return _apply_path_entries(space, entries[: path_index + 1])


def _display_path_entries(space):
    root_tree = _get_root_animgraph_tree(space)
    if not _is_animgraph_tree(root_tree):
        return []

    current_tree = _get_current_animgraph_tree(space)
    rebuilt_entries = _build_path_entries(root_tree, current_tree)
    if rebuilt_entries is None:
        rebuilt_entries = [(root_tree, None)]

    entries = _collect_path_entries(space)
    return entries if _path_entries_match(entries, rebuilt_entries) else rebuilt_entries


def _tag_navigation_refresh(context, space):
    tree = _get_current_animgraph_tree(space)
    if tree is not None:
        try:
            tree.update_tag()
        except Exception:
            pass

    area = getattr(context, "area", None)
    if area is not None:
        try:
            area.tag_redraw()
        except Exception:
            pass


class ANIMGRAPH_OT_make_group(Operator):
    bl_idname = "animgraph.make_group"
    bl_label = "Enter AnimGraph Group"

    # TODO Selektierte Nodes ermitteln
    # TODO Selektierte Nodes in neuen AnimNodeTree
    # TODO verbindungen von selektierten zu unselektierten Node als Ein- und AusgangsSocket des neuen AnimNodeTree definieren
    # TODO AnimNodeGroup mit neuem AnimNodeTree erstellen
    # TODO Verbindungen von unselektierten zu Selektierten Node an AnimNodeGroup verlegen


class ANIMGRAPH_OT_enter_group(Operator):
    """Enter an AnimGraph subgroup."""

    bl_idname = "animgraph.enter_group"
    bl_label = "Enter AnimGraph Group"

    node_name: StringProperty()

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space:
            self.report({'WARNING'}, "AnimGraph navigation requires a Node Editor.")
            return {'CANCELLED'}

        root_tree = _get_root_animgraph_tree(space)
        if not _is_animgraph_tree(root_tree):
            self.report({'WARNING'}, "AnimGraph groups can only be opened in an AnimNodeTree editor.")
            return {'CANCELLED'}

        if _ensure_root_path(space, root_tree) is None:
            self.report({'WARNING'}, "Could not initialize the AnimGraph navigation path.")
            return {'CANCELLED'}

        parent_tree = _get_current_animgraph_tree(space)
        if not _is_animgraph_tree(parent_tree):
            self.report({'WARNING'}, "Current editor tree is not a valid AnimGraph tree.")
            return {'CANCELLED'}

        if not self.node_name:
            self.report({'WARNING'}, "AnimGraph group node name is missing.")
            return {'CANCELLED'}

        nodes = getattr(parent_tree, "nodes", None)
        node = nodes.get(self.node_name) if nodes else None
        if node is None:
            self.report({'WARNING'}, "AnimGraph group node not found in the current tree.")
            return {'CANCELLED'}
        if getattr(node, "bl_idname", None) != "AnimNodeGroup":
            self.report({'WARNING'}, "Selected node is not an AnimGraph group node.")
            return {'CANCELLED'}

        subgroup: NodeTree | None = getattr(node, "node_tree", None)
        if not _is_animgraph_tree(subgroup):
            self.report({'WARNING'}, "AnimGraph group node has no valid subgroup tree.")
            return {'CANCELLED'}

        if _same_rna(subgroup, parent_tree):
            self.report({'WARNING'}, "Cannot enter a group that points to the current tree.")
            return {'CANCELLED'}

        if subgroup is None: return {'CANCELLED'}

        from ..Nodes.group_node import ensure_group_io_nodes
        ensure_group_io_nodes(subgroup)

        if _append_tree_to_path(space, subgroup, node) is None:
            self.report({'WARNING'}, "Could not enter the selected AnimGraph subgroup.")
            return {'CANCELLED'}

        _tag_navigation_refresh(context, space)
        return {'FINISHED'}


class ANIMGRAPH_OT_exit_group(Operator):
    """Exit to the parent AnimGraph tree."""

    bl_idname = "animgraph.exit_group"
    bl_label = "Exit AnimGraph Group"

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space:
            self.report({'WARNING'}, "AnimGraph navigation requires a Node Editor.")
            return {'CANCELLED'}

        root_tree = _get_root_animgraph_tree(space)
        if not _is_animgraph_tree(root_tree):
            self.report({'WARNING'}, "AnimGraph groups can only be exited in an AnimNodeTree editor.")
            return {'CANCELLED'}

        if _ensure_root_path(space, root_tree) is None:
            self.report({'WARNING'}, "Could not restore a valid AnimGraph navigation path.")
            return {'CANCELLED'}

        if _path_len(space) <= 1:
            self.report({'WARNING'}, "Already at the AnimGraph root tree.")
            return {'CANCELLED'}

        if _pop_path(space) is None:
            self.report({'WARNING'}, "Could not exit the current AnimGraph subgroup.")
            return {'CANCELLED'}

        _tag_navigation_refresh(context, space)
        return {'FINISHED'}


class ANIMGRAPH_OT_jump_to_path_index(Operator):
    """Jump to a specific AnimGraph breadcrumb level."""

    bl_idname = "animgraph.jump_to_path_index"
    bl_label = "Jump to AnimGraph Breadcrumb"
    bl_options = {'INTERNAL'}

    path_index: IntProperty(min=0)

    def execute(self, context):
        space = _get_space_node_editor(context)
        if not space:
            self.report({'WARNING'}, "AnimGraph navigation requires a Node Editor.")
            return {'CANCELLED'}

        root_tree = _get_root_animgraph_tree(space)
        if not _is_animgraph_tree(root_tree):
            self.report({'WARNING'}, "AnimGraph breadcrumbs are only available in an AnimNodeTree editor.")
            return {'CANCELLED'}

        if _ensure_root_path(space, root_tree) is None:
            self.report({'WARNING'}, "Could not restore a valid AnimGraph navigation path.")
            return {'CANCELLED'}

        entries = _collect_path_entries(space)
        if not entries:
            self.report({'WARNING'}, "AnimGraph breadcrumb path is empty.")
            return {'CANCELLED'}

        if self.path_index >= len(entries):
            self.report({'WARNING'}, "AnimGraph breadcrumb target is out of range.")
            return {'CANCELLED'}

        if _jump_to_path_index(space, self.path_index) is None:
            self.report({'WARNING'}, "Could not jump to the selected AnimGraph breadcrumb.")
            return {'CANCELLED'}

        _tag_navigation_refresh(context, space)
        return {'FINISHED'}


class ANIMGRAPH_PT_group_navigation(Panel):
    bl_label = "Navigation"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "AnimGraph"

    @classmethod
    def poll(cls, context):
        space = _get_space_node_editor(context)
        return bool(space and _is_animgraph_tree(_get_root_animgraph_tree(space)))

    def draw(self, context):
        layout = self.layout
        space = _get_space_node_editor(context)
        entries = _display_path_entries(space) if space else []
        if layout is None: return

        if not entries:
            layout.label(text="No active AnimGraph tree.", icon="INFO")
            return

        header = layout.row(align=True)
        if len(entries) > 1:
            header.operator("animgraph.exit_group", text="", icon="FILE_PARENT")
        else:
            header.label(text="", icon="BLANK1")
        header.label(text="Breadcrumb", icon="NODETREE")

        row = layout.row(align=True)
        for index, (tree, _node) in enumerate(entries):
            if index > 0:
                row.label(text="", icon="TRIA_RIGHT")

            label = getattr(tree, "name", "") or "AnimGraph"
            if index == len(entries) - 1:
                row.label(text=label)
                continue

            op = row.operator("animgraph.jump_to_path_index", text=label, emboss=False)
            op.path_index = index


_CLASSES = [
    ANIMGRAPH_OT_enter_group,
    ANIMGRAPH_OT_exit_group,
    ANIMGRAPH_OT_jump_to_path_index,
    ANIMGRAPH_PT_group_navigation,
]
