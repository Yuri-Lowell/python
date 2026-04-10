import re
import os
import glob

def extract_namespace_content(code):
    """提取namespace内的内容"""
    namespace_start = re.search(r'^\s*namespace\s+[\w\.]+\s*\{', code, re.MULTILINE)
    if not namespace_start:
        return code
    
    brace_count = 0
    start_pos = namespace_start.end() - 1
    for i in range(start_pos, len(code)):
        if code[i] == '{':
            brace_count += 1
        elif code[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                return code[start_pos + 1:i]
    return code

def clean_xml_comment(comment_text):
    """清理XML注释并提取参数和返回值"""
    # 提取summary
    summary_match = re.search(r'<summary>(.*?)</summary>', comment_text, re.DOTALL)
    summary = re.sub(r'\s+', ' ', summary_match.group(1).strip()) if summary_match else ""
    
    # 提取所有param
    params = []
    for match in re.finditer(r'<param\s+name="([^"]+)"\s*>(.*?)</param>', comment_text, re.DOTALL):
        param_name = match.group(1)
        param_desc = re.sub(r'\s+', ' ', match.group(2).strip())
        params.append((param_name, param_desc))
    
    # 提取returns
    returns_match = re.search(r'<returns>(.*?)</returns>', comment_text, re.DOTALL)
    returns = re.sub(r'\s+', ' ', returns_match.group(1).strip()) if returns_match else ""
    
    return summary, params, returns

def convert_xml_comments(code):
    """转换XML注释为JavaDoc"""
    lines = code.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('///'):
            # 收集连续的注释行
            comment_lines = []
            while i < len(lines) and lines[i].strip().startswith('///'):
                comment_lines.append(lines[i])
                i += 1
            
            # 合并注释
            full_comment = '\n'.join(comment_lines)
            summary, params, returns = clean_xml_comment(full_comment)
            
            # 生成JavaDoc
            javadoc = ['/**']
            if summary:
                javadoc.append(f' * {summary}')
                javadoc.append(' *')
            
            for param_name, param_desc in params:
                javadoc.append(f' * @param {param_name} {param_desc}')
            
            if returns:
                javadoc.append(f' * @return {returns}')
            
            if len(javadoc) == 1:
                javadoc.append(' *')
            
            javadoc.append(' */')
            result.extend(javadoc)
        else:
            result.append(line)
            i += 1
    
    return '\n'.join(result)

def convert_methods_and_add_override(code, class_name):
    """转换方法名首字母小写并添加@Override注解"""
    lines = code.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是public/private/protected方法声明
        stripped = line.strip()
        
        # 匹配方法声明的正则
        method_pattern = r'^\s*(public|private|protected)\s+([\w<>\[\]]+)\s+([A-Z]\w*)\s*\('
        method_match = re.match(method_pattern, line)
        
        if method_match and not stripped.startswith('//') and not stripped.startswith('*'):
            # 获取基本信息
            indent = method_match.group(1)  # 这里实际获取的是修饰符，需要重新获取缩进
            # 重新获取缩进
            indent_match = re.match(r'(\s*)', line)
            indent = indent_match.group(1) if indent_match else ''
            
            modifier = method_match.group(1)
            return_type = method_match.group(2)
            method_name = method_match.group(3)
            
            # 收集完整的方法声明（可能跨多行）
            method_lines = [line]
            j = i + 1
            
            # 计算括号匹配，找到方法体的开始
            paren_count = line.count('(') - line.count(')')
            brace_count = line.count('{') - line.count('}')
            
            while j < len(lines) and (paren_count > 0 or (brace_count == 0 and '{' not in method_lines[-1])):
                method_lines.append(lines[j])
                paren_count += lines[j].count('(') - lines[j].count(')')
                brace_count += lines[j].count('{') - lines[j].count('}')
                j += 1
            
            method_text = '\n'.join(method_lines)
            
            # 找到参数括号的位置
            paren_start = method_text.find('(')
            if paren_start != -1:
                # 找到匹配的结束括号
                paren_count_temp = 0
                paren_end = -1
                for k in range(paren_start + 1, len(method_text)):
                    if method_text[k] == '(':
                        paren_count_temp += 1
                    elif method_text[k] == ')':
                        if paren_count_temp == 0:
                            paren_end = k
                            break
                        else:
                            paren_count_temp -= 1
                
                if paren_end != -1:
                    params = method_text[paren_start + 1:paren_end]
                    rest = method_text[paren_end + 1:]
                    
                    # 转换方法名为首字母小写
                    new_method_name = method_name[0].lower() + method_name[1:] if method_name else method_name
                    
                    # 重新构建方法声明
                    new_method_declaration = f'{indent}{modifier} {return_type} {new_method_name}({params})'
                    
                    # 检查是否需要添加@Override
                    # 条件：public方法，不是构造函数，不是static，不是private
                    is_constructor = (new_method_name == class_name or 
                                     new_method_name == class_name.replace('ServiceImpl', '') or
                                     new_method_name == class_name.replace('Impl', ''))
                    
                    if (modifier == 'public' and 
                        not is_constructor and
                        'static' not in method_text and
                        'final' not in method_text):
                        # 检查前面是否有注释
                        if result and result[-1].strip().endswith('*/'):
                            # 如果上一行是注释结束，在注释后添加@Override
                            result.append(f'{indent}@Override')
                        elif len(result) > 1 and result[-2].strip().endswith('*/'):
                            result.append(f'{indent}@Override')
                        else:
                            result.append(f'{indent}@Override')
                    
                    # 添加方法体
                    result.append(new_method_declaration + rest)
                    i = j
                    continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)

