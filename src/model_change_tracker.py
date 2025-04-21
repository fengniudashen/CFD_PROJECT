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
        quality_faces = self._analyze_face_quality()
        free_edges = self._count_free_edges()
        overlapping_edges = self._count_overlapping_edges()
        overlapping_points = self._count_overlapping_points()
        
        # 更新缓存的按钮计数
        self.cached_button_counts = {
            "交叉面": len(intersections),
            "面质量": len(quality_faces),
            "相邻面": 0,  # 相邻面不存储数量，只在选择时使用
            "自由边": len(free_edges),
            "重叠边": len(overlapping_edges),
            "重叠点": len(overlapping_points)
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
            
            # 返回新旧按钮值的差异
            return {key: self.cached_button_counts[key] - old_counts[key] for key in self.cached_button_counts}
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
            
            # 返回新旧按钮值的差异
            return {key: self.cached_button_counts[key] - old_counts[key] for key in self.cached_button_counts}
    
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
        quality_faces = self._analyze_face_quality(affected_area)
        free_edges = self._count_free_edges(affected_area)
        overlapping_edges = self._count_overlapping_edges(affected_area)
        overlapping_points = self._count_overlapping_points(affected_area)
        
        # 更新缓存的按钮计数和检测结果
        self.cached_button_counts = {
            "交叉面": len(intersections),
            "面质量": len(quality_faces),
            "相邻面": 0,  # 相邻面不存储数量
            "自由边": len(free_edges), 
            "重叠边": len(overlapping_edges),
            "重叠点": len(overlapping_points)
        }
        
        # 更新检测结果缓存
        self.detection_results = {
            'face_intersections': intersections,
            'face_quality': quality_faces,
            'adjacent_faces': [],  # 相邻面不缓存
            'free_edges': free_edges,
            'overlapping_edges': overlapping_edges,
            'overlapping_points': overlapping_points
        }
        
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
            result = self.mesh_viewer.run_silent_detection(
                self.mesh_viewer.detect_face_intersections,
                "交叉面"
            )
            return result if result else []
        else:
            # 尝试导入并使用C++模块
            try:
                import pierced_faces_cpp
                has_cpp = True
            except ImportError:
                has_cpp = False
                
            # 只检查受影响区域内的面
            algorithm = CombinedIntersectionAlgorithm(self.mesh_viewer.mesh_data, detection_mode="pierced")
            # 设置使用C++
            algorithm.use_cpp = has_cpp
            # 限制只检测受影响区域的面
            algorithm.target_faces = affected_area["faces"]
            result = algorithm.execute(parent=None)
            return result.get('selected_faces', []) if result else []
    
    def _analyze_face_quality(self, affected_area=None):
        """分析面质量问题"""
        if affected_area is None:
            result = self.mesh_viewer.run_silent_detection(
                self.mesh_viewer.analyze_face_quality,
                "面质量"
            )
            return result if result else []
        else:
            # 尝试导入并使用C++模块
            try:
                import face_quality_cpp
                has_cpp = True
            except ImportError:
                has_cpp = False
            
            # 创建算法实例
            algorithm = FaceQualityAlgorithm(self.mesh_viewer.mesh_data)
            algorithm.use_cpp = has_cpp
            algorithm.target_faces = affected_area["faces"]
            result = algorithm.execute(parent=None)
            return result.get('selected_faces', []) if result else []
    
    def _count_free_edges(self, affected_area=None):
        """统计自由边并返回自由边列表"""
        if affected_area is None:
            result = self.mesh_viewer.run_silent_detection(
                self.mesh_viewer.select_free_edges,
                "自由边"
            )
            return result if result else []
        else:
            # 尝试导入并使用C++模块
            try:
                import free_edges_cpp
                has_cpp = True
            except ImportError:
                has_cpp = False
                
            algorithm = FreeEdgesAlgorithm(self.mesh_viewer.mesh_data)
            algorithm.use_cpp = has_cpp
            algorithm.target_edges = affected_area["edges"]
            result = algorithm.execute(parent=None)
            return result.get('selected_edges', []) if result else []
    
    def _count_overlapping_edges(self, affected_area=None):
        """统计重叠边并返回重叠边列表"""
        if affected_area is None:
            result = self.mesh_viewer.run_silent_detection(
                self.mesh_viewer.select_overlapping_edges,
                "重叠边"
            )
            return result if result else []
        else:
            # 尝试导入并使用C++模块
            try:
                import overlapping_edges_cpp
                has_cpp = True
            except ImportError:
                has_cpp = False
                
            algorithm = OverlappingEdgesAlgorithm(self.mesh_viewer.mesh_data)
            algorithm.use_cpp = has_cpp
            algorithm.target_edges = affected_area["edges"]
            result = algorithm.execute(parent=None)
            return result.get('selected_edges', []) if result else []
    
    def _count_overlapping_points(self, affected_area=None):
        """统计重叠点并返回重叠点列表"""
        if affected_area is None:
            result = self.mesh_viewer.run_silent_detection(
                self.mesh_viewer.select_overlapping_points,
                "重叠点"
            )
            return result if result else []
        else:
            # 检查可用的C++模块
            has_cpp = False
            try:
                import non_manifold_vertices_cpp
                has_cpp = True
            except ImportError:
                try:
                    import overlapping_points_cpp
                    has_cpp = True
                except ImportError:
                    has_cpp = False
            
            # 使用合并的顶点检测算法
            from algorithms.merged_vertex_detection_algorithm import MergedVertexDetectionAlgorithm
            algorithm = MergedVertexDetectionAlgorithm(self.mesh_viewer.mesh_data, detection_mode="overlapping")
            algorithm.use_cpp = has_cpp
            algorithm.target_vertices = affected_area["points"]
            result = algorithm.execute(parent=None)
            
            # 从结果中提取重叠点
            if 'selected_points' in result and result['selected_points']:
                # 确保mesh_data中也有相同的结果
                self.mesh_viewer.mesh_data['non_manifold_vertices'] = result['selected_points']
                return result['selected_points']
            else:
                return []
    
    def get_button_counts(self):
        """获取当前按钮计数"""
        return self.cached_button_counts
    
    def get_performance_stats(self):
        """获取性能统计信息"""
        return self.performance_stats 