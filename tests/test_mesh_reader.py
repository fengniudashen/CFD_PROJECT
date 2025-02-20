import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from src.mesh_reader import read_nas_file
from src.mesh_viewer_qt import MeshViewerQt

def main():
    # 获取命令行参数中的文件路径，如果没有提供则使用默认文件
    mesh_file = sys.argv[1] if len(sys.argv) > 1 else "tests/test.nas"
    
    # 读取网格文件
    mesh_data = read_nas_file(mesh_file)
    
    # 创建 Qt 应用
    app = QApplication(sys.argv)
    
    # 创建并显示网格查看器
    viewer = MeshViewerQt(mesh_data)
    viewer.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 