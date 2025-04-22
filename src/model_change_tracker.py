from typing import Dict, List, Set, Tuple
import numpy as np
import time
import random
import traceback
from PyQt5.QtCore import QObject, QTimer

# 导入各种检测算法
try:
    from algorithms.combined_intersection_algorithm import CombinedIntersectionAlgorithm
except ImportError:
    print("警告：未找到CombinedIntersectionAlgorithm模块")
    
    # 创建一个空的类作为后备
    class CombinedIntersectionAlgorithm:
        def __init__(self, *args, **kwargs):
            pass
        
        def execute(self, *args, **kwargs):
            return {}

try:
    from algorithms.face_quality_algorithm import FaceQualityAlgorithm
except ImportError:
    class FaceQualityAlgorithm:
        def __init__(self, mesh_data, threshold=0.3):
            self.mesh_data = mesh_data
            self.threshold = threshold
            self.use_cpp = False
            self.target_faces = None
        def execute(self, parent=None):
            print("警告：未找到FaceQualityAlgorithm模块")
            return {}

try:
    from algorithms.free_edges_algorithm import FreeEdgesAlgorithm
except ImportError:
    class FreeEdgesAlgorithm:
        def __init__(self, mesh_data):
            self.mesh_data = mesh_data
            self.target_edges = None
            self.use_cpp = False
        def execute(self, parent=None):
            print("警告：未找到FreeEdgesAlgorithm模块")
            return {}

try:
    from algorithms.overlapping_edges_algorithm import OverlappingEdgesAlgorithm
except ImportError:
    class OverlappingEdgesAlgorithm:
        def __init__(self, mesh_data):
            self.mesh_data = mesh_data
            self.target_edges = None
            self.use_cpp = False
        def execute(self, parent=None):
            print("警告：未找到OverlappingEdgesAlgorithm模块")
            return {}

try:
    from algorithms.non_manifold_vertices_algorithm import NonManifoldVerticesAlgorithm
except ImportError:
    class NonManifoldVerticesAlgorithm:
        def __init__(self, mesh_data):
            self.mesh_data = mesh_data
            self.use_cpp = False
            self.target_vertices = None
        def execute(self, parent=None):
            print("警告：未找到NonManifoldVerticesAlgorithm模块")
            return {}

# 导入算法包中的类，后面会判断是否能用其 C++ 核心
from algorithms.combined_intersection_algorithm import CombinedIntersectionAlgorithm
from algorithms.face_quality_algorithm import FaceQualityAlgorithm
from algorithms.free_edges_algorithm import FreeEdgesAlgorithm
from algorithms.overlapping_edges_algorithm import OverlappingEdgesAlgorithm
from algorithms.merged_vertex_detection_algorithm import MergedVertexDetectionAlgorithm

