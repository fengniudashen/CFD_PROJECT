"""
面片质量分析算法
"""

import numpy as np
from .base_algorithm import BaseAlgorithm
import time

try:
    import face_quality_cpp
    HAS_CPP_MODULE = True
except ImportError:
    HAS_CPP_MODULE = False

class FaceQualityAlgorithm(BaseAlgorithm):
    """面片质量分析算法类"""
    
    def __init__(self, mesh_data=None, threshold=0.3):
        """
        初始化面片质量分析算法
        
        参数:
        mesh_data (dict): 包含顶点和面片数据的字典
        threshold (float): 质量阈值，默认0.3
        """
        super().__init__(mesh_data)
        self.threshold = threshold
        self.stats = {}
        self.use_cpp = HAS_CPP_MODULE
    
    def execute(self, parent=None, threshold=None):
        """
        执行面片质量分析
        
        参数:
        parent: 父窗口，用于显示界面元素
        threshold (float): 质量阈值，可选
        
        返回:
        dict: 结果字典，包含selected_faces和统计信息
        """
        if threshold is not None:
            self.threshold = threshold
            
        if not self.set_mesh_data(self.mesh_data):
            if parent:
                self.show_message(parent, "警告", "缺少有效的网格数据", icon="warning")
            return self.result
        
        progress = None
        if parent:
            progress = self.show_progress_dialog(parent, "面片质量分析", "正在分析面片质量...", 100)
        
        start_time = time.time()
        cpp_success = False
        
        try:
            # 尝试使用C++实现
            if self.use_cpp and HAS_CPP_MODULE:
                if progress: self.update_progress(10, "使用C++算法分析面片质量...")
                try:
                    # 调用C++实现
                    low_quality_faces, stats_dict, detection_time = face_quality_cpp.analyze_face_quality_with_timing(
                        self.vertices, self.faces, self.threshold)
                    
                    # 保存结果和统计信息
                    self.result['selected_faces'] = low_quality_faces if low_quality_faces is not None else []
                    self.stats = stats_dict if stats_dict is not None else {}
                    cpp_success = True
                    
                    total_time = time.time() - start_time
                    self.message = self.generate_quality_report()
                    self.message += f"\n\nC++算法用时: {detection_time:.4f}秒 (总用时: {total_time:.4f}秒)"
                    
                except Exception as e:
                    # 如果C++调用失败，回退到Python实现
                    if progress: self.update_progress(15, f"C++调用失败: {str(e)[:50]}...\n使用Python算法...")
            
            # 如果C++未成功，使用Python算法
            if not cpp_success:
                if progress: self.update_progress(10, "使用Python算法分析面片质量...")
                self.analyze_face_quality(progress)
                
                total_time = time.time() - start_time
                self.message = self.generate_quality_report()
                self.message += f"\n\nPython算法用时: {total_time:.4f}秒"
            
            if progress: self.update_progress(100)
            if progress: self.close_progress_dialog()
            
            # 将统计信息添加到结果中
            self.result['stats'] = self.stats
            
            if parent:
                self.show_message(parent, "面片质量分析完成", self.message)
            
            return self.result
            
        except Exception as e:
            import traceback
            error_msg = f"面片质量分析失败: {str(e)}\n{traceback.format_exc()}"
            if progress: self.close_progress_dialog()
            if parent:
                self.show_message(parent, "错误", error_msg, icon="critical")
            if self.result is None:
                self.result = {'selected_faces': [], 'stats': {}}
            elif 'selected_faces' not in self.result:
                self.result['selected_faces'] = []
            if 'stats' not in self.result:
                self.result['stats'] = {}
            return self.result
    
    def analyze_face_quality(self, progress=None):
        """
        使用STAR-CCM+的算法分析面片质量
        
        STAR-CCM+的面片质量算法: face quality = 2 * (r/R)
        其中：
        r = 内接圆半径
        R = 外接圆半径
        """
        # 初始化统计信息
        self.stats = {
            'total_faces': len(self.faces),
            'quality_values': [],
            'low_quality_faces': [],
            'quality_distribution': {
                '0.0-0.1': 0,
                '0.1-0.2': 0,
                '0.2-0.3': 0,
                '0.3-0.4': 0,
                '0.4-0.5': 0,
                '0.5-0.6': 0,
                '0.6-0.7': 0,
                '0.7-0.8': 0,
                '0.8-0.9': 0,
                '0.9-1.0': 0
            }
        }
        
        total_faces = len(self.faces)
        
        if progress: self.update_progress(10, f"分析 {total_faces} 个面片...")
        
        # 分析每个面片的质量
        for i, face in enumerate(self.faces):
            # 更新进度
            if progress and i % 100 == 0:
                progress_val = 10 + int(85 * i / total_faces)
                self.update_progress(progress_val, f"分析面片 {i+1}/{total_faces}")
                if self.progress_dialog and self.progress_dialog.wasCanceled():
                    break
            
            # 获取面片的三个顶点
            vertices = [self.vertices[face[0]], self.vertices[face[1]], self.vertices[face[2]]]
            
            # 计算面片质量
            quality = self.calculate_face_quality(vertices)
            self.stats['quality_values'].append(quality)
            
            # 更新质量分布
            if quality < 0.1:
                self.stats['quality_distribution']['0.0-0.1'] += 1
            elif quality < 0.2:
                self.stats['quality_distribution']['0.1-0.2'] += 1
            elif quality < 0.3:
                self.stats['quality_distribution']['0.2-0.3'] += 1
            elif quality < 0.4:
                self.stats['quality_distribution']['0.3-0.4'] += 1
            elif quality < 0.5:
                self.stats['quality_distribution']['0.4-0.5'] += 1
            elif quality < 0.6:
                self.stats['quality_distribution']['0.5-0.6'] += 1
            elif quality < 0.7:
                self.stats['quality_distribution']['0.6-0.7'] += 1
            elif quality < 0.8:
                self.stats['quality_distribution']['0.7-0.8'] += 1
            elif quality < 0.9:
                self.stats['quality_distribution']['0.8-0.9'] += 1
            else:
                self.stats['quality_distribution']['0.9-1.0'] += 1
            
            # 检查是否低于阈值
            if quality < self.threshold:
                self.stats['low_quality_faces'].append(i)
        
        # 计算总体统计信息
        if self.stats['quality_values']:
            quality_values = np.array(self.stats['quality_values'])
            self.stats['min_quality'] = float(np.min(quality_values))
            self.stats['max_quality'] = float(np.max(quality_values))
            self.stats['avg_quality'] = float(np.mean(quality_values))
        else:
            self.stats['min_quality'] = 0.0
            self.stats['max_quality'] = 0.0
            self.stats['avg_quality'] = 0.0
        
        # 更新结果
        if self.result is None:
            self.result = {}
        self.result['selected_faces'] = self.stats['low_quality_faces']
        
        if progress: self.update_progress(95, "完成")
        
        return self.result
    
    def calculate_face_quality(self, vertices):
        """
        计算单个面片的质量
        
        参数:
        vertices (list): 包含三个顶点坐标的列表
        
        返回:
        float: 面片质量值 (0-1 之间，越接近1质量越好)
        """
        # 计算三条边的长度
        v1 = np.array(vertices[0])
        v2 = np.array(vertices[1])
        v3 = np.array(vertices[2])
        
        a = np.linalg.norm(v2 - v3)
        b = np.linalg.norm(v1 - v3)
        c = np.linalg.norm(v1 - v2)
        
        # 计算半周长
        s = (a + b + c) / 2.0
        
        # 计算面积（使用海伦公式）
        area = np.sqrt(max(0, s * (s - a) * (s - b) * (s - c)))
        
        # 处理退化三角形
        if area < 1e-10:
            return 0.0
        
        # 计算内接圆半径
        r = area / s
        
        # 计算外接圆半径
        R = (a * b * c) / (4.0 * area)
        
        # 计算STAR-CCM+质量度量
        quality = min(1.0, max(0.0, 2.0 * (r / R)))
        
        return quality
    
    def generate_quality_report(self):
        """
        生成质量分析报告
        
        返回:
        str: 格式化的质量报告
        """
        report = f"面片质量分析报告：\n\n"
        report += f"总面片数: {self.stats['total_faces']}\n"
        report += f"低质量面片数 (< {self.threshold:.2f}): {len(self.stats['low_quality_faces'])}"
        
        if self.stats['total_faces'] > 0:
            percent = len(self.stats['low_quality_faces']) / self.stats['total_faces'] * 100
            report += f" ({percent:.2f}%)\n\n"
        else:
            report += " (0%)\n\n"
        
        report += f"最小质量: {self.stats['min_quality']:.4f}\n"
        report += f"最大质量: {self.stats['max_quality']:.4f}\n"
        report += f"平均质量: {self.stats['avg_quality']:.4f}\n\n"
        
        report += "质量分布:\n"
        for range_key, count in self.stats['quality_distribution'].items():
            percent = count / self.stats['total_faces'] * 100 if self.stats['total_faces'] > 0 else 0
            report += f"{range_key}: {count} ({percent:.2f}%)\n"
        
        return report 