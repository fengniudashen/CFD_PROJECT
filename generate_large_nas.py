import numpy as np
import os
import time
from scipy.spatial import Delaunay

def generate_points_in_triangle(v1, v2, v3, num_points):
    """Generates random points uniformly within a triangle using barycentric coordinates."""
    # Generate random numbers for barycentric coordinates
    r1 = np.random.rand(num_points, 1)
    r2 = np.random.rand(num_points, 1)

    # Ensure points are inside the triangle
    mask = (r1 + r2) > 1
    r1[mask] = 1 - r1[mask]
    r2[mask] = 1 - r2[mask]

    # Calculate barycentric coordinates
    b1 = r1
    b2 = r2
    b3 = 1 - b1 - b2

    # Calculate points coordinates
    points = b1 * v1 + b2 * v2 + b3 * v3
    return points

def main():
    target_points = 5_000_000  # 目标点数
    min_triangles = 1_000_000  # 最少三角形数
    output_dir = os.path.join("src", "data")
    output_filename = os.path.join(output_dir, "large_star.nas")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating approximately {target_points:,} points and over {min_triangles:,} triangles...")
    start_time = time.time()

    # Define the 10 vertices of a star (5 outer, 5 inner)
    radius_outer = 10.0
    radius_inner = 4.0
    outer_vertices = []
    inner_vertices = []
    for i in range(5):
        angle_outer = np.pi / 2 - 2 * np.pi * i / 5
        angle_inner = angle_outer - np.pi / 5
        outer_vertices.append(np.array([radius_outer * np.cos(angle_outer), radius_outer * np.sin(angle_outer), 0.0]))
        inner_vertices.append(np.array([radius_inner * np.cos(angle_inner), radius_inner * np.sin(angle_inner), 0.0]))

    # Define the 10 triangles forming the star surface
    triangles = []
    for i in range(5):
        # Triangles using outer point and two inner points
        triangles.append((outer_vertices[i], inner_vertices[i], inner_vertices[(i + 4) % 5]))
        # Triangles using center (0,0,0) and two inner points (for a filled star)
        triangles.append((np.array([0.0, 0.0, 0.0]), inner_vertices[i], inner_vertices[(i + 1) % 5]))

    num_triangles = len(triangles)
    points_per_triangle = target_points // num_triangles
    
    # Calculate how many sub-triangles we need per original triangle to reach min_triangles
    # Each original triangle with n points will roughly generate (n-2) triangles in the triangulation
    min_points_per_triangle = (min_triangles // num_triangles) + 3
    points_per_triangle = max(points_per_triangle, min_points_per_triangle) 
    
    # Store all points and their triangle associations
    all_points = []
    point_groups = []  # Each group is a set of points within one of the original triangles
    triangle_areas = []  # To adjust point density based on triangle area
    
    # Calculate areas for each original triangle to distribute points proportionally
    for tri in triangles:
        v1, v2, v3 = tri
        # Calculate triangle area using cross product
        edge1 = v2 - v1
        edge2 = v3 - v1
        area = 0.5 * np.linalg.norm(np.cross(edge1, edge2))
        triangle_areas.append(area)
    
    # Normalize areas to get proportional distribution
    total_area = sum(triangle_areas)
    area_ratios = [area / total_area for area in triangle_areas]
    
    # Recalculate points per triangle based on area
    points_per_area = target_points / total_area
    
    try:
        with open(output_filename, 'w') as f:
            print(f"Writing to {output_filename}...")
            f.write("$ Generated Nastran file with star points and triangles\n")
            f.write("BEGIN BULK\n")
            
            # First, generate all GRID* points
            node_id_counter = 1
            print("Generating points...")
            
            # Process each original triangle
            for i, (tri, area_ratio) in enumerate(zip(triangles, area_ratios)):
                v1, v2, v3 = tri
                
                # Determine number of points for this triangle based on area
                num_points_this_triangle = int(target_points * area_ratio)
                # Ensure minimum number for good triangulation
                num_points_this_triangle = max(num_points_this_triangle, 100)
                
                # Generate points within this triangle
                points_group = generate_points_in_triangle(v1, v2, v3, num_points_this_triangle)
                point_ids_group = []
                points_coords_group = []  # 存储每个点的坐标
                
                # Write all points for this triangle
                for point in points_group:
                    # Write point in GRID* format (2 lines per point)
                    line1 = f"GRID*   {node_id_counter:<16}{0:<16}{point[0]:<16.8E}{point[1]:<16.8E}*       "
                    line2 = f"*       {point[2]:<16.8E}"
                    f.write(line1 + "\n")
                    f.write(line2 + "\n")
                    
                    # Store the node ID and coordinates
                    point_ids_group.append(node_id_counter)
                    points_coords_group.append([point[0], point[1]])  # 只存储XY坐标用于2D三角剖分
                    node_id_counter += 1
                
                # Add the original triangle vertices as additional points for better triangulation
                for vertex in [v1, v2, v3]:
                    # Only add if not too close to existing points
                    line1 = f"GRID*   {node_id_counter:<16}{0:<16}{vertex[0]:<16.8E}{vertex[1]:<16.8E}*       "
                    line2 = f"*       {vertex[2]:<16.8E}"
                    f.write(line1 + "\n")
                    f.write(line2 + "\n")
                    
                    point_ids_group.append(node_id_counter)
                    points_coords_group.append([vertex[0], vertex[1]])  # 只存储XY坐标
                    node_id_counter += 1
                
                # Store all point IDs and coordinates for this group
                point_groups.append((point_ids_group, points_coords_group))
                
                # Print progress
                if (i + 1) % 1 == 0 or i == len(triangles) - 1:
                    print(f"Generated points for {i+1}/{len(triangles)} triangles, {node_id_counter-1} points so far")
            
            total_generated_points = node_id_counter - 1
            print(f"Total points generated: {total_generated_points}")
            
            # Now generate triangles for each group using Delaunay triangulation
            print("\nGenerating triangles...")
            total_triangles = 0
            element_id_counter = 1
            
            for i, (point_ids, points_coords) in enumerate(point_groups):
                # Convert coordinates to numpy array
                points_2d = np.array(points_coords)
                
                # Skip if too few points for triangulation
                if len(points_2d) < 3:
                    continue
                
                # Perform Delaunay triangulation on these points
                try:
                    tri = Delaunay(points_2d)
                    
                    # Write each triangle as a CTRIA3 element
                    for simplex in tri.simplices:
                        p1, p2, p3 = simplex
                        # Map back to the original node IDs
                        n1 = point_ids[p1]
                        n2 = point_ids[p2]
                        n3 = point_ids[p3]
                        
                        # Write CTRIA3 (element_id, property_id, n1, n2, n3)
                        f.write(f"CTRIA3  {element_id_counter:<8}{1:<8}{n1:<8}{n2:<8}{n3:<8}\n")
                        element_id_counter += 1
                        total_triangles += 1
                except Exception as e:
                    print(f"Triangulation error in group {i}: {e}")
                    
                # Print progress
                if (i + 1) % 1 == 0 or i == len(point_groups) - 1:
                    print(f"Triangulated {i+1}/{len(point_groups)} point groups, {total_triangles} triangles so far")
                    
                # If we've already created enough triangles, we can stop
                if total_triangles >= min_triangles:
                    print(f"Reached minimum target of {min_triangles} triangles. Stopping triangulation.")
                    break
            
            # Generate more triangles if we haven't reached the target
            if total_triangles < min_triangles:
                print(f"Only generated {total_triangles} triangles, which is less than the target {min_triangles}.")
                print("Adding simple triangles to reach the target...")
                
                # Generate simple triangles linking adjacent points
                points_remaining = list(range(1, total_generated_points + 1))
                np.random.shuffle(points_remaining)
                
                while total_triangles < min_triangles and len(points_remaining) >= 3:
                    n1 = points_remaining.pop()
                    n2 = points_remaining.pop()
                    n3 = points_remaining.pop()
                    
                    # Write CTRIA3
                    f.write(f"CTRIA3  {element_id_counter:<8}{1:<8}{n1:<8}{n2:<8}{n3:<8}\n")
                    element_id_counter += 1
                    total_triangles += 1
                    
                    # Put the points back to reuse them (to ensure connectivity)
                    points_remaining.append(n1)
                    points_remaining.append(n2)
                    
                    # Print progress periodically
                    if total_triangles % 100000 == 0:
                        print(f"Created {total_triangles} triangles...")
            
            f.write("ENDDATA\n")
            
        end_time = time.time()
        print(f"\nSuccessfully generated {total_generated_points:,} points and {total_triangles:,} triangles.")
        print(f"File saved to: {output_filename}")
        print(f"Generation took {end_time - start_time:.2f} seconds.")
        
        # Calculate file size
        file_size_bytes = os.path.getsize(output_filename)
        file_size_mb = file_size_bytes / (1024 * 1024)
        print(f"File size: {file_size_mb:.2f} MB")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 