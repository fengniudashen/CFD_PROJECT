#!/usr/bin/env python
"""
集成C++实现的自由边检测算法的网格查看器
修改自mesh_viewer_qt.py
"""
import sys
import os
import time
import numpy as np
from PyQt5.QtWidgets import QApplication
from mesh_viewer_qt import MeshViewerQt

# 尝试导入C++模块，如果不存在则警告并回退到Python实现
try:
    import free_edges_cpp
    CPP_MODULE_AVAILABLE = True
    print("使用C++加速模块进行自由边检测")
except ImportError:
    CPP_MODULE_AVAILABLE = False
    print("警告：C++加速模块未找到，将使用Python实现（速度较慢）")
    print("如需加速，请运行 src/compare_free_edges.py 编译C++模块")

class MeshViewerQtCpp(MeshViewerQt):
    """继承自MeshViewerQt，使用C++实现的高性能算法"""
    
    def __init__(self, mesh_data):
        # 调用父类初始化方法
        super().__init__(mesh_data)
        # 记录是否使用了C++实现
        self.using_cpp = CPP_MODULE_AVAILABLE
        # 为状态栏添加信息
        if self.using_cpp:
            self.statusBar.showMessage("已启用C++加速 - 自由边检测")
    
    def select_free_edges(self):
        """使用C++实现的自由边检测算法"""
        # 清除之前的选择
        self.selected_edges = []
        
        # 记录开始时间
        start_time = time.time()
        
        if self.using_cpp and CPP_MODULE_AVAILABLE:
            # 使用C++实现
            try:
                cpp_result, cpp_time = free_edges_cpp.detect_free_edges_with_timing(self.mesh_data['faces'].tolist())
                # 将C++结果转换为Python格式
                self.selected_edges = [tuple(edge) for edge in cpp_result]
                execution_time = cpp_time  # 使用C++内部计时
            except Exception as e:
                print(f"C++实现出错，回退到Python实现: {e}")
                # 回退到Python实现
                self.selected_edges = self._detect_free_edges_py()
                execution_time = time.time() - start_time
        else:
            # 使用Python实现
            self.selected_edges = self._detect_free_edges_py()
            execution_time = time.time() - start_time
        
        # 更新显示
        self.update_display()
        
        # 检查是否找到了自由边
        count = len(self.selected_edges)
        if count > 0:
            self.adjust_font_size(self.free_edge_count, str(count))
        else:
            self.adjust_font_size(self.free_edge_count, "0")
        
        # 更新状态栏显示
        impl_type = "C++" if self.using_cpp and CPP_MODULE_AVAILABLE else "Python"
        self.statusBar.showMessage(f"找到 {count} 条自由边 ({impl_type}实现，用时 {execution_time:.4f}秒)")
    
    def _detect_free_edges_py(self):
        """Python实现的自由边检测（与原始实现相同）"""
        # 用字典记录每条边出现的次数
        edge_count = {}
        
        # 遍历所有面片，收集边信息
        for face in self.mesh_data['faces']:
            # 获取面片的三条边
            edge1 = tuple(sorted([face[0], face[1]]))
            edge2 = tuple(sorted([face[1], face[2]]))
            edge3 = tuple(sorted([face[2], face[0]]))
            
            # 更新边的计数
            edge_count[edge1] = edge_count.get(edge1, 0) + 1
            edge_count[edge2] = edge_count.get(edge2, 0) + 1
            edge_count[edge3] = edge_count.get(edge3, 0) + 1
        
        # 找出只出现一次的边（自由边）
        return [edge for edge, count in edge_count.items() if count == 1]

def main():
    """主函数"""
    # 测试用，加载一个示例模型
    nas_file = os.path.join("src", "data", "complex_3d_model.nas")
    
    if not os.path.exists(nas_file):
        print(f"错误: 文件不存在 {nas_file}")
        print("请先运行 generate_complex_3d.py 生成文件")
        return 1
    
    # 加载模型（简化版，实际应使用完整的load_nas_file函数）
    vertices = []
    faces = []
    vertex_id_map = {}
    
    with open(nas_file, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('GRID*'):
            if i + 1 < len(lines):
                parts1 = line.split()
                next_line = lines[i+1].strip()
                if next_line.startswith('*'):
                    parts2 = next_line.split()
                    try:
                        node_id = int(parts1[1])
                        x = float(parts1[3])
                        y = float(parts1[4])
                        z = float(parts2[1])
                        vertex_id_map[node_id] = len(vertices)
                        vertices.append([x, y, z])
                    except (ValueError, IndexError):
                        pass
                    i += 1
        i += 1
    
    for line in lines:
        if line.startswith('CTRIA3'):
            parts = line.split()
            if len(parts) >= 6:
                try:
                    n1 = int(parts[3])
                    n2 = int(parts[4])
                    n3 = int(parts[5])
                    if n1 in vertex_id_map and n2 in vertex_id_map and n3 in vertex_id_map:
                        v1 = vertex_id_map[n1]
                        v2 = vertex_id_map[n2]
                        v3 = vertex_id_map[n3]
                        faces.append([v1, v2, v3])
                except (ValueError, IndexError):
                    pass
    
    # 转换为numpy数组
    vertices = np.array(vertices, dtype=np.float32)
    faces = np.array(faces, dtype=np.int32)
    
    # 计算简单法向量
    normals = np.zeros_like(vertices)
    
    print(f"模型加载完成: {len(vertices)}个顶点, {len(faces)}个面片")
    
    # 使用CPP增强版查看器
    app = QApplication(sys.argv)
    mesh_data = {'vertices': vertices, 'faces': faces, 'normals': normals}
    viewer = MeshViewerQtCpp(mesh_data)
    viewer.show()
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 