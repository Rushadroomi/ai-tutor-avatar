import bpy

AVATAR_PATH = r"c:\Projects\avatar-project\frontend\avatar.glb"

def inspect():
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    bpy.ops.import_scene.gltf(filepath=AVATAR_PATH)
    face_mesh = max([obj for obj in bpy.context.scene.objects if obj.type == 'MESH'], key=lambda o: len(o.data.vertices))
    
    verts = face_mesh.data.vertices
    materials = face_mesh.data.materials
    
    # Get vertices per material
    mat_verts = {}
    for mat in materials:
        if mat:
            mat_verts[mat.name] = []
            
    # Associate vertices with materials via polygons
    vert_to_mats = {i: set() for i in range(len(verts))}
    for poly in face_mesh.data.polygons:
        mat_name = materials[poly.material_index].name if poly.material_index < len(materials) else "None"
        for v_idx in poly.vertices:
            vert_to_mats[v_idx].add(mat_name)
            
    for i, v in enumerate(verts):
        for mname in vert_to_mats[i]:
            if mname in mat_verts:
                mat_verts[mname].append(v)
                
    for mname in ['Teeth_MAT', 'Mouth_MAT']:
        m_verts = mat_verts.get(mname, [])
        if m_verts:
            z_coords = [v.co.z for v in m_verts]
            y_coords = [v.co.y for v in m_verts]
            x_coords = [v.co.x for v in m_verts]
            print(f"\nMaterial: {mname} ({len(m_verts)} vertices)")
            print(f"  Z range: {min(z_coords):.4f} to {max(z_coords):.4f}")
            print(f"  Y range: {min(y_coords):.4f} to {max(y_coords):.4f}")
            print(f"  X range: {min(x_coords):.4f} to {max(x_coords):.4f}")

inspect()
