"""
算法工具类
包含各种检测算法共享的辅助函数，如八叉树和三角形相交检测
"""

import numpy as np

class OctreeNode:
    """八叉树节点"""
    def __init__(self, center, size, depth):
        self.center = center
        self.size = size
        self.depth = depth
        self.face_indices = []
        self.children = None

    def get_octant(self, point):
        """确定点属于哪个八分区"""
        return ((point[0] > self.center[0]) << 2 |
                (point[1] > self.center[1]) << 1 |
                (point[2] > self.center[2]))


class AlgorithmUtils:
    """
    算法工具类，提供各种检测算法共享的功能
    """
    
    @staticmethod
    def create_octree(faces, vertices, max_depth=10, min_faces=10):
        """
        创建八叉树空间分区
        
        参数:
        faces (np.ndarray): 面片数据
        vertices (np.ndarray): 顶点数据
        max_depth (int): 最大深度
        min_faces (int): 叶节点最小面片数
        
        返回:
        OctreeNode: 八叉树根节点
        """
        # 计算所有面片的包围盒
        face_vertices = vertices[faces]
        min_bounds = np.min(face_vertices.reshape(-1, 3), axis=0)
        max_bounds = np.max(face_vertices.reshape(-1, 3), axis=0)
        center = (min_bounds + max_bounds) / 2
        size = max(max_bounds - min_bounds) * 1.01  # 稍微扩大一点以确保包含所有面片

        def build_octree(node, face_indices):
            if len(face_indices) <= min_faces or node.depth >= max_depth:
                node.face_indices = face_indices
                return

            # 创建子节点
            node.children = [None] * 8
            child_faces = [[] for _ in range(8)]
            half_size = node.size / 2

            # 分配面片到子节点
            for face_idx in face_indices:
                face_center = np.mean(vertices[faces[face_idx]], axis=0)
                octant = node.get_octant(face_center)
                child_faces[octant].append(face_idx)

            # 递归构建子节点
            for i in range(8):
                if child_faces[i]:
                    offset = np.array([(i & 4) > 0, (i & 2) > 0, (i & 1) > 0]) * half_size - half_size/2
                    child_center = node.center + offset
                    node.children[i] = OctreeNode(child_center, half_size, node.depth + 1)
                    build_octree(node.children[i], child_faces[i])

        # 创建根节点并构建八叉树
        root = OctreeNode(center, size, 0)
        build_octree(root, list(range(len(faces))))
        return root
    
    @staticmethod
    def check_triangle_intersection(tri1_verts, tri2_verts):
        """
        使用分离轴定理(SAT)检查两个三角形是否相交
        
        参数:
        tri1_verts (np.ndarray): 第一个三角形的三个顶点坐标，形状为(3, 3)
        tri2_verts (np.ndarray): 第二个三角形的三个顶点坐标，形状为(3, 3)
        
        返回:
        bool: 如果两个三角形相交则返回True，否则返回False
        """
        # 快速共面检测 - 如果两个三角形近似共面且不重叠，可以快速排除
        def get_normal(tri):
            v1 = tri[1] - tri[0]
            v2 = tri[2] - tri[0]
            normal = np.cross(v1, v2)
            norm = np.linalg.norm(normal)
            if norm < 1e-10:  # 处理退化三角形
                return np.zeros(3)
            return normal / norm
        
        # 获取三角形的边
        def get_edges(tri):
            return [tri[1] - tri[0], tri[2] - tri[1], tri[0] - tri[2]]
        
        # 投影三角形到轴上
        def project_triangle(tri, axis):
            dots = [np.dot(v, axis) for v in tri]
            return min(dots), max(dots)
        
        # 检查在给定轴上是否分离
        def check_separation(tri1, tri2, axis):
            if np.all(np.abs(axis) < 1e-10):  # 避免零向量
                return False
            p1_min, p1_max = project_triangle(tri1, axis)
            p2_min, p2_max = project_triangle(tri2, axis)
            return p1_max < p2_min or p2_max < p1_min
        
        # 1. 检查面法向量轴
        normal1 = get_normal(tri1_verts)
        normal2 = get_normal(tri2_verts)
        
        if not np.all(np.abs(normal1) < 1e-10) and check_separation(tri1_verts, tri2_verts, normal1):
            return False
        
        if not np.all(np.abs(normal2) < 1e-10) and check_separation(tri1_verts, tri2_verts, normal2):
            return False
        
        # 2. 检查边叉积轴
        edges1 = get_edges(tri1_verts)
        edges2 = get_edges(tri2_verts)
        
        for e1 in edges1:
            for e2 in edges2:
                cross = np.cross(e1, e2)
                if np.any(np.abs(cross) > 1e-10):  # 避免接近零的叉积
                    axis = cross / np.linalg.norm(cross)
                    if check_separation(tri1_verts, tri2_verts, axis):
                        return False
        
        # 没有找到分离轴，三角形相交
        return True
    
    @staticmethod
    def calculate_face_bboxes(faces, vertices):
        """
        计算所有面片的AABB包围盒
        
        参数:
        faces (np.ndarray): 面片数据
        vertices (np.ndarray): 顶点数据
        
        返回:
        list: 包含每个面片包围盒的列表，每个包围盒是(min_coords, max_coords)元组
        """
        face_bboxes = []
        for face_idx in range(len(faces)):
            face_verts = vertices[faces[face_idx]]
            min_coords = np.min(face_verts, axis=0)
            max_coords = np.max(face_verts, axis=0)
            face_bboxes.append((min_coords, max_coords))
        return face_bboxes 