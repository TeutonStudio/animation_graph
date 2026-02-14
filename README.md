# AnimationGraph

AnimationGraph ist ein Blender-Addon fuer node-basierte Animationslogik auf Armatures.
Es verknuepft eine `Action` mit einem `AnimNodeTree`, wertet diesen pro Frame aus und schreibt Bone-Transforms sowie Bone-Properties.

## Status

- Version: `0.2.3`
- Addon-ID: `animgraph`
- Ziel-Blender-Version: `>= 5.0.0`

## Features

- Eigener Node-Tree-Typ `AnimNodeTree` (Animation Node Editor).
- Action-Binding ueber `Action.animgraph_tree`.
- Action-Inputs aus Group-Interface-Sockets im Dopesheet-Panel.
- Runtime-Evaluation ueber `frame_change_post` und `depsgraph_update_post`.
- Bone-Socket-Typ `NodeSocketBone` fuer Armature/Bone-Referenzen.
- Bone Transform schreiben/lesen (Components oder Matrix, inklusive Delta-Modus).
- Bone Property schreiben/lesen (Bool, Int, Float, Vector, Matrix, String, JSON).
- Math-/Adapter-Nodes fuer Zahlen, Vektoren und Matrizen.
- Group-Node mit Subtree-Interface-Sync.
- Timekey-Sync zwischen Tree und Action (`animgraph_time`, inkl. Legacy-Keys `timeKeys`/`time_keys`).

## Installation

### Option 1: Addon installieren

1. Projektordner zippen (die ZIP muss direkt `__init__.py` enthalten).
2. In Blender `Edit > Preferences > Add-ons > Install from Disk...` oeffnen.
3. ZIP auswaehlen und `AnimationGraph` aktivieren.

### Option 2: Entwicklungssetup

1. Ordner in den lokalen Blender-Addon-Pfad legen oder symlinken.
2. Blender neu starten oder das Addon neu laden.

## Quickstart

1. Ein Armature-Objekt mit aktiver `Action` auswaehlen.
2. Im `Dope Sheet` (Action Editor) in der Sidebar das Panel **AnimationNodes** oeffnen.
3. Bei `Animation Graph` auf `New` klicken, um `<ActionName>_AnimGraph` zu erstellen und zuzuweisen.
4. Im Node Editor den Tree-Typ **Animation Node Editor** waehlen.
5. Einen Basisgraph bauen, z. B. `Bone` -> `Transform Bone`, dann `Start` und `Duration` setzen.
6. Timeline scrubben oder abspielen; der Graph wird pro Frame ausgewertet.

## Node-Kategorien

- `RigGraph`: `DefineBoneNode`, `DefineBoneTransformNode`, `DefineBonePropertyNode`, `ReadBoneTransformNode`, `ReadBonePropertyNode`
- `Input: Constant`: `IntConst`, `FloatConst`, `VectorConst`, `RotationConst`, `TranslationConst`, `MatrixConst`
- `Utility: Math`: `IntMath`, `FloatMath`, `VectorMath`, `MatrixMath`
- `Adapter`: `CombineXYZ`, `SeparateXYZ`, `ComposeMatrix`, `DecomposeMatrix`
- `Group`: `AnimNodeGroup`, `NodeGroupInput`, `NodeGroupOutput`

## Projektstruktur

- `__init__.py`: Addon-Entry und Modul-Registrierung.
- `blender_manifest.toml`: Addon-Metadaten.
- `animgraph_eval.py`: Frame-/Depsgraph-Handler und zentrale Evaluation.
- `animgraph_nodes.py`: Node-Registrierung und Kategorien.
- `Core/node_tree.py`: `AnimNodeTree` und Action-Binding.
- `Core/sockets.py`: `NodeSocketBone` und Link-Validierung.
- `Core/helper_methoden.py`: Action-Input-/Timekey-Sync und Import/Export.
- `Core/action_editor.py`: PropertyGroup fuer Action-Input-Werte.
- `Nodes/`: Bone-, Transform-, Math-, Group- und Iteration-Nodes.
- `UI/action_operator.py`: Dopesheet-Panel und Tree-Erstellung.
- `UI/group_operator.py`: Group-Enter-Operator.

## Aktuelle Einschraenkungen

- Armature-only Design (kein allgemeiner Object-Graph).
- Single-Link-Auswertung pro Input (erster Link wird gelesen).
- `AnimNodeRepeatInput`/`AnimNodeRepeatOutput` sind implementiert, aber nicht in den Node-Kategorien eingetragen.
- Ein `Exit Group`-Operator existiert im Code, ist aktuell nicht registriert.
