import re
import os
import glob

def convert_csharp_to_java(csharp_code, class_name):
    """
    将C#代码转换为Java代码
    """
    java_code = csharp_code
    
    # 1. 删除using语句
    lines = java_code.split('\n')
    filtered_lines = []
    for line in lines:
        if not re.match(r'^\s*using\s+[\w\.]+\s*;', line):
            filtered_lines.append(line)
    java_code = '\n'.join(filtered_lines)
    
    # 2. 去掉namespace包装，但保留里面的内容
    # 匹配从namespace开始到最后一个}结束
    namespace_pattern = r'^\s*namespace\s+[\w\.]+\s*\{(.*)\n\s*\}[ \t]*$'
    match = re.search(namespace_pattern, java_code, re.DOTALL | re.MULTILINE)
    if match:
        java_code = match.group(1)
    
    # 3. 删除#region和#endregion
    java_code = re.sub(r'^\s*#region.*$\n', '', java_code, flags=re.MULTILINE)
    java_code = re.sub(r'^\s*#endregion.*$\n', '', java_code, flags=re.MULTILINE)
    
    # 4. 转换XML注释并删除XML标签
    def convert_xml_comment(match):
        comment_lines = match.group(0).split('\n')
        result = ['/**']
        for line in comment_lines:
            # 去除 /// 前缀
            cleaned = re.sub(r'^\s*///\s?', '', line)
            # 删除XML标签
            cleaned = re.sub(r'</?(summary|param|returns|exception|see|c|code|list|item|term|description|example|remarks?)\s*/?>', '', cleaned)
            # 删除XML属性
            cleaned = re.sub(r'\s+\w+="[^"]*"', '', cleaned)
            # 清理多余的空白
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            if cleaned:
                result.append(f' * {cleaned}')
            else:
                result.append(' *')
        result.append(' */')
        return '\n'.join(result)
    
    # 查找连续的///注释块
    java_code = re.sub(r'(?m)^\s*///[^\n]*\n(\s*///[^\n]*\n)*', convert_xml_comment, java_code)
    
    # 5. 转换方法名（首字母小写）- 修复参数括号问题
    def convert_method_signature(match):
        indent = match.group(1)
        modifier = match.group(2)
        return_type = match.group(3)
        method_name = match.group(4)
        params = match.group(5)  # 这部分已经包含了括号内的参数
        # 检查后面是否有方法体开始的花括号
        rest = match.group(6) if len(match.groups()) > 5 else ''
        
        # 如果是构造函数（方法名和类名相同），不转换
        if method_name == class_name:
            return match.group(0)
        
        # 方法名首字母小写
        if method_name and len(method_name) > 0:
            java_method_name = method_name[0].lower() + method_name[1:]
            # 保持参数括号完整
            return f'{indent}{modifier} {return_type} {java_method_name}({params}){rest}'
        return match.group(0)
    
    # 匹配方法声明 - 改进正则表达式以正确捕获参数括号
    method_pattern = r'(\s*)(public|private|protected|internal)\s+([\w<>\[\]]+)\s+([A-Z]\w*)\s*\(([^)]*)\)(\s*\{?)'
    java_code = re.sub(method_pattern, convert_method_signature, java_code)
    
    # 6. 转换属性为字段
    property_pattern = r'(\s*)(public|private|protected|internal)\s+(\w+)\s+([A-Z]\w*)\s*\{\s*get;\s*set;\s*\}'
    def convert_property(match):
        indent = match.group(1)
        modifier = match.group(2)
        prop_type = match.group(3)
        prop_name = match.group(4)
        
        # 转换类型
        if prop_type == 'string':
            prop_type = 'String'
        elif prop_type == 'bool':
            prop_type = 'boolean'
        
        return f'{indent}{modifier} {prop_type} {prop_name};'
    
    java_code = re.sub(property_pattern, convert_property, java_code)
    
    # 7. 转换类型
    java_code = re.sub(r'\bstring\b', 'String', java_code)
    java_code = re.sub(r'\bbool\b', 'boolean', java_code)
    java_code = re.sub(r'\bobject\b', 'Object', java_code)
    
    # 8. 确保类有完整的括号匹配
    def ensure_braces(code):
        # 统计花括号数量
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        # 如果缺少结尾花括号，添加
        if open_braces > close_braces:
            missing = open_braces - close_braces
            code += '\n' + '}' * missing
        return code
    
    java_code = ensure_braces(java_code)
    
    # 9. 处理类名
    if not class_name.endswith('Impl'):
        class_pattern = r'(\s*)(public|private|protected|internal)?\s*class\s+(\w+)'
        def rename_class(match):
            indent = match.group(1)
            modifier = match.group(2) if match.group(2) else 'public'
            old_class_name = match.group(3)
            new_class_name = old_class_name + 'Impl'
            return f'{indent}{modifier} class {new_class_name}'
        java_code = re.sub(class_pattern, rename_class, java_code, count=1)
    
    # 10. 清理多余的空白行
    java_code = re.sub(r'\n\s*\n\s*\n', '\n\n', java_code)
    
    # 11. 确保每个方法都有完整的方法体
    # 如果方法声明后面没有花括号，添加空方法体
    method_without_body = r'(\s*)(public|private|protected)\s+(\w+)\s+(\w+)\(([^)]*)\)\s*;'
    def add_empty_body(match):
        indent = match.group(1)
        modifier = match.group(2)
        return_type = match.group(3)
        method_name = match.group(4)
        params = match.group(5)
        return f'{indent}{modifier} {return_type} {method_name}({params}) {{\n{indent}    // TODO: 实现该方法\n{indent}}}'
    
    java_code = re.sub(method_without_body, add_empty_body, java_code)
    
    return java_code


