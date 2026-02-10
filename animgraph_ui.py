# animation_graph/riggraph_ui.py
import bpy

from .Core.node_tree import AnimNodeTree
from .UI import interface_manage, group_operator

_MODULES = [
    interface_manage,
    group_operator,
]

def register(): 
    for m in _MODULES: m.register()
def unregister(): 
    for m in reversed(_MODULES): m.unregister()

# def _active_armature(context):
#     ob = context.active_object
#     if ob and ob.type == "ARMATURE":
#         return ob.data
#     return None


# class DATA_PT_riggraph(Panel):
#     bl_label = "AnimGraph"
#     bl_space_type = "PROPERTIES"
#     bl_region_type = "WINDOW"
#     bl_context = "data"  # Object Data tab

#     @classmethod
#     def poll(cls, context):
#         ob = context.active_object
#         return bool(ob and ob.type == "ARMATURE")

#     def draw(self, context):
#         layout = self.layout
#         arm = _active_armature(context)

#         row = layout.row()
#         row.prop(arm, "riggraph_tree", text="AnimGraph")

#         row = layout.row(align=True)
#         row.operator("riggraph.new", icon="ADD")
#         row.operator("riggraph.open_node_editor", icon="NODETREE")

#         layout.separator()
#         layout.operator("riggraph.make_proxy_action", icon="ACTION")


# class RIGGRAPH_OT_make_proxy_action(Operator):
#     bl_idname = "riggraph.make_proxy_action"
#     bl_label = "Create DopeSheet Action (AnimationGraph)"
#     bl_options = {"REGISTER", "UNDO"}

#     def execute(self, context):
#         arm = _active_armature(context)
#         if not arm:
#             self.report({"WARNING"}, "No active Armature")
#             return {"CANCELLED"}

#         tree = arm.riggraph_tree
#         if not tree:
#             self.report({"WARNING"}, "No RigGraph assigned")
#             return {"CANCELLED"}

#         # Create a real Action, but keep it empty (no fcurves).
#         name = f"RG_{tree.name}"
#         act = bpy.data.actions.get(name)
#         if act is None:
#             act = bpy.data.actions.new(name=name)

#         # Tag it as RigGraph proxy
#         act["riggraph_id"] = "riggraph"
#         act["riggraph_tree"] = tree.name
#         act.use_fake_user = True  # optional but usually helpful

#         # Assign as active action so it shows up immediately
#         ob = context.active_object
#         if ob.animation_data is None:
#             ob.animation_data_create()
#         ob.animation_data.action = act

#         self.report({"INFO"}, f"Proxy Action '{act.name}' created/assigned")
#         return {"FINISHED"}


# class RIGGRAPH_OT_group_edit(bpy.types.Operator):
#     bl_idname = "riggraph.group_edit"
#     bl_label = "Enter Group"

#     node_name: bpy.props.StringProperty()

#     @classmethod
#     def poll(cls, context):
#         snode = context.space_data
#         return snode and snode.type == "NODE_EDITOR" and getattr(snode, "tree_type", "") == AnimNodeTree.bl_idname

#     def execute(self, context):
#         snode = context.space_data
#         node = snode.node_tree.nodes.get(self.node_name)
#         if not node or not getattr(node, "node_tree", None):
#             return {"CANCELLED"}

#         # Pfad erweitern: Gruppe betreten
#         # SpaceNodeEditorPath: (node_tree, node(optional)) :contentReference[oaicite:10]{index=10}
#         snode.path.append(node_tree=node.node_tree, node=node)
#         return {"FINISHED"}


# class RIGGRAPH_OT_group_exit(bpy.types.Operator):
#     bl_idname = "riggraph.group_exit"
#     bl_label = "Exit Group"

#     @classmethod
#     def poll(cls, context):
#         snode = context.space_data
#         return snode and snode.type == "NODE_EDITOR" and len(snode.path) > 1

#     def execute(self, context):
#         context.space_data.path.pop()
#         return {"FINISHED"}
# --------------------------------------------------------------------
# Group Interface editing (Geometry Nodes style)
# --------------------------------------------------------------------

# def _active_animgraph_tree(context):
#     snode = getattr(context, "space_data", None)
#     if not snode or getattr(snode, "type", "") != "NODE_EDITOR":
#         return None
#     if getattr(snode, "tree_type", "") != AnimNodeTree.bl_idname:
#         return None
#     return getattr(snode, "node_tree", None)

