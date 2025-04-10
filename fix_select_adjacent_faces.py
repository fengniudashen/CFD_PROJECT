#!/usr/bin/env python
"""
This script specifically fixes the indentation issues in the select_adjacent_faces method
of mesh_viewer_qt.py
"""

def fix_select_adjacent_faces():
    """Fix indentation issues in the select_adjacent_faces method."""
    with open('src/mesh_viewer_qt.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the problematic section and replace it
    problematic = '''            # 将检测到的面片转换为选择
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
            QMessageBox.information(self, "邻近性分析完成", "未检测到邻近面片。")'''
    
    fixed = '''            # 将检测到的面片转换为选择
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
                QMessageBox.information(self, "邻近性分析完成", "未检测到邻近面片。")'''
    
    # Replace the problematic section
    if problematic in content:
        content = content.replace(problematic, fixed)
        with open('src/mesh_viewer_qt.py', 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

if __name__ == "__main__":
    if fix_select_adjacent_faces():
        print("Fixed select_adjacent_faces method in mesh_viewer_qt.py")
    else:
        print("Could not find the problematic section to fix") 