class ModelChangeTracker:
    """模型变更追踪器 - 用于跟踪模型变更并高效更新分析结果"""
    
    def __init__(self, mesh_viewer):
        self.mesh_viewer = mesh_viewer
        
        # 缓存当前模型状态
        self.cached_model_state = {
            "points": set(),          # 点ID集合
            "edges": set(),           # 边ID集合
            "faces": set(),           # 面ID集合
            "point_connections": {},  # 点到相连点/边/面的映射
            "edge_connections": {},   # 边到相连点/边/面的映射
            "face_connections": {},   # 面到相连点/边/面的映射
        }
        
        # 缓存按钮状态
        self.cached_button_counts = {
            "交叉面": 0,    # 相交面
            "面质量": 0,    # 面质量问题
            "相邻面": 0,    # 相邻面
            "自由边": 0,    # 自由边
            "重叠边": 0,    # 重叠边
            "重叠点": 0     # 重叠点
        }
        
        # 缓存检测结果(保存具体元素集合而非仅数量)
        self.detection_results = {
            'face_intersections': [],  # 相交面
            'face_quality': [],        # 面质量问题
            'adjacent_faces': [],      # 相邻面
            'free_edges': [],          # 自由边
            'overlapping_edges': [],   # 重叠边
            'overlapping_points': []   # 重叠点
        }
        
        # 最近修改的元素
        self.modified_elements = {
            "points": set(),
            "edges": set(),
            "faces": set()
        }
        
        # 标记是否需要完全重新计算
        self.need_full_recompute = True
        
        # 性能统计
        self.performance_stats = {
            "local_updates": 0,
            "full_updates": 0,
            "time_saved": 0
        }
        
        # 存储每次分析的耗时
        self.last_analysis_times = {}
    
    def initialize_cache(self):
        """初始化缓存，完整分析整个模型"""
        start_time = time.time()
        
        # 获取当前模型所有点线面
        self._cache_model_topology()
        
        # 计算所有分析项的初始值
        self._compute_full_analysis()
        
        self.need_full_recompute = False
        end_time = time.time()
        print(f"初始化缓存完成，耗时: {end_time - start_time:.2f}秒")
    
    def _cache_model_topology(self):
        """缓存模型拓扑结构"""
        # 重置缓存
        self.cached_model_state = {
            "points": set(),
            "edges": set(),
            "faces": set(),
            "face_connections": {},
            "point_connections": {},
            "edge_connections": {}
        }
        
        # 获取模型数据
        mesh_data = self.mesh_viewer.mesh_data
        
        # 缓存点 - 处理mesh_data['vertices']是numpy数组的情况
        if 'vertices' in mesh_data:
            # 缓存所有点ID
            for point_id in range(len(mesh_data['vertices'])):
                self.cached_model_state["points"].add(point_id)
                self.cached_model_state["point_connections"][point_id] = {
                    "points": set(),
                    "edges": set(),
                    "faces": set()
                }
        
        # 缓存边 - 如果存在边数据
        if 'edges' in mesh_data:
            if isinstance(mesh_data['edges'], dict):
                # 如果edges是字典格式
                for edge_id, edge_data in mesh_data['edges'].items():
                    self.cached_model_state["edges"].add(edge_id)
                    self.cached_model_state["edge_connections"][edge_id] = {
                        "points": set([edge_data.get("start_point"), edge_data.get("end_point")]),
                        "edges": set(),
                        "faces": set()
                    }
                    
                    # 更新点的连接
                    for point_id in self.cached_model_state["edge_connections"][edge_id]["points"]:
                        if point_id in self.cached_model_state["point_connections"]:
                            self.cached_model_state["point_connections"][point_id]["edges"].add(edge_id)
            else:
                # 如果edges是数组格式 - 这里假设每行表示一个边，前两个元素是起点和终点
                for edge_id, edge in enumerate(mesh_data['edges']):
                    start_point, end_point = edge[0], edge[1]  # 假设边定义为[start_id, end_id]
                    self.cached_model_state["edges"].add(edge_id)
                    self.cached_model_state["edge_connections"][edge_id] = {
                        "points": set([start_point, end_point]),
                        "edges": set(),
                        "faces": set()
                    }
                    
                    # 更新点的连接
                    for point_id in [start_point, end_point]:
                        if point_id in self.cached_model_state["point_connections"]:
                            self.cached_model_state["point_connections"][point_id]["edges"].add(edge_id)
        
        # 缓存面 - 处理mesh_data['faces']是numpy数组的情况
        if 'faces' in mesh_data:
            # 如果faces是numpy数组
            for face_id in range(len(mesh_data['faces'])):
                face = mesh_data['faces'][face_id]  # 获取面的顶点索引
                
                self.cached_model_state["faces"].add(face_id)
                face_points = set(face)  # 面的顶点索引集合
                
                # 确定相关的边
                # 注意：我们可能没有显式的边定义，需要从面的点推断
                face_edges = set()
                
                # 将面信息存入缓存
                self.cached_model_state["face_connections"][face_id] = {
                    "points": face_points,
                    "edges": face_edges,
                    "faces": set()
                }
                
                # 更新点的连接
                for point_id in face_points:
                    if point_id in self.cached_model_state["point_connections"]:
                        self.cached_model_state["point_connections"][point_id]["faces"].add(face_id)
        
        # 计算相邻面 - 通过共享点来推断
        for face_id, face_conn in self.cached_model_state["face_connections"].items():
            for point_id in face_conn["points"]:
                if point_id in self.cached_model_state["point_connections"]:
                    for other_face_id in self.cached_model_state["point_connections"][point_id]["faces"]:
                        if other_face_id != face_id:
                            face_conn["faces"].add(other_face_id)
    
    def _compute_full_analysis(self):
        """计算完整分析结果"""
        # 调用mesh_viewer中的分析方法，并保存完整结果
        intersections = self._analyze_face_intersections()
        
        # 面质量分析 - 仅在用户初始化后执行
        quality_faces = []
        if hasattr(self.mesh_viewer, 'face_quality_initialized') and self.mesh_viewer.face_quality_initialized:
            quality_faces = self._analyze_face_quality()
            print("正在执行面质量分析（已初始化）...")
        else:
            print("跳过面质量分析（未初始化）...")
        
        free_edges = self._count_free_edges()
        overlapping_edges = self._count_overlapping_edges()
        overlapping_points = self._count_overlapping_points()
        
        # 相邻面分析 - 仅在用户初始化后执行
        adjacent_faces = []
        if hasattr(self.mesh_viewer, 'adjacent_faces_initialized') and self.mesh_viewer.adjacent_faces_initialized:
            adjacent_faces = self._analyze_adjacent_faces()
            print("正在执行相邻面分析（已初始化）...")
        else:
            print("跳过相邻面分析（未初始化）...")
        
        # 更新缓存的按钮计数
        self.cached_button_counts = {
            "交叉面": len(intersections),
            "面质量": len(quality_faces),
            "相邻面": len(adjacent_faces),
            "自由边": len(free_edges),
            "重叠边": len(overlapping_edges),
            "重叠点": len(overlapping_points)
        }
        
        # 更新检测结果缓存
        self.detection_results = {
            'face_intersections': intersections,
            'face_quality': quality_faces,
            'adjacent_faces': adjacent_faces,
            'free_edges': free_edges,
            'overlapping_edges': overlapping_edges,
            'overlapping_points': overlapping_points
        }
        
        # 同步到mesh_viewer的检测缓存
        self._sync_detection_cache()
    
    def track_modification(self, element_type, element_ids):
        """跟踪模型修改
        
        Args:
            element_type: 元素类型 ('points', 'edges', 'faces')
            element_ids: 修改的元素ID列表或集合
        """
        if not element_ids:
            return
        
        # 添加到修改集
        self.modified_elements[element_type].update(element_ids)
        
        # 如果修改了太多元素，标记需要完全重新计算
        if (len(self.modified_elements["points"]) > len(self.cached_model_state["points"]) * 0.1 or
            len(self.modified_elements["edges"]) > len(self.cached_model_state["edges"]) * 0.1 or
            len(self.modified_elements["faces"]) > len(self.cached_model_state["faces"]) * 0.1):
            self.need_full_recompute = True
    
    def get_affected_area(self):
        """获取受影响区域（直接修改的元素及其连接的元素）"""
        if self.need_full_recompute:
            return {
                "points": self.cached_model_state["points"].copy(),
                "edges": self.cached_model_state["edges"].copy(),
                "faces": self.cached_model_state["faces"].copy()
            }
        
        affected_area = {
            "points": self.modified_elements["points"].copy(),
            "edges": self.modified_elements["edges"].copy(),
            "faces": self.modified_elements["faces"].copy()
        }
        
        # 扩展到相连元素
        self._expand_affected_area(affected_area)
        
        return affected_area
    
    def _expand_affected_area(self, affected_area):
        """扩展受影响区域到相连元素"""
        # 临时存储扩展的元素
        expanded_points = set()
        expanded_edges = set()
        expanded_faces = set()
        
        # 从点扩展
        for point_id in affected_area["points"]:
            if point_id in self.cached_model_state["point_connections"]:
                conn = self.cached_model_state["point_connections"][point_id]
                expanded_points.update(conn["points"])
                expanded_edges.update(conn["edges"])
                expanded_faces.update(conn["faces"])
        
        # 从边扩展
        for edge_id in affected_area["edges"]:
            if edge_id in self.cached_model_state["edge_connections"]:
                conn = self.cached_model_state["edge_connections"][edge_id]
                expanded_points.update(conn["points"])
                expanded_edges.update(conn["edges"])
                expanded_faces.update(conn["faces"])
        
        # 从面扩展
        for face_id in affected_area["faces"]:
            if face_id in self.cached_model_state["face_connections"]:
                conn = self.cached_model_state["face_connections"][face_id]
                expanded_points.update(conn["points"])
                expanded_edges.update(conn["edges"])
                expanded_faces.update(conn["faces"])
        
        # 更新受影响区域
        affected_area["points"].update(expanded_points)
        affected_area["edges"].update(expanded_edges)
        affected_area["faces"].update(expanded_faces)
    
    def update_analysis(self):
        """更新分析结果"""
        start_time = time.time()
        
        if self.need_full_recompute:
            # 获取原始按钮值
            old_counts = self.cached_button_counts.copy()
            
            # 执行完整重新计算
            self._cache_model_topology()
            self._compute_full_analysis()
            
            # 更新性能统计
            self.performance_stats["full_updates"] += 1
            
            # 重置修改跟踪
            self.modified_elements = {"points": set(), "edges": set(), "faces": set()}
            self.need_full_recompute = False
            
            end_time = time.time()
            print(f"完整更新分析，耗时: {end_time - start_time:.2f}秒")
            
            # 返回新旧按钮值的差异 (需要处理字符串类型)
            updates = {}
            for key in self.cached_button_counts:
                new_val = self.cached_button_counts[key]
                old_val = old_counts.get(key, 0)
                # 如果值是字符串 (即"未分析")，则差值为0
                if isinstance(new_val, str) or isinstance(old_val, str):
                    updates[key] = 0
                else:
                    updates[key] = new_val - old_val
            return updates
        else:
            # 获取原始按钮值
            old_counts = self.cached_button_counts.copy()
            
            # 获取受影响区域
            affected_area = self.get_affected_area()
            
            # 更新拓扑缓存 (局部)
            self._update_topology_cache(affected_area)
            
            # 增量更新分析结果
            self._update_analysis_incrementally(affected_area)
            
            # 更新性能统计
            self.performance_stats["local_updates"] += 1
            
            # 重置修改跟踪
            self.modified_elements = {"points": set(), "edges": set(), "faces": set()}
            
            end_time = time.time()
            print(f"局部更新分析，耗时: {end_time - start_time:.2f}秒")
            
            # 估算节省的时间
            estimated_full_time = len(self.cached_model_state["faces"]) / max(1, len(affected_area["faces"])) * (end_time - start_time)
            self.performance_stats["time_saved"] += max(0, estimated_full_time - (end_time - start_time))
            
            # 返回新旧按钮值的差异 (需要处理字符串类型)
            updates = {}
            for key in self.cached_button_counts:
                new_val = self.cached_button_counts[key]
                old_val = old_counts.get(key, 0)
                # 如果值是字符串 (即"未分析")，则差值为0
                if isinstance(new_val, str) or isinstance(old_val, str):
                    updates[key] = 0
                else:
                    updates[key] = new_val - old_val
            return updates
    
    def _update_topology_cache(self, affected_area):
        """更新拓扑缓存中的受影响区域"""
        mesh_data = self.mesh_viewer.mesh_data
        
        # 移除不再存在的元素
        for point_id in list(affected_area["points"]):
            if 'vertices' in mesh_data and point_id >= len(mesh_data['vertices']):
                if point_id in self.cached_model_state["points"]:
                    self.cached_model_state["points"].remove(point_id)
                if point_id in self.cached_model_state["point_connections"]:
                    del self.cached_model_state["point_connections"][point_id]
        
        for edge_id in list(affected_area["edges"]):
            if 'edges' in mesh_data:
                if isinstance(mesh_data['edges'], dict) and edge_id not in mesh_data['edges']:
                    if edge_id in self.cached_model_state["edges"]:
                        self.cached_model_state["edges"].remove(edge_id)
                    if edge_id in self.cached_model_state["edge_connections"]:
                        del self.cached_model_state["edge_connections"][edge_id]
                elif not isinstance(mesh_data['edges'], dict) and edge_id >= len(mesh_data['edges']):
                    if edge_id in self.cached_model_state["edges"]:
                        self.cached_model_state["edges"].remove(edge_id)
                    if edge_id in self.cached_model_state["edge_connections"]:
                        del self.cached_model_state["edge_connections"][edge_id]
        
        for face_id in list(affected_area["faces"]):
            if 'faces' in mesh_data and face_id >= len(mesh_data['faces']):
                if face_id in self.cached_model_state["faces"]:
                    self.cached_model_state["faces"].remove(face_id)
                if face_id in self.cached_model_state["face_connections"]:
                    del self.cached_model_state["face_connections"][face_id]
        
        # 更新或添加受影响区域内的元素
        # 更新点
        for point_id in affected_area["points"]:
            if 'vertices' in mesh_data and point_id < len(mesh_data['vertices']):
                if point_id not in self.cached_model_state["points"]:
                    self.cached_model_state["points"].add(point_id)
                
                self.cached_model_state["point_connections"][point_id] = {
                    "points": set(),
                    "edges": set(),
                    "faces": set()
                }
        
        # 更新边
        if 'edges' in mesh_data:
            for edge_id in affected_area["edges"]:
                if isinstance(mesh_data['edges'], dict) and edge_id in mesh_data['edges']:
                    edge_data = mesh_data['edges'][edge_id]
                    
                    if edge_id not in self.cached_model_state["edges"]:
                        self.cached_model_state["edges"].add(edge_id)
                    
                    self.cached_model_state["edge_connections"][edge_id] = {
                        "points": set([edge_data.get("start_point"), edge_data.get("end_point")]),
                        "edges": set(),
                        "faces": set()
                    }
                    
                    # 更新点的连接
                    for point_id in self.cached_model_state["edge_connections"][edge_id]["points"]:
                        if point_id in self.cached_model_state["point_connections"]:
                            self.cached_model_state["point_connections"][point_id]["edges"].add(edge_id)
                            
                elif not isinstance(mesh_data['edges'], dict) and edge_id < len(mesh_data['edges']):
                    edge = mesh_data['edges'][edge_id]
                    
                    if edge_id not in self.cached_model_state["edges"]:
                        self.cached_model_state["edges"].add(edge_id)
                    
                    start_point, end_point = edge[0], edge[1]  # 假设边定义为[start_id, end_id]
                    self.cached_model_state["edge_connections"][edge_id] = {
                        "points": set([start_point, end_point]),
                        "edges": set(),
                        "faces": set()
                    }
                    
                    # 更新点的连接
                    for point_id in [start_point, end_point]:
                        if point_id in self.cached_model_state["point_connections"]:
                            self.cached_model_state["point_connections"][point_id]["edges"].add(edge_id)
        
        # 更新面
        for face_id in affected_area["faces"]:
            if 'faces' in mesh_data and face_id < len(mesh_data['faces']):
                face = mesh_data['faces'][face_id]  # 获取面的点索引数组
                
                if face_id not in self.cached_model_state["faces"]:
                    self.cached_model_state["faces"].add(face_id)
                
                face_points = set(face)  # 面的顶点索引集合
                face_edges = set()  # 从面的点推断边
                
                self.cached_model_state["face_connections"][face_id] = {
                    "points": face_points,
                    "edges": face_edges,
                    "faces": set()
                }
                
                # 更新点和边的连接
                for point_id in face_points:
                    if point_id in self.cached_model_state["point_connections"]:
                        self.cached_model_state["point_connections"][point_id]["faces"].add(face_id)
        
        # 更新相邻面关系 - 通过共享点来推断
        for face_id in affected_area["faces"]:
            if face_id in self.cached_model_state["face_connections"]:
                face_conn = self.cached_model_state["face_connections"][face_id]
                face_conn["faces"] = set()  # 重置相邻面
                
                for point_id in face_conn["points"]:
                    if point_id in self.cached_model_state["point_connections"]:
                        for other_face_id in self.cached_model_state["point_connections"][point_id]["faces"]:
                            if other_face_id != face_id:
                                face_conn["faces"].add(other_face_id)
    
    def _update_analysis_incrementally(self, affected_area):
        """增量更新分析结果"""
        # 重新计算受影响区域的分析结果
        intersections = self._analyze_face_intersections(affected_area)
        
        # 面质量分析 - 仅在用户初始化后执行
        quality_faces = []
        if hasattr(self.mesh_viewer, 'face_quality_initialized') and self.mesh_viewer.face_quality_initialized:
            quality_faces = self._analyze_face_quality(affected_area)
            print("正在执行面质量局部分析（已初始化）...")
        else:
            print("跳过面质量局部分析（未初始化）...")
        
        free_edges = self._count_free_edges(affected_area)
        overlapping_edges = self._count_overlapping_edges(affected_area)
        overlapping_points = self._count_overlapping_points(affected_area)
        
        # 相邻面分析 - 仅在用户初始化后执行
        adjacent_faces_result = None
        if hasattr(self.mesh_viewer, 'adjacent_faces_initialized') and self.mesh_viewer.adjacent_faces_initialized:
            adjacent_faces_result = self._analyze_adjacent_faces(affected_area)
            print("正在执行相邻面局部分析（已初始化）...")
        else:
            print("跳过相邻面局部分析（未初始化）...")
        
        # --- 更新缓存 --- 
        # 先保留旧计数，以防某些分析未执行
        old_counts = self.cached_button_counts.copy()
        old_results = self.detection_results.copy()
        
        # 根据新计算的结果更新
        new_counts = {
            "交叉面": len(intersections),
            # 面质量: 如果未初始化，则不存储数字，以便UI处理时能显示"未分析"而不是0
            "面质量": len(quality_faces) if hasattr(self.mesh_viewer, 'face_quality_initialized') and self.mesh_viewer.face_quality_initialized else "",
            # "相邻面": 先不更新，下面单独处理
            "自由边": len(free_edges), 
            "重叠边": len(overlapping_edges),
            "重叠点": len(overlapping_points)
        }
        new_results = {
            'face_intersections': intersections,
            'face_quality': quality_faces,
            # 'adjacent_faces': 先不更新
            'free_edges': free_edges,
            'overlapping_edges': overlapping_edges,
            'overlapping_points': overlapping_points
        }
        
        # 单独处理相邻面结果
        if adjacent_faces_result is not None: # 只有当分析实际执行时才更新
             new_counts["相邻面"] = len(adjacent_faces_result)
             new_results['adjacent_faces'] = adjacent_faces_result
        else: # 如果分析未执行 (例如缺阈值或未初始化)，保留旧值或设为0
            if hasattr(self.mesh_viewer, 'adjacent_faces_initialized') and self.mesh_viewer.adjacent_faces_initialized:
                # 如果已初始化但分析失败，保留旧值
                new_counts["相邻面"] = old_counts.get("相邻面", 0)
                new_results['adjacent_faces'] = old_results.get('adjacent_faces', [])
            else:
                # 如果未初始化，设为空字符串，使UI能显示"未分析"
                new_counts["相邻面"] = ""
                new_results['adjacent_faces'] = []
            
        # 应用更新
        self.cached_button_counts = new_counts
        self.detection_results = new_results
        
        # 同步到mesh_viewer的检测缓存
        self._sync_detection_cache()
    
    def _sync_detection_cache(self):
        """将检测结果同步到mesh_viewer的缓存中"""
        if hasattr(self.mesh_viewer, 'detection_cache'):
            self.mesh_viewer.detection_cache['face_intersections'] = self.detection_results['face_intersections']
            self.mesh_viewer.detection_cache['face_quality'] = self.detection_results['face_quality']
            self.mesh_viewer.detection_cache['adjacent_faces'] = self.detection_results['adjacent_faces']  
            self.mesh_viewer.detection_cache['free_edges'] = self.detection_results['free_edges']
            self.mesh_viewer.detection_cache['overlapping_edges'] = self.detection_results['overlapping_edges']
            self.mesh_viewer.detection_cache['overlapping_points'] = self.detection_results['overlapping_points']
    
    # 各种分析功能的实现
    def _analyze_face_intersections(self, affected_area=None):
        """分析面片交叉问题"""
        if affected_area is None:
            # 如果是全局分析，使用mesh_viewer的功能
            try:
                result = self.mesh_viewer.run_silent_detection(
                    self.mesh_viewer.detect_face_intersections,
                    "交叉面"
                )
                return result if result else []
            except Exception as e:
                print(f"错误: 全局交叉面分析失败: {str(e)}")
                return []
        else:
            # 检查 C++ 模块
            try:
                import pierced_faces_cpp
                has_cpp = True
            except ImportError:
                print("错误：未找到 pierced_faces_cpp 模块，无法执行交叉面分析。")
                return []
                
            # 只检查受影响区域内的面
            algorithm = CombinedIntersectionAlgorithm(self.mesh_viewer.mesh_data, detection_mode="pierced")
            algorithm.use_cpp = has_cpp
            algorithm.target_faces = affected_area["faces"]
            algorithm.enhanced_cpp_available = hasattr(self.mesh_viewer, 'has_enhanced_pierced_faces') and self.mesh_viewer.has_enhanced_pierced_faces

            # 传递 parent=None 以抑制对话框
            result = algorithm.execute(parent=None)
            return result.get('selected_faces', []) if result else []
    
    def _analyze_face_quality(self, affected_area=None):
        """分析面质量问题 (强制使用C++) """
        # 检查 C++ 模块
        try:
            import face_quality_cpp
            has_cpp = True
        except ImportError:
            print("错误：未找到 face_quality_cpp 模块，无法执行面质量分析。")
            return [] # 返回空列表表示失败

        # 创建算法实例并强制使用 C++
        algorithm = FaceQualityAlgorithm(self.mesh_viewer.mesh_data)
        algorithm.use_cpp = True # 强制使用C++
        # 如果提供了 affected_area，限制目标面
        if affected_area and 'faces' in affected_area:
            algorithm.target_faces = affected_area["faces"]
        threshold = getattr(self.mesh_viewer, 'face_quality_threshold', 0.3)
        if not threshold: return [] # 如果没有有效阈值，直接返回

        # 传递 parent=None 以抑制对话框
        result = algorithm.execute(parent=None)
        return result.get('selected_faces', []) if result else []
    
    def _count_free_edges(self, affected_area=None):
        """统计自由边并返回自由边列表 (强制使用C++) """
        # 检查 C++ 模块
        try:
            import free_edges_cpp # 假设 C++ 模块名为 free_edges_cpp
            has_cpp = True
        except ImportError:
            print("错误：未找到 free_edges_cpp 模块，无法执行自由边检测。")
            return []
            
        algorithm = FreeEdgesAlgorithm(self.mesh_viewer.mesh_data)
        algorithm.use_cpp = True # 强制使用C++
        # 如果提供了affected_area，限制目标边
        if affected_area and 'edges' in affected_area:
             algorithm.target_edges = affected_area["edges"]
        else: # 否则处理所有边 (全量分析)
            algorithm.target_edges = None # 或者不设置，取决于算法默认行为

        # 传递 parent=None 以抑制对话框
        result = algorithm.execute(parent=None)
        return result.get('selected_edges', []) if result else []
    
    def _count_overlapping_edges(self, affected_area=None):
        """统计重叠边并返回重叠边列表 (强制使用C++) """
        # 检查 C++ 模块
        try:
            import overlapping_edges_cpp  # 假设 C++ 模块名为 overlapping_edges_cpp
            has_cpp = True
        except ImportError:
            print("错误：未找到 overlapping_edges_cpp 模块，无法执行重叠边检测。")
            return []
            
        # 创建算法实例
        algorithm = OverlappingEdgesAlgorithm(self.mesh_viewer.mesh_data)
        algorithm.use_cpp = True  # 强制使用C++
        
        # 如果提供了affected_area，限制目标边
        if affected_area and 'edges' in affected_area:
            algorithm.target_edges = affected_area["edges"]
        else:  # 否则处理所有边 (全量分析)
            algorithm.target_edges = None  # 或者不设置，取决于算法默认行为
            
        # 执行算法
        # 传递 parent=None 以抑制对话框
        result = algorithm.execute(parent=None)
        return result.get('selected_edges', []) if result else []
    
    def _count_overlapping_points(self, affected_area=None):
        """统计重叠点并返回重叠点列表 (强制使用C++) """
        start_time = time.time()  # 记录开始时间
        selected_points = []  # 初始化结果列表
        
        # 检查 C++ 模块
        try:
            # 优先检查 non_manifold_vertices_cpp
            import non_manifold_vertices_cpp
            cpp_module_name = "non_manifold_vertices_cpp"
        except ImportError:
            try:
                # 其次检查 overlapping_points_cpp
                import overlapping_points_cpp
                cpp_module_name = "overlapping_points_cpp"
            except ImportError:
                print("错误：未找到 non_manifold_vertices_cpp 或 overlapping_points_cpp 模块，无法执行重叠点检测。")
                self.last_analysis_times['重叠点'] = time.time() - start_time  # 记录耗时 (即使失败)
                return []
        
        # 使用合并后的顶点检测算法，并强制使用C++
        algorithm = MergedVertexDetectionAlgorithm(self.mesh_viewer.mesh_data, detection_mode="overlapping")
        algorithm.use_cpp = True  # 强制使用C++
        
        # 如果提供了affected_area，限制目标点
        if affected_area and 'points' in affected_area:
            algorithm.target_vertices = affected_area["points"]
        else:
            algorithm.target_vertices = None
            
        # 执行算法
        # 传递 parent=None 以抑制对话框
        result = algorithm.execute(parent=None)
        
        # 从结果中提取重叠点
        if 'selected_points' in result and result['selected_points']:
            selected_points = result['selected_points']
        
        end_time = time.time()  # 记录结束时间
        self.last_analysis_times['重叠点'] = end_time - start_time  # 存储耗时
        return selected_points
    
    def _analyze_adjacent_faces(self, affected_area=None):
        """分析面片邻近性 (目前总是执行完整分析)"""
        start_time = time.time()
        selected_faces = []
        execution_time_cpp = 0 # C++内部执行时间
        
        # 从viewer获取阈值
        threshold = getattr(self.mesh_viewer, 'adjacent_faces_threshold', None)
        
        if threshold is None:
            print("警告：未设置相邻面阈值，跳过分析。")
            self.last_analysis_times['Adjacent Faces'] = time.time() - start_time
            return None # 返回 None 表示分析未执行
            
        # 检查mesh_data是否有效
        if not self.mesh_viewer.mesh_data or 'vertices' not in self.mesh_viewer.mesh_data or 'faces' not in self.mesh_viewer.mesh_data:
            print("警告：无效的网格数据，跳过相邻面分析。")
            self.last_analysis_times['Adjacent Faces'] = time.time() - start_time
            return None # 返回 None 表示分析未执行
            
        # 检查顶点和面片数据
        if len(self.mesh_viewer.mesh_data['vertices']) == 0 or len(self.mesh_viewer.mesh_data['faces']) == 0:
            print("警告：模型没有顶点或面片数据，跳过相邻面分析。")
            self.last_analysis_times['Adjacent Faces'] = time.time() - start_time
            return None # 返回 None 表示分析未执行
            
        try:
            # 尝试导入C++模块
            import adjacent_faces_cpp
            print("使用C++模块进行相邻面分析")
            
            # 准备数据
            vertices_np = np.array(self.mesh_viewer.mesh_data['vertices'], dtype=np.float32)
            faces_np = np.array(self.mesh_viewer.mesh_data['faces'], dtype=np.int32)
            
            # 调用C++函数 (总是进行全量分析)
            adjacent_pairs, execution_time_cpp = adjacent_faces_cpp.detect_adjacent_faces_with_timing(
                vertices_np, faces_np, proximity_threshold=float(threshold)
            )
            
            # 处理结果
            face_set = set()
            if adjacent_pairs is not None:
                for pair in adjacent_pairs:
                    if isinstance(pair, (tuple, list)) and len(pair) == 2:
                        i, j = pair
                        face_set.add(int(i))
                        face_set.add(int(j))
                    else:
                        print(f"警告: 意外的相邻对格式: {type(pair)}")
            selected_faces = list(face_set)
            print(f"相邻面分析完成 (C++): 找到 {len(selected_faces)} 个面, C++耗时 {execution_time_cpp:.4f}秒")

        except ImportError:
            print("错误：未找到 adjacent_faces_cpp 模块，无法执行相邻面分析。")
            # 这里可以添加Python后备实现，但目前省略
        except Exception as e:
            print(f"错误：相邻面分析失败: {str(e)}\n{traceback.format_exc()}")
            # 分析失败也返回 None，以保留旧计数
            selected_faces = None
            
        end_time = time.time()
        total_time = end_time - start_time
        self.last_analysis_times['Adjacent Faces'] = total_time # 存储总耗时
        print(f"相邻面分析总耗时: {total_time:.4f}秒")
        return selected_faces
    
    def get_button_counts(self):
        """获取当前按钮计数"""
        return self.cached_button_counts
    
    def get_cached_results(self, analysis_type):
        """获取指定分析类型的缓存结果列表"""
        key_map = {
            "交叉面": 'face_intersections',
            "面质量": 'face_quality',
            "相邻面": 'adjacent_faces',
            "自由边": 'free_edges',
            "重叠边": 'overlapping_edges',
            "重叠点": 'overlapping_points',
            # 兼容 MeshViewerQt 中的调用
            "Adjacent Faces": 'adjacent_faces' 
        }
        internal_key = key_map.get(analysis_type)
        if internal_key:
            return self.detection_results.get(internal_key, None)
        return None

    def run_analysis_for_button(self, analysis_type, **kwargs):
        """手动触发指定按钮的分析"""
        start_time = time.time()
        result_list = []
        analysis_key = None # 用于存储 self.last_analysis_times 的键
        
        # 映射按钮名称到内部方法和结果键
        analysis_map = {
            "交叉面": (self._analyze_face_intersections, 'face_intersections'),
            "面质量": (self._analyze_face_quality, 'face_quality'),
            "相邻面": (self._analyze_adjacent_faces, 'adjacent_faces'),
            "自由边": (self._count_free_edges, 'free_edges'),
            "重叠边": (self._count_overlapping_edges, 'overlapping_edges'),
            "重叠点": (self._count_overlapping_points, 'overlapping_points'),
            # 兼容 MeshViewerQt 中的调用
            "Adjacent Faces": (self._analyze_adjacent_faces, 'adjacent_faces'),
        }

        if analysis_type in analysis_map:
            analysis_func, result_key = analysis_map[analysis_type]
            analysis_key = analysis_type # 使用按钮名称作为耗时记录的键
            
            # 特殊处理需要参数的分析 (例如相邻面阈值)
            if analysis_type in ["相邻面", "Adjacent Faces"]:
                threshold = kwargs.get('threshold', getattr(self.mesh_viewer, 'adjacent_faces_threshold', None))
                if threshold is not None:
                    # 更新阈值并执行分析
                    self.mesh_viewer.adjacent_faces_threshold = threshold
                    print(f"执行 {analysis_type} 分析，阈值: {threshold}")
                    result_list = analysis_func() # 调用对应的分析方法
                else:
                    print(f"警告：运行 {analysis_type} 分析缺少阈值。")
            elif analysis_type == "面质量":
                 threshold = kwargs.get('threshold', 0.3) # 获取阈值，默认0.3
                 # 注意: _analyze_face_quality 目前不支持直接传递阈值，需要修改
                 print(f"执行 {analysis_type} 分析，阈值: {threshold}")
                 # 需要修改 _analyze_face_quality 以接受阈值参数
                 result_list = analysis_func() # 调用分析方法 (需要修改才能使用kwargs中的阈值)
            else:
                # 其他分析直接调用
                print(f"执行 {analysis_type} 分析")
                result_list = analysis_func() # 调用对应的分析方法

            # 更新缓存
            if result_key:
                self.detection_results[result_key] = result_list
                # 更新对应的按钮计数
                if analysis_type in self.cached_button_counts:
                     self.cached_button_counts[analysis_type] = len(result_list)
                # 如果是 Adjacent Faces，也更新中文键
                if analysis_type == "Adjacent Faces":
                    self.cached_button_counts["相邻面"] = len(result_list)
                    
            # 同步到 viewer 的缓存
            self._sync_detection_cache()
            
            # 更新界面显示 (假设viewer有update_button_display方法)
            if hasattr(self.mesh_viewer, 'update_button_display'):
                 self.mesh_viewer.update_button_display()
                 
        else:
            print(f"错误：未知的分析类型 '{analysis_type}'")
            
        end_time = time.time()
        # 记录本次按钮触发的分析耗时
        if analysis_key:
             self.last_analysis_times[analysis_key + "_button_triggered"] = end_time - start_time
        print(f"按钮触发分析 '{analysis_type}' 完成，耗时: {end_time - start_time:.4f}秒")
    
    def get_performance_stats(self):
        """获取性能统计信息"""
        return self.performance_stats 
        
    def get_last_analysis_time(self, analysis_type):
        """获取指定分析类型最后一次的执行时间"""
        # 映射 viewer 调用时使用的键到内部存储的键
        key_map = {
            "Adjacent Faces": "Adjacent Faces" # 保持一致，或映射到中文键？
            # ... 其他映射 ...
        }
        internal_key = key_map.get(analysis_type, analysis_type)
        return self.last_analysis_times.get(internal_key, 0.0) 