# def _interface_socket_types():
#     return [
#         ("NodeSocketFloat", "Float", ""),
#         ("NodeSocketInt", "Int", ""),
#         ("NodeSocketBool", "Bool", ""),
#         ("NodeSocketVector", "Vector", ""),
#         ("NodeSocketColor", "Color", ""),
#         ("NodeSocketString", "String", ""),
#         ("NodeSocketMatrix", "Matrix", ""),
#         ("NodeSocketBone", "Bone", ""),
#     ]

# def _resync_group_system_for_tree(tree):
#     # Resync GroupInput/GroupOutput inside THIS tree
#     for n in getattr(tree, "nodes", []):
#         if getattr(n, "bl_idname", "") in {"ANIMGRAPH_GroupInput", "ANIMGRAPH_GroupOutput"}:
#             try:
#                 n.sync_from_tree_interface()
#             except Exception:
#                 pass

#     # Resync ALL group-call nodes that reference this tree
#     for t in bpy.data.node_groups:
#         if getattr(t, "bl_idname", "") != AnimNodeTree.bl_idname:
#             continue
#         for n in getattr(t, "nodes", []):
#             if getattr(n, "bl_idname", "") != "ANIMGRAPH_Group":
#                 continue
#             if getattr(n, "node_tree", None) == tree:
#                 try:
#                     n.sync_sockets_from_subtree()
#                 except Exception:
#                     pass

#     try:
#         tree.update_tag()
#     except Exception:
#         pass


# class RIGGRAPH_OT_interface_add_socket(bpy.types.Operator):
#     bl_idname = "riggraph.interface_add_socket"
#     bl_label = "Add Group Socket"
#     bl_options = {"REGISTER", "UNDO"}

#     in_out: bpy.props.EnumProperty(
#         name="Direction",
#         items=[("INPUT", "Input", ""), ("OUTPUT", "Output", "")],
#         default="INPUT",
#     )
#     socket_type: bpy.props.EnumProperty(
#         name="Socket Type",
#         items=_interface_socket_types(),
#         default="NodeSocketFloat",
#     )
#     name: bpy.props.StringProperty(name="Name", default="Value")

#     @classmethod
#     def poll(cls, context):
#         tree = _active_animgraph_tree(context)
#         return bool(tree and getattr(tree, "interface", None))

#     def invoke(self, context, event):
#         return context.window_manager.invoke_props_dialog(self)

#     def execute(self, context):
#         tree = _active_animgraph_tree(context)
#         if not tree:
#             return {"CANCELLED"}

#         iface = getattr(tree, "interface", None)
#         if iface is None:
#             self.report({"WARNING"}, "Tree has no interface (Blender API mismatch?)")
#             return {"CANCELLED"}

#         base = (self.name or "").strip() or "Value"
#         existing = {getattr(s, "name", "") for s in _iter_interface_sockets(tree)}
#         name = base
#         i = 2
#         while name in existing:
#             name = f"{base}.{i:03d}"
#             i += 1

#         try:
#             iface.new_socket(name=name, in_out=self.in_out, socket_type=self.socket_type)
#         except TypeError:
#             # some builds use bl_socket_idname instead of socket_type
#             iface.new_socket(name=name, in_out=self.in_out, bl_socket_idname=self.socket_type)

#         _resync_group_system_for_tree(tree)
#         return {"FINISHED"}


# class RIGGRAPH_OT_interface_remove_socket(bpy.types.Operator):
#     bl_idname = "riggraph.interface_remove_socket"
#     bl_label = "Remove Group Socket"
#     bl_options = {"REGISTER", "UNDO"}

#     in_out: bpy.props.EnumProperty(
#         name="Direction",
#         items=[("INPUT", "Input", ""), ("OUTPUT", "Output", "")],
#         default="INPUT",
#     )
#     name: bpy.props.StringProperty(
#         name="Name",
#         default="Value",
#         description="Exact socket name to remove (MVP).",
#     )

#     @classmethod
#     def poll(cls, context):
#         tree = _active_animgraph_tree(context)
#         return bool(tree and getattr(tree, "interface", None))

#     def invoke(self, context, event):
#         return context.window_manager.invoke_props_dialog(self)

#     def execute(self, context):
#         tree = _active_animgraph_tree(context)
#         if not tree:
#             return {"CANCELLED"}

#         iface = getattr(tree, "interface", None)
#         if iface is None:
#             return {"CANCELLED"}

#         target = None
#         for s in _iter_interface_sockets(tree, want_in_out=self.in_out):
#             if getattr(s, "name", None) == self.name:
#                 target = s
#                 break

#         if target is None:
#             self.report({"WARNING"}, f"No {self.in_out} socket named '{self.name}'")
#             return {"CANCELLED"}

