#!/usr/bin/env python
"""
This script fixes indentation issues in mesh_viewer_qt.py.
It specifically targets the incorrectly indented self.update_display() calls.
"""

def fix_indentation():
    # Read the file
    with open('src/mesh_viewer_qt.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix lines with incorrect indentation
    for i in range(len(lines)):
        # Fix self.update_display() calls with excessive indentation
        if '                self.update_display()' in lines[i]:
            indent_level = lines[i].index('self')
            if indent_level > 8:  # If indentation is excessive
                # Determine the correct indentation from the context
                # Usually it should match the indentation of the surrounding lines
                correct_indent = ' ' * 8  # Default to 8 spaces
                
                # Check previous line to determine context
                if i > 0:
                    prev_line = lines[i-1]
                    if prev_line.strip() and not prev_line.strip().startswith('#'):
                        # Get indentation of previous line
                        prev_indent = len(prev_line) - len(prev_line.lstrip())
                        correct_indent = ' ' * prev_indent
                
                # Apply the correct indentation
                lines[i] = correct_indent + 'self.update_display()\n'
    
    # Write the corrected content back to the file
    with open('src/mesh_viewer_qt.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

if __name__ == "__main__":
    fix_indentation()
    print("Indentation issues fixed in mesh_viewer_qt.py") 