#!/usr/bin/env python
"""
This script will find and fix any remaining indentation issues in mesh_viewer_qt.py
"""

def fix_file():
    # Read the file
    with open('src/mesh_viewer_qt.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix specific known issues
    content = content.replace(
        '            # 更新界面显示\n                    self.update_display()',
        '            # 更新界面显示\n            self.update_display()'
    )
    
    # Write the corrected file
    with open('src/mesh_viewer_qt.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed remaining indentation issues in mesh_viewer_qt.py")

if __name__ == "__main__":
    fix_file() 