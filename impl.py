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
    namespace_start = re.search(r'^\s*namespace\s+[\w\.]+\s*\{', java_code, re.MULTILINE)
    if namespace_start:
        brace_count = 0
        start_pos = namespace_start.end() - 1
        for i in range(start_pos, len(java_code)):
            if java_code[i] == '{':
                brace_count += 1
            elif java_code[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    java_code = java_code[start_pos + 1:i]
                    break
    
    # 3. 删除#region和#endregion
    java_code = re.sub(r'^\s*#region.*$\n', '', java_code, flags=re.MULTILINE)
    java_code = re.sub(r'^\s*#endregion.*$\n', '', java_code, flags=re.MULTILINE)
    
    # 4. 转换XML注释并彻底删除XML标签
    def clean_xml_from_comment(comment_text):
        """彻底清理注释中的XML标签"""
        # 删除所有XML标签（包括自闭合标签）
        comment_text = re.sub(r'<[/]?\w+\s*[^>]*>', '', comment_text)
        # 删除XML标签内的属性
        comment_text = re.sub(r'\b\w+="[^"]*"', '', comment_text)
        # 删除多余的空白字符
        comment_text = re.sub(r'\s+', ' ', comment_text)
        # 删除行首行尾空格
        comment_text = comment_text.strip()
        return comment_text
    
    def convert_xml_comment(match):
        comment_lines = match.group(0).split('\n')
        result = ['/**']
        for line in comment_lines:
            # 去除 /// 前缀
            cleaned = re.sub(r'^\s*///\s?', '', line)
            # 彻底清理XML标签
            cleaned = clean_xml_from_comment(cleaned)
            
            if cleaned:
                result.append(f' * {cleaned}')
            else:
                result.append(' *')
        result.append(' */')
        return '\n'.join(result)
    
    # 查找连续的///注释块
    java_code = re.sub(r'(?m)^\s*///[^\n]*\n(\s*///[^\n]*\n)*', convert_xml_comment, java_code)
    
    # 5. 转换方法名（首字母小写）
    def convert_method_signature(match):
        indent = match.group(1)
        modifier = match.group(2)
        return_type = match.group(3)
        method_name = match.group(4)
        params = match.group(5)
        rest = match.group(6) if len(match.groups()) > 5 else ''
        
        # 如果是构造函数，不转换方法名
        if method_name == class_name or method_name == class_name.replace('Impl', ''):
            new_method_name = method_name
        else:
            # 方法名首字母小写
            new_method_name = method_name[0].lower() + method_name[1:]
        
        return f'{indent}{modifier} {return_type} {new_method_name}({params}){rest}'
    
    # 匹配方法声明
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
    
    # 8. 提取接口名（从类继承或实现中）
    interface_name = None
    # 查找类继承/实现
    extends_pattern = r'class\s+\w+\s*:\s*(\w+)'
    match = re.search(extends_pattern, java_code)
    if match:
        interface_name = match.group(1)
        # 删除继承部分
        java_code = re.sub(r'\s*:\s*\w+', '', java_code)
    
    # 9. 修改类名：添加Service和Impl
    def rename_class(match):
        indent = match.group(1)
        modifier = match.group(2) if match.group(2) else 'public'
        old_class_name = match.group(3)
        
        # 提取基础名称（去掉Impl或Service后缀）
        base_name = old_class_name
        if base_name.endswith('Impl'):
            base_name = base_name[:-4]
        if base_name.endswith('Service'):
            base_name = base_name[:-7]
        
        # 新类名：基础名 + ServiceImpl
        new_class_name = f'{base_name}ServiceImpl'
        
        # 添加implements子句
        if interface_name:
            return f'{indent}{modifier} class {new_class_name} implements {interface_name}'
        else:
            return f'{indent}{modifier} class {new_class_name}'
    
    class_pattern = r'(\s*)(public|private|protected|internal)?\s*class\s+(\w+)'
    java_code = re.sub(class_pattern, rename_class, java_code, count=1)
    
    # 10. 确保类有完整的括号匹配
    def ensure_braces(code):
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        if open_braces > close_braces:
            missing = open_braces - close_braces
            code += '\n' + '}' * missing
        return code
    
    java_code = ensure_braces(java_code)
    
    # 11. 清理多余的空白行
    java_code = re.sub(r'\n\s*\n\s*\n', '\n\n', java_code)
    
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
            
            # 提取新的类名（从转换后的代码中）
            class_match = re.search(r'class\s+(\w+)', java_code)
            if class_match:
                new_class_name = class_match.group(1)
            else:
                # 默认生成类名
                base = original_class_name.replace('Impl', '').replace('Service', '')
                new_class_name = f'{base}ServiceImpl'
            
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
            import traceback
            traceback.print_exc()
    
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