#         try:
#             iface.remove(target)
#         except Exception:
#             iface.items_tree.remove(target)

#         _resync_group_system_for_tree(tree)
#         return {"FINISHED"}

# class RIGGRAPH_OT_path_pop_to(bpy.types.Operator):
#     bl_idname = "riggraph.path_pop_to"
#     bl_label = "Jump to Path Level"

#     index: bpy.props.IntProperty(default=0)

#     @classmethod
#     def poll(cls, context):
#         snode = getattr(context, "space_data", None)
#         return bool(snode and getattr(snode, "type", "") == "NODE_EDITOR" and getattr(snode, "path", None))

#     def execute(self, context):
#         snode = context.space_data
#         # Ziel-Länge ist index+1 (weil index 0 = root)
#         target_len = max(1, self.index + 1)
#         while len(snode.path) > target_len:
#             snode.path.pop()
#         return {"FINISHED"}

# def riggraph_draw_breadcrumb(self, context):
#     snode = context.space_data
#     if not snode or snode.type != "NODE_EDITOR": return
#     if getattr(snode, "tree_type", "") != AnimNodeTree.bl_idname: return

#     layout = self.layout

#     # Wie GN: Objekt > "AnimationNodes" > Tree > Subgruppen
#     ob = context.active_object
#     ob_name = ob.name if ob else "<No Object>"

#     row = layout.row(align=True)
#     row.label(text=ob_name, icon="OBJECT_DATA")
#     row.label(text=">", icon="DISCLOSURE_TRI_RIGHT")
#     row.label(text="AnimationNodes", icon="NODETREE")
#     row.label(text=">", icon="DISCLOSURE_TRI_RIGHT")

#     # SpaceNodeEditor.path ist die offizielle Breadcrumb-Quelle
#     # (root + group stack) :contentReference[oaicite:1]{index=1}
#     for i, p in enumerate(snode.path):
#         name = p.node_tree.name if p.node_tree else "<None>"
#         op = row.operator("riggraph.path_pop_to", text=name, emboss=True)
#         op.index = i
#         if i < len(snode.path) - 1:
#             row.label(text=">", icon="DISCLOSURE_TRI_RIGHT")

# def riggraph_draw_breadcrumb_blender_like(self, context):
#     snode = context.space_data
#     if not isinstance(snode, bpy.types.SpaceNodeEditor):
#         return
#     if snode.type != "NODE_EDITOR":
#         return
#     if getattr(snode, "tree_type", "") != AnimNodeTree.bl_idname:
#         return

#     layout = self.layout

#     # Optional: wenn du den echten Blender-Context-Path darunter willst,
#     # einfach anschalten. (Dann solltest du deinen eigenen Pfad evtl. kurz halten.)
#     # snode.overlay.show_context_path = True

#     # Blender-Style: kompakt, klickbar, mit kleinen Trennern
#     # In Blender ist das eher eine "Path Bar", nicht ein riesiger Row-Block.
#     row = layout.row(align=True)

#     # (Optional) Prefix wie "Object" etc. Blender hat je nach Kontext Icons links.
#     ob = context.active_object
#     if ob:
#         # Blender zeigt hier oft nur ein Icon + Name, ohne zusätzliche ">"-Kaskade.
#         op = row.operator("riggraph.path_pop_to", text=ob.name, icon="OBJECT_DATA", emboss=True)
#         op.index = 0  # oder -1 wenn dein Operator so etwas unterstützt
#         # Trenner
#         row.label(text="", icon="RIGHTARROW_THIN")

#     # Root + Group Stack: snode.path[0] ist typischerweise Root-Tree.
#     # Blender zeigt jeden Path-Eintrag als klickbaren Button.
#     path = list(snode.path)

#     # Wenn path leer ist: nichts zu tun
#     if not path:
#         return

#     # Zeige zuerst den Root-Tree (typisch: der aktuelle NodeTree)
#     for i, p in enumerate(path):
#         nt = getattr(p, "node_tree", None)
#         label = nt.name if nt else "<None>"

#         # Blender-Optik: Buttons sind "embossed" aber klein/kompakt
#         op = row.operator("riggraph.path_pop_to", text=label, emboss=True)
#         op.index = i

#         # Trenner zwischen Einträgen
#         if i < len(path) - 1:
#             row.label(text="", icon="RIGHTARROW_THIN")

#     # Optional: Spacer, damit der Rest vom Header nicht von deinem Breadcrumb erschlagen wird
#     # layout.separator_spacer()
