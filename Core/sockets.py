# animation_graph/Core/sockets.py

import bpy

def _enum_bones_from_selected_armature(self, context):
    """
    Baut die Bone-Liste dynamisch basierend auf self.armature_obj.
    Muss eine Liste von (identifier, name, description) liefern.
    """
    arm_obj = getattr(self, "armature_obj", None)

    if not arm_obj or arm_obj.type != "ARMATURE" or not arm_obj.data:
        return [("", "(erst Armature wählen)", "Bitte zuerst eine Armature auswählen.")]

    items = []
    # arm_obj.data ist bpy.types.Armature, .bones sind Edit/Rest-Bones (nicht PoseBones)
    for b in arm_obj.data.bones:
        items.append((b.name, b.name, ""))

    if not items:
        return [("", "(keine Bones vorhanden)", "Die gewählte Armature hat keine Bones.")]
    return items

def _on_armature_changed(self, context):
    """
    Wenn Armature wechselt: Bone-Auswahl zurücksetzen, falls nicht mehr gültig.
    """
    arm_obj = getattr(self, "armature_obj", None)
    current = getattr(self, "bone_name", "")

    if not arm_obj or arm_obj.type != "ARMATURE" or not arm_obj.data:
        self.bone_name = ""
        return

    if current and current not in arm_obj.data.bones:
        self.bone_name = ""

class NodeSocketBone(bpy.types.NodeSocket):
    bl_idname = "NodeSocketBone"
    bl_label = "Bone"
    display_shape = 'SQUARE'

    armature_obj: bpy.props.PointerProperty(
        name="Armature",
        description="Armature-Objekt aus der aktuellen Datei",
        type=bpy.types.Object,
        poll=lambda self, obj: obj is not None and obj.type == "ARMATURE",
        update=_on_armature_changed,
    )

    bone_name: bpy.props.EnumProperty(
        name="Bone",
        description="Bone to use",
        items=_enum_bones_from_selected_armature,
    )

    def draw(self, context, layout, node, text):
        # Socket-Label links im UI
        if text:
            layout.label(text=text)

        # Group Input Outputs sollen aus dem Action-Panel kommen und hier nicht manuell gesetzt werden.
        if self.is_output and getattr(node, "type", "") == "GROUP_INPUT":
            arm = getattr(self, "armature_obj", None)
            bone = getattr(self, "bone_name", "") or "(kein Bone)"
            arm_name = arm.name if arm else "(keine Armature)"

            col = layout.column(align=True)
            col.enabled = False
            col.label(text=arm_name)
            col.label(text=bone)
            return

        # Wenn verbunden: nur anzeigen, nicht editierbar (dein bisheriges Verhalten)
        if self.is_linked and self.links and (not self.is_output):
            from_sock = self.links[0].from_socket
            linked_arm = getattr(from_sock, "armature_obj", None)
            linked_bone = getattr(from_sock, "bone_name", "") or "(kein Bone)"
            linked_arm_name = linked_arm.name if linked_arm else "(keine Armature)"

            col = layout.column(align=True)
            col.enabled = False
            col.label(text=linked_arm_name)
            col.label(text=linked_bone)
            return

        # Unlinked (oder Output) -> editierbar:
        col = layout.column(align=True)

        # 1) Armature wählen
        col.prop(self, "armature_obj", text="")

        # 2) Bone wählen (nur wenn Armature gültig)
        arm_obj = self.armature_obj
        row = col.row(align=True)
        row.enabled = bool(arm_obj and arm_obj.type == "ARMATURE" and arm_obj.data)
        row.prop(self, "bone_name", text="")

    def draw_color(self, context, node):
        return (0.8, 0.7, 0.2, 1.0)

_SOCKET_PREFIX = "NodeSocket"
def _S(datatype: str) -> str:
    return _SOCKET_PREFIX + datatype.lower().capitalize()
def _D(sockettype: str) -> str | None:
    raw = sockettype.removeprefix(_SOCKET_PREFIX)
    if raw != sockettype: return raw.upper()
    return None

# _S = {
#     "INT":          "NodeSocketInt",
#     "FLOAT":        "NodeSocketFloat",
#     "VECTOR":       "NodeSocketVector",
#     "VECTORXYZ":    "NodeSocketVectorXYZ",
#     "ROTATION":     "NodeSocketRotation",
#     "TRANSLATION":  "NodeSocketVectorTranslation",
#     "MATRIX":       "NodeSocketMatrix",
#     "BONE":         "NodeSocketBone",
#     "BOOL":         "NodeSocketBool",
#     "STRING":       "NodeSocketString",
#     'DATA_BLOCK':   "", # TODO
#     'PYTHON':       "", # TODO
# }
# _S_rev = {v: k for k, v in _S.items() if v}

# _S_INT = "NodeSocketInt"
# _S_FLOAT = "NodeSocketFloat"
# _S_VECTOR = "NodeSocketVector"
# _S_VECTORXYZ = "NodeSocketVectorXYZ"
# _S_ROTATION = "NodeSocketRotation"
# _S_TRANSLATION = "NodeSocketVectorTranslation"
# _S_MATRIX = "NodeSocketMatrix"
# _S_BONE = "NodeSocketBone"
# _S_BOOL = "NodeSocketBool"
# _S_STRING = "NodeSocketString"
# _D = {
#     'FLOAT':        _S_FLOAT,
#     'FLOAT_ARRAY':  None,
#     'INT':          _S_INT,
#     'INT_ARRAY':    None,
#     'BOOL':         _S_BOOL,
#     'BOOL_ARRAY':   None,
#     'STRING':       _S_STRING,
# }
# _SOCKET_VECTORS = {_S("VECTOR"),_S("VECTORXYZ"),_S("ROTATION"),_S("TRANSLATION")}
validLinks = {
    "INT":         {"INT"},
    "FLOAT":       {"FLOAT","INT"},
    "VECTOR":      {"VECTOR","VECTORXYZ","ROTATION","TRANSLATION"},
    "VECTORXYZ":   {"VECTORXYZ","VECTOR"},
    "ROTATION":    {"ROTATION","VECTOR"},
    "TRANSLATION": {"TRANSLATION","VECTOR"},
    "MATRIX":      {"MATRIX"},
    "BONE":        {"BONE"},
}
def isValidLink(l: bpy.types.NodeLink) -> bool:
    try:
        from_sock = l.from_socket
        to_sock = l.to_socket
        vn = from_sock.bl_idname
        zn = to_sock.bl_idname
    except Exception:
        return False

    allowed = _S(validLinks.get(vn))
    if allowed is None: return vn == zn
    return zn in allowed or vn == zn
