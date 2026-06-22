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
    "viseme_aa":  {"jaw": 0.75, "spread": 0.12, "round": 0.00, "upper": 0.08, "lower": 0.50},
    "viseme_E":   {"jaw": 0.40, "spread": 0.32, "round": 0.00, "upper": 0.10, "lower": 0.25},
    "viseme_I":   {"jaw": 0.22, "spread": 0.40, "round": 0.00, "upper": 0.12, "lower": 0.12},
    "viseme_O":   {"jaw": 0.50, "spread": 0.00, "round": 0.45, "upper": 0.06, "lower": 0.32},
    "viseme_U":   {"jaw": 0.35, "spread": 0.00, "round": 0.60, "upper": 0.05, "lower": 0.20},
}

# ── Movement scales (meters) — tuned for clearly visible, natural movement ──
JAW_SCALE    = 0.075   # lower jaw/lip drop
LOWER_SCALE  = 0.035   # additional lower-lip-specific drop
UPPER_SCALE  = 0.035   # upper lip raise
SPREAD_SCALE = 0.040   # corners pulled outward (X)
ROUND_SCALE  = 0.040   # lips pushed forward / pucker (toward -Y, the front direction)

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

    # ── DYNAMIC FEATURE AND MATERIAL IDENTIFICATION ──
    lip_mats = []
    face_mats = []
    teeth_mats = []
    mouth_mats = []

    for mat in face_mesh.data.materials:
        if not mat:
            continue
        name = mat.name.lower()
        if 'lip' in name:
            lip_mats.append(mat.name)
        elif 'face' in name or 'skin' in name or 'head' in name:
            if not any(k in name for k in ['body', 'arm', 'leg', 'hand', 'foot', 'sweater', 'jeans', 'eyelash']):
                face_mats.append(mat.name)
        elif 'teeth' in name or 'tooth' in name:
            teeth_mats.append(mat.name)
        elif 'mouth' in name or 'tongue' in name or 'oral' in name:
            mouth_mats.append(mat.name)

    print("Detected materials:")
    print(f"  Lips: {lip_mats}")
    print(f"  Face/Skin: {face_mats}")
    print(f"  Teeth: {teeth_mats}")
    print(f"  Mouth/Tongue: {mouth_mats}")

    # Fallbacks to defaults if nothing detected
    if not lip_mats: lip_mats = ['Lips_MAT']
    if not face_mats: face_mats = ['face_MAT']
    if not teeth_mats: teeth_mats = ['Teeth_MAT']
    if not mouth_mats: mouth_mats = ['Mouth_MAT']

    # Pre-classify all vertices by their connected material names
    materials = face_mesh.data.materials
    vert_materials = {}
    for poly in face_mesh.data.polygons:
        mat_name = materials[poly.material_index].name if (poly.material_index < len(materials) and materials[poly.material_index]) else "None"
        for v_idx in poly.vertices:
            if v_idx not in vert_materials:
                vert_materials[v_idx] = set()
            vert_materials[v_idx].add(mat_name)

    # Calculate mouth coordinates dynamically using lip vertices
    lip_vert_indices = []
    allowed_lip_indices = set(idx for idx, mat in enumerate(face_mesh.data.materials) if mat and mat.name in lip_mats)
    for poly in face_mesh.data.polygons:
        if poly.material_index in allowed_lip_indices:
            for v_idx in poly.vertices:
                lip_vert_indices.append(v_idx)

    if len(lip_vert_indices) > 0:
        lip_zs = [verts[i].co.z for i in lip_vert_indices]
        lip_xs = [verts[i].co.x for i in lip_vert_indices]
        lip_ys = [verts[i].co.y for i in lip_vert_indices]
        
        mouth_z_center = sum(lip_zs) / len(lip_zs)
        z_band = (max(lip_zs) - min(lip_zs)) * 1.3
        x_band = (max(lip_xs) - min(lip_xs)) * 1.1
        y_min = min(lip_ys) - 0.015
        y_max = max(lip_ys) + 0.055
        print(f"Calculated mouth dimensions:")
        print(f"  mouth_z_center = {mouth_z_center:.4f}, z_band = {z_band:.4f}, x_band = {x_band:.4f}")
    else:
        # Fallback to hardcoded defaults for the Larisa avatar
        mouth_z_center = 1.687
        z_band = 0.022
        x_band = 0.032
        y_min = -0.110
        y_max = -0.060
        print("Fallback mouth dimensions used.")

    # Calculate split Z thresholds dynamically
    teeth_vert_indices = []
    allowed_teeth_indices = set(idx for idx, mat in enumerate(face_mesh.data.materials) if mat and mat.name in teeth_mats)
    for poly in face_mesh.data.polygons:
        if poly.material_index in allowed_teeth_indices:
            for v_idx in poly.vertices:
                teeth_vert_indices.append(v_idx)
                
    if len(teeth_vert_indices) > 0:
        teeth_split_z = sum(verts[i].co.z for i in teeth_vert_indices) / len(teeth_vert_indices)
    else:
        teeth_split_z = 1.689

    # Find the maximum Z coordinate of the mouth interior to use for interpolation limit
    mouth_vert_zs = []
    allowed_mouth_indices = set(idx for idx, mat in enumerate(face_mesh.data.materials) if mat and mat.name in mouth_mats)
    for poly in face_mesh.data.polygons:
        if poly.material_index in allowed_mouth_indices:
            for v_idx in poly.vertices:
                mouth_vert_zs.append(verts[v_idx].co.z)

    if len(mouth_vert_zs) > 0:
        mouth_max_z = max(mouth_vert_zs)
    else:
        mouth_max_z = 1.705
    print(f"Calculated split heights: Teeth split Z = {teeth_split_z:.4f}, Mouth max Z = {mouth_max_z:.4f}")

    skin_lips_indices = set()
    teeth_indices = set()
    mouth_indices = set()

    for i, v in enumerate(verts):
        mats = vert_materials.get(i, set())
        vx, vy, vz = v.co.x, v.co.y, v.co.z

        # Classify skin and lips (deform fully)
        if any(m in mats for m in lip_mats) or any(m in mats for m in face_mats):
            if (abs(vz - mouth_z_center) < z_band and abs(vx) < x_band and y_min < vy < y_max):
                skin_lips_indices.add(i)
        # Classify teeth
        elif any(m in mats for m in teeth_mats):
            if vy < -0.03 and abs(vx) < 0.05:
                teeth_indices.add(i)
        # Classify mouth interior / tongue
        elif any(m in mats for m in mouth_mats):
            if vy < -0.03 and abs(vx) < 0.05:
                mouth_indices.add(i)

    print(f"Skin/Lips vertices for morphing: {len(skin_lips_indices)}")
    print(f"Teeth vertices: {len(teeth_indices)}")
    print(f"Mouth interior vertices: {len(mouth_indices)}")

    # Remove existing viseme shape keys to avoid duplicates when re-running
    if face_mesh.data.shape_keys is not None:
        print("Removing existing viseme shape keys...")
        keys_to_remove = [key.name for key in face_mesh.data.shape_keys.key_blocks if key.name.startswith("viseme_")]
        for kname in keys_to_remove:
            key_block = face_mesh.data.shape_keys.key_blocks[kname]
            face_mesh.shape_key_remove(key_block)

    if face_mesh.data.shape_keys is None or len(face_mesh.data.shape_keys.key_blocks) == 0:
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

        # ── 1. Apply to Skin & Lips (with falloff, rounding, and spread) ──
        for i in skin_lips_indices:
            v  = verts[i]
            vx, vy, vz = v.co.x, v.co.y, v.co.z
            dz = vz - mouth_z_center

            v_fall = max(0.0, 1.0 - abs(dz) / z_band) ** 1.3
            h_fall = max(0.0, 1.0 - abs(vx) / x_band)
            weight = v_fall * h_fall

            new_co = sk.data[i].co

            if dz <= 0:
                # Lower lip / jaw — drops DOWN (decrease Z)
                new_co.z = vz - (jaw * JAW_SCALE + lower * LOWER_SCALE) * weight
            else:
                # Upper lip — rises slightly (increase Z)
                new_co.z = vz + (upper * UPPER_SCALE * weight)

            # Corners spread outward (X) — stronger near the edges of the zone
            edge_bias = abs(vx) / x_band
            new_co.x = vx + (1 if vx > 0 else -1) * (spread * SPREAD_SCALE * weight * edge_bias)

            # Round/pucker — push forward, i.e. MORE negative Y (front = -Y here)
            new_co.y = vy - (rnd * ROUND_SCALE * weight)

        # ── 2. Apply to Teeth (rigidly split upper and lower) ──
        for i in teeth_indices:
            v = verts[i]
            if v.co.z < teeth_split_z:
                sk.data[i].co.z = v.co.z - (jaw * JAW_SCALE)

        # ── 3. Apply to Mouth Interior / Tongue (smooth vertical stretch to prevent tearing) ──
        for i in mouth_indices:
            v = verts[i]
            vz = v.co.z
            if vz < mouth_z_center:
                factor = 1.0
            else:
                denom = mouth_max_z - mouth_z_center
                if denom > 0.001:
                    factor = max(0.0, (mouth_max_z - vz) / denom)
                else:
                    factor = 0.0
            sk.data[i].co.z = v.co.z - (jaw * JAW_SCALE * factor)

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