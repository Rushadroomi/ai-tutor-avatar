import bpy

AVATAR_PATH = r"c:\Projects\avatar-project\frontend\avatar.glb"
OUTPUT_PATH = r"c:\Projects\avatar-project\frontend\avatar.glb"

VISEME_SHAPES = {
    "viseme_sil": {"jaw": 0.00, "spread": 0.00, "round": 0.00, "upper": 0.00, "lower": 0.00},
    "viseme_PP":  {"jaw": 0.02, "spread": 0.00, "round": 0.00, "upper": 0.00, "lower": 0.00},
    "viseme_FF":  {"jaw": 0.10, "spread": 0.05, "round": 0.00, "upper": 0.15, "lower": 0.02},
    "viseme_TH":  {"jaw": 0.14, "spread": 0.06, "round": 0.00, "upper": 0.06, "lower": 0.10},
    "viseme_DD":  {"jaw": 0.18, "spread": 0.08, "round": 0.00, "upper": 0.04, "lower": 0.14},
    "viseme_kk":  {"jaw": 0.22, "spread": 0.05, "round": 0.00, "upper": 0.04, "lower": 0.16},
    "viseme_CH":  {"jaw": 0.16, "spread": 0.00, "round": 0.18, "upper": 0.06, "lower": 0.10},
    "viseme_SS":  {"jaw": 0.08, "spread": 0.15, "round": 0.00, "upper": 0.04, "lower": 0.06},
    "viseme_nn":  {"jaw": 0.14, "spread": 0.06, "round": 0.00, "upper": 0.03, "lower": 0.10},
    "viseme_RR":  {"jaw": 0.16, "spread": 0.00, "round": 0.20, "upper": 0.04, "lower": 0.12},
    "viseme_aa":  {"jaw": 0.65, "spread": 0.10, "round": 0.00, "upper": 0.06, "lower": 0.45},
    "viseme_E":   {"jaw": 0.32, "spread": 0.28, "round": 0.00, "upper": 0.08, "lower": 0.20},
    "viseme_I":   {"jaw": 0.18, "spread": 0.35, "round": 0.00, "upper": 0.10, "lower": 0.10},
    "viseme_O":   {"jaw": 0.42, "spread": 0.00, "round": 0.40, "upper": 0.05, "lower": 0.28},
    "viseme_U":   {"jaw": 0.28, "spread": 0.00, "round": 0.55, "upper": 0.04, "lower": 0.16},
}

# ── VALIDATED zone — confirmed by visual inspection in Blender ──
MOUTH_Z_CENTER = 1.687
Z_BAND  = 0.022
X_BAND  = 0.032
Y_MIN   = -0.110
Y_MAX   = -0.060

# ── Movement scales (meters) — tuned for clearly visible, natural movement ──
JAW_SCALE    = 0.035   # lower jaw/lip drop
LOWER_SCALE  = 0.018   # additional lower-lip-specific drop
UPPER_SCALE  = 0.018   # upper lip raise
SPREAD_SCALE = 0.025   # corners pulled outward (X)
ROUND_SCALE  = 0.025   # lips pushed forward / pucker (toward -Y, the front direction)

def add_visemes():
    print("Clearing scene...")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    print(f"Importing {AVATAR_PATH}")
    bpy.ops.import_scene.gltf(filepath=AVATAR_PATH)

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    face_mesh = max(meshes, key=lambda o: len(o.data.vertices))
    print(f"Using mesh: {face_mesh.name} ({len(face_mesh.data.vertices)} verts)")

    bpy.context.view_layer.objects.active = face_mesh
    face_mesh.select_set(True)

    verts = face_mesh.data.vertices

    # Identify mouth verts using the VALIDATED zone
    mouth_indices = []
    for i, v in enumerate(verts):
        if (abs(v.co.z - MOUTH_Z_CENTER) < Z_BAND and
            abs(v.co.x) < X_BAND and
            Y_MIN < v.co.y < Y_MAX):
            mouth_indices.append(i)
    print(f"Mouth zone verts: {len(mouth_indices)}")

    if face_mesh.data.shape_keys is None:
        bpy.ops.object.shape_key_add(from_mix=False)
        face_mesh.data.shape_keys.key_blocks[0].name = "Basis"

    for vname, params in VISEME_SHAPES.items():
        sk = face_mesh.shape_key_add(name=vname, from_mix=False)
        sk.value = 0.0

        jaw    = params["jaw"]
        spread = params["spread"]
        rnd    = params["round"]
        upper  = params["upper"]
        lower  = params["lower"]

        for i in mouth_indices:
            v  = verts[i]
            vx, vy, vz = v.co.x, v.co.y, v.co.z
            dz = vz - MOUTH_Z_CENTER

            v_fall = max(0.0, 1.0 - abs(dz) / Z_BAND) ** 1.3
            h_fall = max(0.0, 1.0 - abs(vx) / X_BAND)
            weight = v_fall * h_fall

            new_co = sk.data[i].co

            if dz <= 0:
                # Lower lip / jaw — drops DOWN (decrease Z)
                new_co.z = vz - (jaw * JAW_SCALE + lower * LOWER_SCALE) * weight
            else:
                # Upper lip — rises slightly (increase Z)
                new_co.z = vz + (upper * UPPER_SCALE * weight)

            # Corners spread outward (X) — stronger near the edges of the zone
            edge_bias = abs(vx) / X_BAND
            new_co.x = vx + (1 if vx > 0 else -1) * (spread * SPREAD_SCALE * weight * edge_bias)

            # Round/pucker — push forward, i.e. MORE negative Y (front = -Y here)
            new_co.y = vy - (rnd * ROUND_SCALE * weight)

        print(f"  Added: {vname}")

    print("\nAll visemes added!")
    print(f"Exporting to {OUTPUT_PATH}")
    bpy.ops.export_scene.gltf(
        filepath=OUTPUT_PATH,
        export_format='GLB',
        export_morph=True,
        export_morph_normal=False,
        export_materials='EXPORT',
    )
    print("Export complete!")

add_visemes()