def convert_csharp_to_java(csharp_code, class_name):
    """将C#代码转换为Java代码"""
    
    # 1. 删除using语句
    lines = csharp_code.split('\n')
    filtered_lines = [line for line in lines if not re.match(r'^\s*using\s+[\w\.]+\s*;', line)]
    java_code = '\n'.join(filtered_lines)
    
    # 2. 提取namespace内容
    java_code = extract_namespace_content(java_code)
    
    # 3. 删除#region和#endregion
    java_code = re.sub(r'^\s*#region.*$\n', '', java_code, flags=re.MULTILINE)
    java_code = re.sub(r'^\s*#endregion.*$\n', '', java_code, flags=re.MULTILINE)
    
    # 4. 转换XML注释
    java_code = convert_xml_comments(java_code)
    
    # 5. 转换属性为字段
    property_pattern = r'(\s*)(public|private|protected)\s+(\w+)\s+([A-Z]\w*)\s*\{\s*get;\s*set;\s*\}'
    def convert_property(match):
        indent = match.group(1)
        modifier = match.group(2)
        prop_type = match.group(3)
        prop_name = match.group(4)
        
        if prop_type == 'string':
            prop_type = 'String'
        elif prop_type == 'bool':
            prop_type = 'boolean'
        
        return f'{indent}{modifier} {prop_type} {prop_name};'
    
    java_code = re.sub(property_pattern, convert_property, java_code)
    
    # 6. 转换类型
    java_code = re.sub(r'\bstring\b', 'String', java_code)
    java_code = re.sub(r'\bbool\b', 'boolean', java_code)
    java_code = re.sub(r'\bobject\b', 'Object', java_code)
    java_code = re.sub(r'\bDateTime\b', 'LocalDateTime', java_code)
    
    # 7. 提取接口名
    interface_name = None
    extends_pattern = r'class\s+\w+\s*:\s*(\w+)'
    match = re.search(extends_pattern, java_code)
    if match:
        interface_name = match.group(1)
        java_code = re.sub(r'\s*:\s*\w+', '', java_code)
    
    # 8. 先转换方法名和添加@Override（在类名修改之前）
    # 获取基础类名（去掉可能的Impl后缀）
    base_class_name = class_name.replace('Impl', '').replace('Service', '')
    java_code = convert_methods_and_add_override(java_code, base_class_name)
    
    # 9. 修改类名并添加@Service注解
    def rename_class(match):
        indent = match.group(1)
        modifier = match.group(2) if match.group(2) else 'public'
        old_class_name = match.group(3)
        
        base_name = old_class_name
        if base_name.endswith('Impl'):
            base_name = base_name[:-4]
        if base_name.endswith('Service'):
            base_name = base_name[:-7]
        
        new_class_name = f'{base_name}ServiceImpl'
        
        # 构建类声明
        class_declaration = f'{indent}{modifier} class {new_class_name}'
        if interface_name:
            class_declaration += f' implements {interface_name}'
        
        # 在类声明前添加@Service注解
        service_annotation = f'{indent}@Service'
        return f'{service_annotation}\n{class_declaration}'
    
    class_pattern = r'(\s*)(public|private|protected)?\s*class\s+(\w+)'
    java_code = re.sub(class_pattern, rename_class, java_code, count=1)
    
    # 10. 添加必要的imports
    imports = set()
    
    if '@Service' in java_code:
        imports.add('import org.springframework.stereotype.Service;')
    
    if '@Override' in java_code:
        imports.add('import java.lang.Override;')
    
    if 'LocalDateTime' in java_code:
        imports.add('import java.time.LocalDateTime;')
    if 'List' in java_code:
        imports.add('import java.util.List;')
    if 'ArrayList' in java_code:
        imports.add('import java.util.ArrayList;')
    if 'Map' in java_code:
        imports.add('import java.util.Map;')
    if 'HashMap' in java_code:
        imports.add('import java.util.HashMap;')
    
    if imports:
        import_section = '\n'.join(sorted(imports)) + '\n\n'
        java_code = import_section + java_code
    
    # 11. 确保括号匹配
    open_braces = java_code.count('{')
    close_braces = java_code.count('}')
    if open_braces > close_braces:
        java_code += '\n' + '}' * (open_braces - close_braces)
    
    # 12. 清理多余空行
    java_code = re.sub(r'\n\s*\n\s*\n', '\n\n', java_code)
    
    return java_code