def process_folder(input_folder, output_folder=None):
    """
    处理文件夹中的所有C#文件
    """
    # 设置输出文件夹
    if output_folder is None:
        output_folder = os.path.join(input_folder, 'java_output')
    
    # 创建输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"创建输出目录: {output_folder}")
    
    # 查找所有.cs文件
    cs_files = glob.glob(os.path.join(input_folder, '*.cs'))
    
    if not cs_files:
        print(f"在 {input_folder} 中没有找到.cs文件")
        return
    
    print(f"找到 {len(cs_files)} 个C#文件\n")
    
    for cs_file in cs_files:
        try:
            # 读取C#文件
            with open(cs_file, 'r', encoding='utf-8') as f:
                csharp_code = f.read()
            
            # 提取原始类名（从文件名）
            base_name = os.path.basename(cs_file)
            original_class_name = base_name.replace('.cs', '')
            
            # 转换为Java
            java_code = convert_csharp_to_java(csharp_code, original_class_name)
            
            # 确定新的类名
            if original_class_name.endswith('Impl'):
                new_class_name = original_class_name
            else:
                new_class_name = original_class_name + 'Impl'
            
            # 生成Java文件名
            java_file_name = f'{new_class_name}.java'
            java_file_path = os.path.join(output_folder, java_file_name)
            
            # 写入Java文件
            with open(java_file_path, 'w', encoding='utf-8') as f:
                f.write(java_code)
            
            # 检查转换质量
            open_count = java_code.count('{')
            close_count = java_code.count('}')
            param_count = java_code.count('(')
            param_close_count = java_code.count(')')
            
            issues = []
            if open_count != close_count:
                issues.append(f"括号不匹配 (开:{open_count}, 闭:{close_count})")
            if param_count != param_close_count:
                issues.append(f"参数括号不匹配 (开:{param_count}, 闭:{param_close_count})")
            
            if issues:
                print(f"⚠ 警告: {base_name} - {', '.join(issues)}")
            elif len(java_code.strip()) == 0:
                print(f"⚠ 警告: {base_name} 转换后为空")
            else:
                print(f"✓ 转换成功: {base_name} -> {java_file_name}")
            
        except Exception as e:
            print(f"✗ 转换失败: {cs_file}")
            print(f"  错误: {str(e)}")
    
    print(f"\n转换完成！输出目录: {output_folder}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='将C#服务实现类转换为Java实现类')
    parser.add_argument('input_folder', help='输入的C#文件夹路径')
    parser.add_argument('-o', '--output', help='输出的Java文件夹路径（可选）', default=None)
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_folder):
        print(f"错误: 输入文件夹不存在: {args.input_folder}")
        return
    
    if not os.path.isdir(args.input_folder):
        print(f"错误: 输入路径不是文件夹: {args.input_folder}")
        return
    
    process_folder(args.input_folder, args.output)


if __name__ == '__main__':
    # 如果没有命令行参数，使用交互式输入
    import sys
    
    if len(sys.argv) == 1:
        input_folder = input("请输入C#文件所在的文件夹路径: ").strip()
        output_folder = input("请输入Java输出文件夹路径（直接回车使用默认）: ").strip()
        
        if not output_folder:
            output_folder = None
        
        if os.path.exists(input_folder) and os.path.isdir(input_folder):
            process_folder(input_folder, output_folder)
        else:
            print(f"错误: 文件夹不存在: {input_folder}")
    else:
        main()
