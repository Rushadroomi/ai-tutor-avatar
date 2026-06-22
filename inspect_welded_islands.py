import bpy

AVATAR_PATH = r"c:\Projects\avatar-project\frontend\avatar.glb"

def inspect():
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    bpy.ops.import_scene.gltf(filepath=AVATAR_PATH)
    face_mesh = max([obj for obj in bpy.context.scene.objects if obj.type == 'MESH'], key=lambda o: len(o.data.vertices))
    
    # Enter Edit Mode and remove doubles (weld vertices)
    bpy.context.view_layer.objects.active = face_mesh
    face_mesh.select_set(True)
    
    print("Welding duplicate vertices...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    verts = face_mesh.data.vertices
    materials = face_mesh.data.materials
    print(f"Mesh now has {len(verts)} vertices (down from split count).")
    
    # Get materials per vertex
    vert_to_mats = {i: set() for i in range(len(verts))}
    for poly in face_mesh.data.polygons:
        mat_name = materials[poly.material_index].name if poly.material_index < len(materials) else "None"
        for v_idx in poly.vertices:
            vert_to_mats[v_idx].add(mat_name)
            
    # Build adjacency list
    adj = {i: [] for i in range(len(verts))}
    for edge in face_mesh.data.edges:
        u, v = edge.vertices
        adj[u].append(v)
        adj[v].append(u)
        
    # Get all mouth/teeth vertices
    mouth_teeth_verts = set()
    for i in range(len(verts)):
        mats = vert_to_mats.get(i, set())
        if 'Teeth_MAT' in mats or 'Mouth_MAT' in mats:
            if 'Lips_MAT' not in mats and 'face_MAT' not in mats:
                mouth_teeth_verts.add(i)
                
    # Find components (islands)
    visited = set()
    components = []
    
    for v_idx in mouth_teeth_verts:
        if v_idx not in visited:
            comp = []
            queue = [v_idx]
            visited.add(v_idx)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for n in adj[curr]:
                    if n in mouth_teeth_verts and n not in visited:
                        visited.add(n)
                        queue.append(n)
            components.append(comp)
            
    print(f"\nTotal components found after welding: {len(components)}")
    # Sort components by size descending
    components.sort(key=len, reverse=True)
    
    for idx, comp in enumerate(components[:15]): # Print top 15 largest islands
        z_coords = [verts[i].co.z for i in comp]
        avg_z = sum(z_coords) / len(comp)
        min_z, max_z = min(z_coords), max(z_coords)
        
        comp_mats = set()
        for i in comp:
            comp_mats.update(vert_to_mats[i])
            
        print(f"Component {idx}: {len(comp)} verts, avg_z={avg_z:.4f} (range: {min_z:.4f} to {max_z:.4f}), mats={list(comp_mats)}")

inspect()
