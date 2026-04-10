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
    # 匹配 namespace xxx { 内容 }
    namespace_pattern = r'^\s*namespace\s+[\w\.]+\s*\{(.*?)\n\s*\}[ \t]*$'
    match = re.search(namespace_pattern, java_code, re.DOTALL | re.MULTILINE)
    if match:
        # 只保留namespace内部的内容
        java_code = match.group(1)
    
    # 3. 删除#region和#endregion
    java_code = re.sub(r'^\s*#region.*$\n', '', java_code, flags=re.MULTILINE)
    java_code = re.sub(r'^\s*#endregion.*$\n', '', java_code, flags=re.MULTILINE)
    
    # 4. 转换XML注释 /// 为 /** */
    def convert_xml_comment(match):
        comment_lines = match.group(0).split('\n')
        result = ['/**']
        for line in comment_lines:
            # 去除 /// 前缀
            cleaned = re.sub(r'^\s*///\s?', '', line)
            if cleaned.strip():
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
        rest = match.group(6)
        
        # 如果是构造函数（方法名和类名相同），不转换
        if method_name == class_name:
            return match.group(0)
        
        # 方法名首字母小写
        if method_name and len(method_name) > 0:
            java_method_name = method_name[0].lower() + method_name[1:]
            return f'{indent}{modifier} {return_type} {java_method_name}{params}{rest}'
        return match.group(0)
    
    # 匹配方法声明
    method_pattern = r'(\s*)(public|private|protected|internal)\s+([\w<>\[\]]+)\s+([A-Z]\w*)\s*\(([^)]*)\)(\s*\{)'
    java_code = re.sub(method_pattern, convert_method_signature, java_code)
    
    # 6. 转换属性为字段（去掉get;set;）
    # public string Name { get; set; } -> public String Name;
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
    
    # 8. 处理类名（确保文件名和类名对应）
    # 如果类名不是以Impl结尾，添加Impl
    if not class_name.endswith('Impl'):
        # 查找类声明并修改类名
        class_pattern = r'(\s*)(public|private|protected|internal)?\s*class\s+(\w+)'
        def rename_class(match):
            indent = match.group(1)
            modifier = match.group(2) if match.group(2) else 'public'
            old_class_name = match.group(3)
            new_class_name = old_class_name + 'Impl'
            return f'{indent}{modifier} class {new_class_name}'
        java_code = re.sub(class_pattern, rename_class, java_code, count=1)
    
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
            
            # 确定新的类名（ServiceImpl）
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
            
            # 检查是否为空
            if len(java_code.strip()) == 0:
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
