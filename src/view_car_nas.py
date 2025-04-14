#!/usr/bin/env python
"""
演示脚本：使用mesh_viewer.py中的功能读取并显示汽车NAS模型
"""
import sys
import os
from mesh_viewer import MeshViewer

def main():
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 使用命令行参数作为文件路径
        nas_file = sys.argv[1]
    else:
        # 使用默认文件路径
        nas_file = os.path.join("data", "car_model.nas")
    
    # 确保文件存在
    if not os.path.exists(nas_file):
        print(f"错误: 文件不存在 {nas_file}")
        return 1
    
    print(f"正在加载并显示NAS文件: {nas_file}")
    
    # 创建网格查看器实例
    viewer = MeshViewer()
    
    # 直接从NAS文件读取并显示三角形网格
    viewer.view_triangular_nas_from_file(nas_file)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 