def process_folder(input_folder, output_folder=None):
    """处理文件夹中的所有C#文件"""
    
    if output_folder is None:
        output_folder = os.path.join(input_folder, 'java_output')
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"创建输出目录: {output_folder}")
    
    cs_files = glob.glob(os.path.join(input_folder, '*.cs'))
    
    if not cs_files:
        print(f"在 {input_folder} 中没有找到.cs文件")
        return
    
    print(f"找到 {len(cs_files)} 个C#文件\n")
    
    for cs_file in cs_files:
        try:
            with open(cs_file, 'r', encoding='utf-8') as f:
                csharp_code = f.read()
            
            base_name = os.path.basename(cs_file)
            original_class_name = base_name.replace('.cs', '')
            
            java_code = convert_csharp_to_java(csharp_code, original_class_name)
            
            # 提取新类名
            class_match = re.search(r'class\s+(\w+)', java_code)
            if class_match:
                new_class_name = class_match.group(1)
            else:
                base = original_class_name.replace('Impl', '').replace('Service', '')
                new_class_name = f'{base}ServiceImpl'
            
            java_file_name = f'{new_class_name}.java'
            java_file_path = os.path.join(output_folder, java_file_name)
            
            with open(java_file_path, 'w', encoding='utf-8') as f:
                f.write(java_code)
            
            # 验证转换质量
            open_count = java_code.count('{')
            close_count = java_code.count('}')
            param_count = java_code.count('(')
            param_close_count = java_code.count(')')
            
            # 检查是否有@Override注解
            has_override = '@Override' in java_code
            # 检查方法名是否首字母小写
            method_names = re.findall(r'public\s+[\w<>\[\]]+\s+([a-z]\w*)\s*\(', java_code)
            
            print(f"✓ 转换成功: {base_name} -> {java_file_name}")
            if not has_override:
                print(f"  ⚠ 注意: 没有检测到@Override注解")
            if not method_names:
                print(f"  ⚠ 注意: 没有检测到转换后的方法")
            
        except Exception as e:
            print(f"✗ 转换失败: {cs_file}")
            print(f"  错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n转换完成！输出目录: {output_folder}")

def main():
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
