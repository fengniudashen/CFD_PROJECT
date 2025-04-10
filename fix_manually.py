#!/usr/bin/env python
"""
This script will manually fix the indentation issues in mesh_viewer_qt.py
"""

def fix_file():
    # Read the file
    with open('src/mesh_viewer_qt.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the problematic method
    adjacent_faces_start = 0
    adjacent_faces_end = 0
    
    for i, line in enumerate(lines):
        if 'def select_adjacent_faces(self):' in line:
            adjacent_faces_start = i
        elif adjacent_faces_start > 0 and 'def select_overlapping_points(self):' in line:
            adjacent_faces_end = i
            break
    
    if adjacent_faces_start > 0 and adjacent_faces_end > 0:
        # Replace the method with a fixed version
        fixed_method = '''    def select_adjacent_faces(self):
        """
        分析面片邻近性，使用STAR-CCM+公式和高性能算法来检测和识别问题面片。
        
        性能优化策略:
        1. 使用专用的高性能实现，从独立模块导入
        2. 利用numpy向量化操作 
        3. 使用空间哈希网格而非KD-tree加速空间查询
        4. 使用AABB包围盒快速剔除
        5. 多线程并行计算面片距离
        """
        try:
            # 导入高性能实现
            from high_performance_proximity import detect_face_proximity
            import numpy as np
            from PyQt5.QtWidgets import QInputDialog, QProgressDialog, QMessageBox
            
            # 获取用户输入的邻近阈值
            threshold, ok = QInputDialog.getDouble(
                self, "设置面片邻近性阈值", 
                "请输入邻近性阈值 (0.01-0.5)，较小的值检测更严格:", 
                0.1, 0.01, 0.5, 2)
            
            if not ok:
                return

            # 创建进度对话框
            progress = QProgressDialog("分析面片邻近性...", "取消", 0, 100, self)
            progress.setWindowTitle("面片邻近性分析")
            progress.setMinimumDuration(0)
            progress.setWindowModality(2)  # 应用程序模态
            progress.show()
            
            # 进度回调函数
            def update_progress(value, message):
                progress.setValue(value)
                progress.setLabelText(message)
                if progress.wasCanceled():
                    raise Exception("用户取消")
            
            # 清除当前选择
            self.clear_selection()
            
            # 准备面片和顶点数据为numpy数组
            vertices = np.array(self.mesh_data['vertices'])
            faces = np.array(self.mesh_data['faces'])
            
            # 使用高性能模块检测邻近面片
            proximity_faces = detect_face_proximity(
                faces, vertices, threshold, 
                use_multiprocessing=True, 
                progress_callback=update_progress
            )
            
            # 将检测到的面片转换为选择
            if proximity_faces:
                # 将检测到的面片添加到选择中
                self.selected_faces = list(proximity_faces)
                
                # 更新网格显示
                self.update_display()
                
                # 显示结果信息
                QMessageBox.information(
                    self, "邻近性分析完成", 
                    f"检测到 {len(proximity_faces)} 个邻近面片，占总面片数的 {len(proximity_faces)/len(faces)*100:.2f}%。\\n"
                    f"这些面片已被选中。"
                )
            else:
                QMessageBox.information(self, "邻近性分析完成", "未检测到邻近面片。")
            
            # 关闭进度对话框
            progress.setValue(100)
            
        except ImportError:
            QMessageBox.critical(
                self, "模块缺失", 
                "无法导入高性能邻近性检测模块。请确保high_performance_proximity.py文件存在于src目录中。"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"邻近性分析失败: {str(e)}")
        
'''
        
        # Replace the method
        new_lines = lines[:adjacent_faces_start] + [fixed_method] + lines[adjacent_faces_end:]
        
        # Write the corrected file
        with open('src/mesh_viewer_qt.py', 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"Fixed the select_adjacent_faces method (lines {adjacent_faces_start}-{adjacent_faces_end})")
        return True
    else:
        print("Could not find the select_adjacent_faces method")
        return False

if __name__ == "__main__":
    fix_file() 