import os
import re
import shutil

def convert_cs_to_java(input_folder, output_folder=None):
    """
    转换文件夹中的所有.cs文件到Java（支持嵌套）
    :param input_folder: 输入文件夹路径
    :param output_folder: 输出文件夹路径（可选，默认为input_folder + '_java'）
    """
    if output_folder is None:
        output_folder = input_folder.rstrip('/\\') + '_java'
    
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)
    
    cs_files = []
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith('.cs'):
                cs_path = os.path.join(root, file)
                # 计算相对路径
                rel_path = os.path.relpath(cs_path, input_folder)
                java_path = os.path.join(output_folder, rel_path).replace('.cs', '.java')
                cs_files.append((cs_path, java_path))
    
    print(f"找到 {len(cs_files)} 个.cs文件")
    
    for cs_path, java_path in cs_files:
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(java_path), exist_ok=True)
            convert_file(cs_path, java_path)
            print(f"✓ 转换成功: {cs_path} -> {java_path}")
        except Exception as e:
            print(f"✗ 转换失败: {cs_path}\n  错误: {str(e)}")

def convert_file(cs_file, java_file):
    """转换单个.cs文件到.java"""
    with open(cs_file, 'r', encoding='utf-8') as f:
        cs_content = f.read()
    
    java_content = transform_content(cs_content)
    
    with open(java_file, 'w', encoding='utf-8') as f:
        f.write(java_content)

def transform_content(content):
    """执行核心转换逻辑"""
    
    # 1. 移除using语句
    content = re.sub(r'^using\s+.*?;', '', content, flags=re.MULTILINE)
    
    # 2. 处理命名空间
    content = re.sub(r'namespace\s+([\w.]+)\s*\{', r'// Package: \1\n', content)
    
    # 3. 转换类声明
    content = re.sub(r'public\s+partial\s+class', 'public class', content)
    content = re.sub(r'public\s+sealed\s+class', 'public final class', content)
    content = re.sub(r'public\s+static\s+class', 'public static class', content)
    content = re.sub(r'public\s+abstract\s+class', 'public abstract class', content)
    
    # 4. 转换数据类型
    type_mapping = {
        r'\bstring\b': 'String',
        r'\bint\b': 'int',
        r'\blong\b': 'long',
        r'\bbool\b': 'boolean',
        r'\bdouble\b': 'double',
        r'\bfloat\b': 'float',
        r'\bdecimal\b': 'BigDecimal',
        r'\bDateTime\b': 'LocalDateTime',
        r'\bvoid\b': 'void',
        r'\bobject\b': 'Object',
        r'\bbyte\[\]\b': 'byte[]',
        r'\bchar\b': 'char'
    }
    
    for cs_type, java_type in type_mapping.items():
        content = re.sub(cs_type, java_type, content)
    
    # 5. 转换方法并处理注释（含@param和@return）
    content = convert_methods_with_comments(content)
    
    # 6. 转换属性（自动生成getter/setter）
    content = convert_properties(content)
    
    # 7. 转换字符串格式化
    content = re.sub(r'\$@"([^"]*)"', r'String.format("\1")', content)
    content = re.sub(r'\{(\d+)\}', r'%s', content)
    
    # 8. 转换常用语句
    content = re.sub(r'\bConsole\.WriteLine\b', 'System.out.println', content)
    content = re.sub(r'\bConsole\.Write\b', 'System.out.print', content)
    content = re.sub(r'\bConvert\.ToInt32\b', 'Integer.parseInt', content)
    content = re.sub(r'\bToString\(\)\b', 'toString()', content)
    
    # 9. 处理out/ref参数
    content = re.sub(r'\bout\s+', '', content)
    content = re.sub(r'\bref\s+', '', content)
    
    # 10. 转换属性访问
    content = re.sub(r'\.Length\b', '.length', content)
    
    return content

def convert_methods_with_comments(content):
    """转换方法，处理XML注释为JavaDoc格式"""
    
    # 匹配方法及其前面的注释
    # 注释可能包含summary, param, returns等
    pattern = r'((?:///\s*<summary>.*?///\s*</summary>\s*)?(?:///\s*<param\s+name="([^"]+)">.*?</param>\s*)*)?(?:///\s*<returns>(.*?)</returns>\s*)?(public|private|protected|internal|static)\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)\s*(\{|;)'
    
    def method_replacer(match):
        comment_block = match.group(1) or ''
        returns_comment = match.group(3) or ''
        modifiers = match.group(4)
        return_type = match.group(5)
        method_name = match.group(6)
        parameters = match.group(7)
        body_start = match.group(8)
        
        # 方法名首字母小写
        new_method_name = method_name[0].lower() + method_name[1:] if method_name else method_name
        
        # 提取参数列表
        param_list = []
        if parameters.strip():
            for param in parameters.split(','):
                param = param.strip()
                if param:
                    parts = param.split()
                    if len(parts) >= 2:
                        param_type = parts[-2]
                        param_name = parts[-1]
                        param_list.append((param_type, param_name))
        
        # 生成JavaDoc注释
        javadoc = []
        if comment_block or param_list or returns_comment:
            javadoc.append('/**')
            
            # 提取summary
            summary_match = re.search(r'<summary>(.*?)</summary>', comment_block, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip().replace('\n', '\n * ')
                javadoc.append(f' * {summary}')
                javadoc.append(' * ')
            
            # 添加@param
            for param_type, param_name in param_list:
                # 尝试从注释中提取参数描述
                param_desc = ''
                param_pattern = rf'<param\s+name="{param_name}">(.*?)</param>'
                param_match = re.search(param_pattern, comment_block, re.DOTALL)
                if param_match:
                    param_desc = param_match.group(1).strip()
                javadoc.append(f' * @param {param_name} {param_desc}')
            
            # 添加@return
            if return_type != 'void':
                return_desc = returns_comment.strip() if returns_comment else ''
                javadoc.append(f' * @return {return_desc}')
            
            javadoc.append(' */')
        
        javadoc_text = '\n'.join(javadoc) + '\n    ' if javadoc else ''
        
        # 生成方法签名
        return f'{javadoc_text}{modifiers} {return_type} {new_method_name}({parameters}){body_start}'
    
    content = re.sub(pattern, method_replacer, content, flags=re.DOTALL | re.MULTILINE)
    return content

def convert_properties(content):
    """转换自动属性为getter/setter"""
    
    def property_replacer(match):
        access = match.group(1)  # public/private等
        prop_type = match.group(2)
        prop_name = match.group(3)
        
        field_name = prop_name[0].lower() + prop_name[1:]
        getter_name = f'get{prop_name}'
        setter_name = f'set{prop_name}'
        
        return f'''private {prop_type} {field_name};
    {access} {prop_type} {getter_name}() {{ return {field_name}; }}
    {access} void {setter_name}({prop_type} {field_name}) {{ this.{field_name} = {field_name}; }}'''
    
    content = re.sub(
        r'(public|private|protected)\s+(\w+)\s+(\w+)\s*\{\s*get;\s*set;\s*\}',
        property_replacer,
        content
    )
    
    return content

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python cs2java.py <输入文件夹> [输出文件夹]")
        print("示例: python cs2java.py ./CSharpProject ./JavaProject")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_folder):
        print(f"错误: 输入文件夹 '{input_folder}' 不存在")
        sys.exit(1)
    
    convert_cs_to_java(input_folder, output_folder)
    print("\n转换完成!")

if __name__ == "__main__":
    import sys
    main()
