"""
网格相交检测算法
专注于穿刺面检测功能
"""

import numpy as np
from .base_algorithm import BaseAlgorithm
from .algorithm_utils import AlgorithmUtils
import time
import traceback
    
try:
    import pierced_faces_cpp
    HAS_PIERCED_FACES_CPP = True
except ImportError:
    HAS_PIERCED_FACES_CPP = False

class CombinedIntersectionAlgorithm(BaseAlgorithm):
    """
    网格相交检测算法类
    专注于穿刺面检测功能
    """
    
    def __init__(self, mesh_data=None, detection_mode="pierced"):
        """
        初始化网格相交检测算法
        
        参数:
        mesh_data (dict): 包含顶点和面片数据的字典
        detection_mode (str): 检测模式，目前仅支持"pierced"(穿刺面检测)
        """
        super().__init__(mesh_data)
        
        # 初始化参数
        if detection_mode != "pierced":
            print("警告: 仅支持穿刺面检测模式，已设置为默认值'pierced'")
        self.detection_mode = "pierced"
        
        # 检查是否可以使用C++模块
        self.use_cpp = HAS_PIERCED_FACES_CPP
            
        # 初始化辅助变量
        self.message_shown = False
        self.message = ""
    
        # 面相交关系映射
        self.face_intersection_map = {}
        
        # 增强版C++模块标志
        self.enhanced_cpp_available = False
        self.used_enhanced_cpp = False
    
    def execute(self, parent=None, threshold=None):
        """
        执行网格相交检测
        
        参数:
        parent: 父窗口，用于显示界面元素
        threshold: 未使用
        
        返回:
        dict: 结果字典，包含selected_faces
        """
        if not self.set_mesh_data(self.mesh_data):
            self.show_message(parent, "警告", "缺少有效的网格数据", icon="warning")
            return self.result
        
        # 修复：取消缩进，使其成为主要返回路径
        return self.detect_pierced_faces(parent)
    
    def detect_pierced_faces(self, parent=None):
        """检测穿刺面"""
        # 只有在 parent 不为 None 时才显示进度对话框
        progress = None
        if parent:
            progress = self.show_progress_dialog(parent, "穿刺面检测", "正在检测穿刺面...", 100)
        
        # 确保result是字典
        if self.result is None:
            self.result = {
                'selected_points': [],
                'selected_edges': [],
                'selected_faces': [],
                'intersection_map': {},
                'total_intersections': 0
            }
        
        start_time = time.time()
        
        try:
            # 尝试使用C++实现
            if self.use_cpp and HAS_PIERCED_FACES_CPP:
                # 检查是否是局部检测模式
                is_local_detection = hasattr(self, 'target_faces') and self.target_faces
                if is_local_detection:
                    if progress: self.update_progress(10, "使用C++算法进行局部穿刺面检测...")
                    print(f"局部检测模式: 检测 {len(self.target_faces)} 个指定面片")
                else:
                    if progress: self.update_progress(10, "使用C++算法进行全局穿刺面检测...")
                    print("全局检测模式: 检测所有面片")
                
                try:
                    # 尝试使用新版C++模块(返回相交映射)
                    if hasattr(self, 'enhanced_cpp_available') and self.enhanced_cpp_available:
                        if progress: self.update_progress(15, "使用增强版C++算法(支持相交映射)...")
                        intersecting_faces, intersection_map, detection_time = pierced_faces_cpp.detect_pierced_faces_with_timing(
                            self.faces, self.vertices)
                        
                        # 标记使用了增强版C++模块
                        self.used_enhanced_cpp = True
                        
                        # 转换C++返回的映射为Python的set格式
                        self.face_intersection_map = {int(k): set(v) for k, v in intersection_map.items()}
                        
                        # 如果是局部检测，过滤结果只保留目标面片及与其相交的面片
                        if is_local_detection:
                            if progress: self.update_progress(80, "局部检测模式: 过滤检测结果...")
                            # 创建一个新的结果集，只包含target_faces和与其相交的面片
                            filtered_faces = set()
                            filtered_map = {}
                            
                            # 添加target_faces中所有相交的面
                            for face_idx in self.target_faces:
                                if face_idx in self.face_intersection_map:
                                    filtered_faces.add(face_idx)
                                    # 保留该面的相交关系
                                    filtered_map[face_idx] = self.face_intersection_map[face_idx]
                                    # 将与该面相交的面也添加到结果集
                                    filtered_faces.update(self.face_intersection_map[face_idx])
                            
                            # 为相交的非目标面添加相交关系，但只保留与目标面的关系
                            for face_idx in filtered_faces:
                                if face_idx not in self.target_faces and face_idx in self.face_intersection_map:
                                    # 获取该面与target_faces中面的交集
                                    intersecting_with_targets = self.face_intersection_map[face_idx].intersection(self.target_faces)
                                    if intersecting_with_targets:
                                        filtered_map[face_idx] = intersecting_with_targets
                            
                            # 更新结果
                            intersecting_faces = list(filtered_faces)
                            self.face_intersection_map = filtered_map
                    else:
                        # 尝试使用增强版API，如果失败则回退
                        try:
                            if progress: self.update_progress(15, "尝试使用增强版C++算法...")
                            intersecting_faces, intersection_map, detection_time = pierced_faces_cpp.detect_pierced_faces_with_timing(
                                self.faces, self.vertices)
                            
                            # 标记使用了增强版C++模块
                            self.used_enhanced_cpp = True
                            
                            # 转换C++返回的映射为Python的set格式
                            self.face_intersection_map = {int(k): set(v) for k, v in intersection_map.items()}
                            
                            # 如果是局部检测，过滤结果只保留目标面片及与其相交的面片
                            if is_local_detection:
                                if progress: self.update_progress(80, "局部检测模式: 过滤检测结果...")
                                # 创建一个新的结果集，只包含target_faces和与其相交的面片
                                filtered_faces = set()
                                filtered_map = {}
                                
                                # 添加target_faces中所有相交的面
                                for face_idx in self.target_faces:
                                    if face_idx in self.face_intersection_map:
                                        filtered_faces.add(face_idx)
                                        # 保留该面的相交关系
                                        filtered_map[face_idx] = self.face_intersection_map[face_idx]
                                        # 将与该面相交的面也添加到结果集
                                        filtered_faces.update(self.face_intersection_map[face_idx])
                                
                                # 为相交的非目标面添加相交关系，但只保留与目标面的关系
                                for face_idx in filtered_faces:
                                    if face_idx not in self.target_faces and face_idx in self.face_intersection_map:
                                        # 获取该面与target_faces中面的交集
                                        intersecting_with_targets = self.face_intersection_map[face_idx].intersection(self.target_faces)
                                        if intersecting_with_targets:
                                            filtered_map[face_idx] = intersecting_with_targets
                                
                                # 更新结果
                                intersecting_faces = list(filtered_faces)
                                self.face_intersection_map = filtered_map
                        except ValueError:
                            # 如果是旧版C++模块，回退到只返回面片列表的版本
                            print("警告: 使用的是旧版C++模块，将进行相交关系手动计算")
                            if progress: self.update_progress(15, "使用基础版C++算法(需要构建相交映射)...")
                            all_intersecting_faces = [] # 初始化以防 try 块失败
                            detection_time = 0          # 初始化以防 try 块失败
                            try:
                                # 防止C++模块返回None或其他非预期结果
                                cpp_result = pierced_faces_cpp.detect_pierced_faces_with_timing(self.faces, self.vertices)
                                if isinstance(cpp_result, tuple) and len(cpp_result) >= 2:
                                    all_intersecting_faces, detection_time = cpp_result
                                else:
                                    print(f"警告: C++模块返回了意外格式的结果: {type(cpp_result)}")
                                    raise ValueError("C++模块返回格式不正确")
                                    
                                # 检查返回的面片列表
                                if all_intersecting_faces is None:
                                    print("警告: C++模块返回了None而不是面片列表")
                                    all_intersecting_faces = []
                            except Exception as e:
                                print(f"旧版C++模块调用失败: {e}")
                                # 出错时设置空结果 (已在try块前初始化)
                                
                            # --- 这部分逻辑现在应该在 except ValueError 内部，但在 try/except Exception 之后 ---
                            # 如果是局部检测，过滤结果只保留目标面片及相关面片
                            if is_local_detection:
                                if progress: self.update_progress(60, "局部检测模式: 过滤检测结果...")
                                # 确保 all_intersecting_faces 是列表
                                if not isinstance(all_intersecting_faces, list):
                                     all_intersecting_faces = []
                                intersecting_faces = [face_idx for face_idx in all_intersecting_faces 
                                                     if face_idx in self.target_faces]
                            else:
                                intersecting_faces = all_intersecting_faces
                            
                            # 标记未使用增强版C++模块
                            self.used_enhanced_cpp = False
                            
                            # 初始化面相交映射
                            self.face_intersection_map = {}
                            
                            # 由于C++模块当前版本不返回相交映射，我们需要重建它
                            # 这里使用一个简化的重建过程，检测不共享顶点的面之间的交叉
                            if progress: self.update_progress(70, "构建面相交映射...")
                            
                            # 确定要检查的面片
                            if not isinstance(intersecting_faces, list):
                                intersecting_faces = [] # 如果不是列表（例如 None），设置为空列表
                            faces_to_check = self.target_faces if is_local_detection else intersecting_faces
                            
                            # 对于每个检测到的相交面，找出它与哪些面相交
                            for i, face_idx in enumerate(faces_to_check):
                                if i % 10 == 0:
                                    if progress: self.update_progress(70 + int(20 * i / len(faces_to_check)), f"构建相交映射 {i+1}/{len(faces_to_check)}")
                                    
                                # 获取当前面片的顶点
                                face_i = self.faces[face_idx]
                                face_i_verts = [self.vertices[face_i[0]], self.vertices[face_i[1]], self.vertices[face_i[2]]]
                                
                                # 创建相交关系映射
                                if face_idx not in self.face_intersection_map:
                                    self.face_intersection_map[face_idx] = set()
                                    
                                # 检查与其他相交面的关系
                                for other_idx in intersecting_faces:
                                    if other_idx != face_idx:
                                        face_j = self.faces[other_idx]
                                        
                                        # 只检查不共享顶点的面
                                        if not set(face_i).intersection(set(face_j)):
                                            face_j_verts = [self.vertices[face_j[0]], self.vertices[face_j[1]], self.vertices[face_j[2]]]
                                            
                                            # 使用三角形相交检测
                                            if AlgorithmUtils.check_triangle_intersection(face_i_verts, face_j_verts):
                                                self.face_intersection_map[face_idx].add(other_idx)
                                                
                                                # 确保另一面也有映射
                                                if other_idx not in self.face_intersection_map:
                                                    self.face_intersection_map[other_idx] = set()
                                                self.face_intersection_map[other_idx].add(face_idx)
                
                # --- 外层的 except ValueError 应该在这里 ---              
                except ValueError as e:
                    # 这个异常处理的是增强版 C++ 模块检测失败的情况
                    print(f"错误: C++模块实现不一致或增强版检测失败: {e}")
                    if progress: self.update_progress(15, "C++模块出错，回退到Python算法...")
                    self.detect_pierced_faces_python(progress)
                    self.used_enhanced_cpp = False
                    # --- 设置标志，表示使用了 Python 回退 --- 
                    python_fallback_used = True 
                else:
                     # --- 如果 try 块成功执行（没有 ValueError），设置标志 --- 
                    python_fallback_used = False
                
                # --- 这部分更新结果的逻辑应该在整个 C++ 尝试块 (包括 except ValueError 和 else) 之后 --- 
                # 只有在未使用 Python 回退时才执行此更新逻辑
                if not python_fallback_used:
                    # 计算相交关系总数
                    total_intersections = sum(len(faces) for faces in self.face_intersection_map.values())
                    
                    # 更新结果
                    # 确保intersecting_faces存在且有效
                    if 'intersecting_faces' not in locals() or intersecting_faces is None:
                        intersecting_faces = []
                        
                    self.result['selected_faces'] = list(intersecting_faces)
                    self.result['intersection_map'] = {str(k): list(v) for k, v in self.face_intersection_map.items()}
                    
                    # 计算相交关系总数
                    total_intersections = sum(len(faces) for faces in self.face_intersection_map.values())
                    if self.used_enhanced_cpp:
                        self.result['total_intersections'] = total_intersections
                    else:
                        self.result['total_intersections'] = total_intersections // 2  # 除以2因为每个关系被计算了两次
                    
                    total_time = time.time() - start_time
                    cpp_type = "增强版" if self.used_enhanced_cpp else "基础版"
                    if 'detection_time' not in locals():
                        detection_time = 0  # 如果之前的逻辑出错，初始化为0
                    detection_mode = "局部" if is_local_detection else "全局"
                    self.message = f"{detection_mode}检测: 检测到{len(intersecting_faces)}个穿刺面\n相交关系数量: {self.result['total_intersections']}个\n{cpp_type}C++算法用时: {detection_time:.4f}秒\n总用时: {total_time:.4f}秒"

            else: # --- 这个 else 对应 if self.use_cpp and HAS_PIERCED_FACES_CPP: ---
                # 使用Python算法
                if progress: self.update_progress(10, "使用Python算法检测穿刺面...")
                self.detect_pierced_faces_python(progress)
                
                total_time = time.time() - start_time
                detection_mode = "局部" if hasattr(self, 'target_faces') and self.target_faces else "全局"
                # 安全获取结果值
                if self.result:
                    selected_faces = self.result.get('selected_faces', [])
                    total_intersections = self.result.get('total_intersections', 0)
                    self.message = f"{detection_mode}检测: 检测到{len(selected_faces)}个穿刺面\n相交关系数量: {total_intersections}个\nPython算法用时: {total_time:.4f}秒"
                else:
                    self.message = f"{detection_mode}检测: 检测失败\nPython算法用时: {total_time:.4f}秒"
            
            self.update_progress(100)
            self.close_progress_dialog()
            
            if parent:
                self.show_message(parent, "穿刺面检测完成", self.message)
                self.message_shown = True
            
            return self.result
        except Exception as e:
            traceback.print_exc()
            self.close_progress_dialog()
            if parent:
                self.show_message(parent, "错误", f"穿刺面检测失败: {str(e)}", icon="critical")
            return self.result
    
    def detect_pierced_faces_python(self, progress=None):
        """使用Python进行穿刺面检测"""
        n_faces = len(self.faces)
        intersecting_faces = set()
        self.face_intersection_map = {} # 初始化相交映射
        self.detection_time = 0 # Python 实现暂时不精确计时
        
        # 优化：仅检查可能相交的面片对（例如基于包围盒）
        start_build_time = time.time()
        octree = self.build_octree()
        end_build_time = time.time()
        print(f"八叉树构建耗时: {end_build_time - start_build_time:.4f} 秒")
        
        # 用于存储潜在相交的面片对，避免重复检查
        potential_pairs = set()
            
        # 查询八叉树获取潜在相交对
        start_query_time = time.time()
        for face_idx in range(n_faces):
            if progress and face_idx % 50 == 0:
                self.update_progress(10 + int(30 * face_idx / n_faces), f"查询八叉树 {face_idx+1}/{n_faces}")
            potential_partners = query_octree(octree, face_idx)
            for partner_idx in potential_partners:
                # 确保存储的对是唯一的(较小索引在前)
                if face_idx < partner_idx:
                    potential_pairs.add((face_idx, partner_idx))
                else:
                    potential_pairs.add((partner_idx, face_idx))
        end_query_time = time.time()
        print(f"八叉树查询耗时: {end_query_time - start_query_time:.4f} 秒, 找到 {len(potential_pairs)} 对潜在相交面片")
                    
        # 检查潜在相交的面片对
        start_check_time = time.time()
        checked_count = 0
        for idx, (i, j) in enumerate(potential_pairs):
            if progress and idx % 100 == 0:
                 progress_val = 40 + int(60 * idx / len(potential_pairs))
                 self.update_progress(progress_val, f"检查相交对 {idx+1}/{len(potential_pairs)}")
            
            face_i = self.faces[i]
            face_j = self.faces[j]
            face_i_verts = [self.vertices[face_i[0]], self.vertices[face_i[1]], self.vertices[face_i[2]]]
            face_j_verts = [self.vertices[face_j[0]], self.vertices[face_j[1]], self.vertices[face_j[2]]]
            
            if AlgorithmUtils.check_triangle_intersection(face_i_verts, face_j_verts):
                intersecting_faces.add(i)
                intersecting_faces.add(j)
                                        
                # 更新相交映射
                if i not in self.face_intersection_map:
                    self.face_intersection_map[i] = set()
                if j not in self.face_intersection_map:
                    self.face_intersection_map[j] = set()
                self.face_intersection_map[i].add(j)
                self.face_intersection_map[j].add(i)
            
            checked_count += 1
        
        end_check_time = time.time()
        print(f"相交检查耗时: {end_check_time - start_check_time:.4f} 秒, 检查了 {checked_count} 对")
        
        # 确保 result 是字典
        if self.result is None:
            self.result = {}
            
            self.result['selected_faces'] = list(intersecting_faces)
        # Python实现中face_intersection_map已经在此方法内构建
        # 可以在此函数末尾或finally块中统一设置self.result['intersection_map']
        # self.result['intersection_map'] = self.face_intersection_map
    
    # 以下是几何计算辅助函数，用于穿刺面检测
    
    def bounding_boxes_close(self, t1, t2, threshold):
        """
        检查两个三角形的边界框是否接近
        """
        # 计算边界框
        t1_min = np.min(t1, axis=0)
        t1_max = np.max(t1, axis=0)
        t2_min = np.min(t2, axis=0)
        t2_max = np.max(t2, axis=0)
        
        # 检查边界框是否接近
        for i in range(3):  # 对每个维度
            if t1_min[i] > t2_max[i] + threshold or t2_min[i] > t1_max[i] + threshold:
                return False
                
        return True
    
    def triangles_minimum_distance(self, t1, t2):
        """
        计算两个三角形之间的最小距离
        """
        min_distance = float('inf')
        
        # 检查t1的每个顶点到t2的距离
        for p in t1:
            dist = self.point_triangle_distance(p, t2)
            min_distance = min(min_distance, dist)
            
        # 检查t2的每个顶点到t1的距离
        for p in t2:
            dist = self.point_triangle_distance(p, t1)
            min_distance = min(min_distance, dist)
            
        # 检查边与边之间的距离
        for i in range(3):
            e1_start = t1[i]
            e1_end = t1[(i+1)%3]
            
            for j in range(3):
                e2_start = t2[j]
                e2_end = t2[(j+1)%3]
                
                dist = self.edge_edge_distance(e1_start, e1_end, e2_start, e2_end)
                min_distance = min(min_distance, dist)
        
        return min_distance
    
    def edge_edge_distance(self, p1, p2, p3, p4):
        """
        计算两条边之间的最小距离
        """
        p1 = np.array(p1)
        p2 = np.array(p2)
        p3 = np.array(p3)
        p4 = np.array(p4)
        
        # 计算边的方向向量
        d1 = p2 - p1
        d2 = p4 - p3
        
        # 计算边长度的平方
        l1_squared = np.sum(d1 * d1)
        l2_squared = np.sum(d2 * d2)
        
        # 处理退化边的情况
        if l1_squared < 1e-10:
            return self.point_segment_distance(p1, p3, p4)
        if l2_squared < 1e-10:
            return self.point_segment_distance(p3, p1, p2)
        
        # 计算混合积
        cross_d1d2 = np.cross(d1, d2)
        cross_d1d2_squared = np.sum(cross_d1d2 * cross_d1d2)
        
        # 如果两边几乎平行
        if cross_d1d2_squared < 1e-10:
            # 计算p1到p3p4的距离
            dist1 = self.point_segment_distance(p1, p3, p4)
            # 计算p2到p3p4的距离
            dist2 = self.point_segment_distance(p2, p3, p4)
            # 计算p3到p1p2的距离
            dist3 = self.point_segment_distance(p3, p1, p2)
            # 计算p4到p1p2的距离
            dist4 = self.point_segment_distance(p4, p1, p2)
            
            return min(dist1, dist2, dist3, dist4)
        
        # 计算线段参数方程的系数
        t = np.dot(np.cross(p3 - p1, d2), cross_d1d2) / cross_d1d2_squared
        s = np.dot(np.cross(p3 - p1, d1), cross_d1d2) / cross_d1d2_squared
        
        # 限制参数在[0,1]范围内
        t = max(0, min(1, t))
        s = max(0, min(1, s))
        
        # 计算最近点
        p1_nearest = p1 + t * d1
        p2_nearest = p3 + s * d2
        
        # 计算最小距离
        return np.linalg.norm(p1_nearest - p2_nearest)
    
    def point_triangle_distance(self, point, triangle):
        """
        计算点到三角形的最小距离
        """
        p = np.array(point)
        a, b, c = np.array(triangle[0]), np.array(triangle[1]), np.array(triangle[2])
        
        # 计算三角形法向量
        normal = np.cross(b - a, c - a)
        normal_length = np.linalg.norm(normal)
        
        # 处理退化三角形情况（面积接近0）
        if normal_length < 1e-10:
            # 如果三角形退化，计算点到三边的最小距离
            dist_ab = self.point_segment_distance(p, a, b)
            dist_bc = self.point_segment_distance(p, b, c)
            dist_ca = self.point_segment_distance(p, c, a)
            return min(dist_ab, dist_bc, dist_ca)
        
        # 单位法向量
        unit_normal = normal / normal_length
        
        # 计算点到三角形所在平面的距离
        plane_dist = abs(np.dot(p - a, unit_normal))
        
        # 计算点在三角形平面上的投影点
        projection = p - plane_dist * unit_normal
        
        # 使用重心坐标检查投影点是否在三角形内部
        area = 0.5 * normal_length
        
        # 计算子三角形面积
        area_pab = 0.5 * np.linalg.norm(np.cross(a - projection, b - projection))
        area_pbc = 0.5 * np.linalg.norm(np.cross(b - projection, c - projection))
        area_pca = 0.5 * np.linalg.norm(np.cross(c - projection, a - projection))
        
        # 计算重心坐标
        sum_areas = area_pab + area_pbc + area_pca
        
        # 检查点的投影是否在三角形内部
        # 允许一点数值误差 (1e-10)
        if abs(sum_areas - area) < 1e-10:
            return plane_dist
        
        # 如果投影在三角形外部，计算到最近的边的距离
        dist_ab = self.point_segment_distance(p, a, b)
        dist_bc = self.point_segment_distance(p, b, c)
        dist_ca = self.point_segment_distance(p, c, a)
        
        return min(dist_ab, dist_bc, dist_ca)
    
    def point_segment_distance(self, p, a, b):
        """
        计算点到线段的最小距离
        """
        p = np.array(p)
        a = np.array(a)
        b = np.array(b)
        
        # 线段方向向量
        ab = b - a
        ab_length = np.linalg.norm(ab)
        
        # 处理退化线段（长度接近0）
        if ab_length < 1e-10:
            return np.linalg.norm(p - a)
            
        # 单位方向向量
        ab_unit = ab / ab_length
        
        # 计算p到a的向量在ab方向上的投影长度
        ap = p - a
        projection_length = np.dot(ap, ab_unit)
        
        # 如果投影在线段外部，返回到最近端点的距离
        if projection_length < 0:
            return np.linalg.norm(p - a)
        elif projection_length > ab_length:
            return np.linalg.norm(p - b)
            
        # 计算投影点
        projection = a + projection_length * ab_unit
        
        # 计算点到投影点的距离
        return np.linalg.norm(p - projection)

    def triangles_intersect(self, t1, t2):
        """
        检查两个三角形是否相交
        """
        # 首先进行快速的边界盒检测
        # 计算t1的边界盒
        t1_min = np.min(t1, axis=0)
        t1_max = np.max(t1, axis=0)
        
        # 计算t2的边界盒
        t2_min = np.min(t2, axis=0)
        t2_max = np.max(t2, axis=0)
        
        # 如果边界盒不重叠，三角形肯定不相交
        if (t1_min[0] > t2_max[0] or t2_min[0] > t1_max[0] or
            t1_min[1] > t2_max[1] or t2_min[1] > t1_max[1] or
            t1_min[2] > t2_max[2] or t2_min[2] > t1_max[2]):
            return False
        
        # 检查三角形边是否与另一个三角形平面相交
        # 检查t1的边与t2平面的相交
        for i in range(3):
            edge_start = t1[i]
            edge_end = t1[(i + 1) % 3]
            
            if self.line_triangle_intersect(edge_start, edge_end, t2):
                return True
        
        # 检查t2的边与t1平面的相交
        for i in range(3):
            edge_start = t2[i]
            edge_end = t2[(i + 1) % 3]
            
            if self.line_triangle_intersect(edge_start, edge_end, t1):
                return True
        
        return False
    
    def line_triangle_intersect(self, line_start, line_end, triangle):
        """
        检查一条线段是否与一个三角形相交
        """
        # 实现Möller-Trumbore算法
        p1, p2, p3 = triangle
        
        # 线段的方向向量
        dir_vec = np.array(line_end) - np.array(line_start)
        dir_length = np.linalg.norm(dir_vec)
        
        if dir_length < 1e-10:  # 线段长度近似为0
            return False
            
        dir_vec = dir_vec / dir_length  # 归一化
        
        # 三角形的边向量
        edge1 = np.array(p2) - np.array(p1)
        edge2 = np.array(p3) - np.array(p1)
        
        # 计算叉乘
        h = np.cross(dir_vec, edge2)
        a = np.dot(edge1, h)
        
        # 如果平行于三角形平面，则不相交
        if abs(a) < 1e-10:
            return False
            
        f = 1.0 / a
        s = np.array(line_start) - np.array(p1)
        u = f * np.dot(s, h)
        
        # 判断u是否在[0,1]范围内
        if u < 0.0 or u > 1.0:
            return False
            
        q = np.cross(s, edge1)
        v = f * np.dot(dir_vec, q)
        
        # 判断v是否在[0,1]范围内
        if v < 0.0 or u + v > 1.0:
            return False
            
        # 计算参数t
        t = f * np.dot(edge2, q)
        
        # 判断t是否在[0,1]范围内（线段范围）
        return 0.0 <= t <= 1.0 