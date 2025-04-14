import os
import sys
import time
import numpy as np
from PyQt5.QtWidgets import QApplication

# Import the necessary reader class from the existing mesh_reader module
try:
    from mesh_reader import NastranReader
except ImportError:
    print("Error: Could not import NastranReader from mesh_reader.py.")
    print("Ensure mesh_reader.py is in the correct location.")
    exit(1)

# Import the MeshViewerQt class from the mesh_viewer_qt module
try:
    from src.mesh_viewer_qt import MeshViewerQt
except ImportError:
    print("Error: Could not import MeshViewerQt from src/mesh_viewer_qt.py.")
    print("Ensure src/mesh_viewer_qt.py exists.")
    exit(1)

def compute_normals(vertices, faces):
    """计算顶点法向量"""
    normals = np.zeros_like(vertices)
    
    # 计算每个面的法向量
    for face in faces:
        if len(face) >= 3:
            v1, v2, v3 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
            # 计算两条边
            edge1 = v2 - v1
            edge2 = v3 - v1
            # 计算面法向量
            face_normal = np.cross(edge1, edge2)
            # 归一化
            norm = np.linalg.norm(face_normal)
            if norm > 0:
                face_normal /= norm
            # 将面法向量加到顶点
            for idx in face:
                normals[idx] += face_normal
    
    # 归一化顶点法向量
    for i in range(len(normals)):
        norm = np.linalg.norm(normals[i])
        if norm > 0:
            normals[i] /= norm
        else:
            normals[i] = np.array([0, 0, 1])  # 默认法向量
    
    return normals

def main():
    # Define the path to the LARGE mesh file
    mesh_file_path = os.path.join("src", "data", "large_star.nas")

    print(f"--- Loading LARGE file with Python: {mesh_file_path} ---")
    
    if not os.path.exists(mesh_file_path):
        print(f"Error: Mesh file not found at '{mesh_file_path}'")
        return 1

    # Initialize the Python QT application
    app = QApplication(sys.argv)
        
    start_time_py = time.perf_counter()
    try:
        # Load the mesh using pure Python
        py_reader = NastranReader()
        print(f"Attempting to load mesh file using NastranReader...")
        mesh_data_py = py_reader.read(mesh_file_path)
        end_time_py = time.perf_counter()
        duration_py = end_time_py - start_time_py
        
        if mesh_data_py and mesh_data_py.get('nodes') is not None and mesh_data_py['nodes'].size > 0:
            print(f"Successfully loaded {mesh_data_py['nodes'].shape[0]} nodes in {duration_py:.4f} seconds.")
            
            # Convert the mesh_data_py to the format expected by MeshViewerQt
            # MeshViewerQt expects: 'vertices', 'faces', 'normals'
            vertices = mesh_data_py['nodes']
            
            # If 'elements' exists, use it for faces, otherwise create an empty array
            if 'elements' in mesh_data_py:
                faces = mesh_data_py['elements']
            else:
                print("Warning: No elements found in the loaded data. Creating empty array.")
                faces = np.array([], dtype=np.int32).reshape(0, 3)
            
            # Compute normals if needed
            normals = compute_normals(vertices, faces)
            
            # Create the dictionary in the format expected by MeshViewerQt
            viewer_data = {
                'vertices': vertices,
                'faces': faces,
                'normals': normals
            }
            
            print("\nLaunching Mesh Viewer with loaded data...")
            # Create and show the mesh viewer
            viewer = MeshViewerQt(viewer_data)
            viewer.show()
            
            # Start the Qt event loop
            return app.exec_()
            
        else:
            print(f"Python reader finished in {duration_py:.4f} seconds, but no valid nodes were loaded.")
            return 1
        
    except Exception as e:
        end_time_py = time.perf_counter()
        duration_py = end_time_py - start_time_py
        print(f"Error loading mesh with Python module after {duration_py:.4f} seconds: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 