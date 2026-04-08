#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASPX to Thymeleaf HTML Converter
将ASPX文件转换为Thymeleaf HTML格式
"""

import re
import os
import sys
from pathlib import Path

def convert_aspx_to_thymeleaf(input_file, output_file=None):
    """
    将ASPX文件转换为Thymeleaf HTML
    
    Args:
        input_file: 输入的ASPX文件路径
        output_file: 输出的HTML文件路径（如果为None，则自动生成）
    
    Returns:
        bool: 转换是否成功
    """
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：文件不存在 - {input_file}")
        return False
    
    # 读取输入文件（shift-jis编码）
    try:
        with open(input_file, 'r', encoding='shift-jis') as f:
            content = f.read()
        print(f"成功读取文件（shift-jis编码）: {input_file}")
    except UnicodeDecodeError:
        try:
            # 尝试使用utf-8作为备选
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"成功读取文件（utf-8编码）: {input_file}")
        except Exception as e:
            print(f"错误：无法读取文件 - {e}")
            return False
    
    original_content = content
    
    # 执行转换
    converted_lines = []
    lines = content.splitlines()
    
    # 标记是否需要转换body
    body_has_fragment = False
    
    for line_num, line in enumerate(lines, 1):
        converted_line = line
        
        # 1. 转换按钮：<asp:Button> 到 <md-outlined-button>
        # 匹配自闭合的asp:Button
        button_pattern_self_closed = r'<asp:Button\s+([^>]*?)\s*/>'
        # 匹配非自闭合的asp:Button
        button_pattern_closed = r'<asp:Button\s+([^>]*?)>(.*?)</asp:Button>'
        
        def extract_button_attributes(attrs_text):
            """提取按钮属性并转换为md-outlined-button格式"""
            # 提取ID
            id_match = re.search(r'ID="([^"]+)"', attrs_text, re.IGNORECASE)
            button_id = id_match.group(1) if id_match else ""
            
            # 提取Text
            text_match = re.search(r'Text="([^"]+)"', attrs_text, re.IGNORECASE)
            button_text = text_match.group(1) if text_match else "Button"
            
            # 提取其他属性（如CssClass, OnClick等）
            other_attrs = []
            # 排除已处理的ID和Text
            remaining_attrs = re.sub(r'ID="[^"]+"', '', attrs_text, flags=re.IGNORECASE)
            remaining_attrs = re.sub(r'Text="[^"]+"', '', remaining_attrs, flags=re.IGNORECASE)
            
            # 转换CssClass为class
            class_match = re.search(r'CssClass="([^"]+)"', remaining_attrs, re.IGNORECASE)
            if class_match:
                other_attrs.append(f'class="{class_match.group(1)}"')
                remaining_attrs = re.sub(r'CssClass="[^"]+"', '', remaining_attrs, flags=re.IGNORECASE)
            
            # 保留其他属性
            other_attrs_str = ' '.join([attr for attr in remaining_attrs.split() if attr.strip()])
            
            # 构建新的按钮标签
            attrs_list = []
            if button_id:
                attrs_list.append(f'th:id="{button_id}"')
            if button_text:
                attrs_list.append(f'>{button_text}</md-outlined-button>')
                # 如果有其他属性，添加到开始标签
                if other_attrs_str or attrs_list:
                    attrs_str = ' '.join([a for a in attrs_list if not a.startswith('>')])
                    return f'<md-outlined-button {attrs_str} {other_attrs_str}'
            else:
                # 如果没有文本，使用自闭合形式
                attrs_str = ' '.join(attrs_list)
                return f'<md-outlined-button {attrs_str} {other_attrs_str} />'
        
        # 处理按钮转换
        def convert_button_self_closed(match):
            attrs = match.group(1)
            try:
                return extract_button_attributes(attrs)
            except Exception as e:
                print(f"警告：第{line_num}行按钮转换失败 - {e}")
                return f'<!-- 无法转换的按钮: {match.group(0)} -->'
        
        def convert_button_closed(match):
            attrs = match.group(1)
            content_between = match.group(2)
            try:
                result = extract_button_attributes(attrs)
                # 如果标签内有内容，需要特殊处理
                if content_between.strip():
                    return f'{result}>{content_between}</md-outlined-button>'
                return result
            except Exception as e:
                print(f"警告：第{line_num}行按钮转换失败 - {e}")
                return f'<!-- 无法转换的按钮: {match.group(0)} -->'
        
        converted_line = re.sub(button_pattern_self_closed, convert_button_self_closed, converted_line, flags=re.IGNORECASE)
        converted_line = re.sub(button_pattern_closed, convert_button_closed, converted_line, flags=re.IGNORECASE | re.DOTALL)
        
        # 2. 转换图片路径为 ./images
        # 匹配img标签中的src属性
        def convert_image_path(match):
            full_tag = match.group(0)
            src_match = re.search(r'src=["\']([^"\']+)["\']', full_tag)
            if src_match:
                original_path = src_match.group(1)
                # 提取文件名
                filename = os.path.basename(original_path)
                new_path = f'./images/{filename}'
                new_tag = full_tag.replace(original_path, new_path)
                return new_tag
            return full_tag
        
        # 处理图片标签
        img_pattern = r'<img[^>]*src=["\'][^"\']*["\'][^>]*>'
        converted_line = re.sub(img_pattern, convert_image_path, converted_line, flags=re.IGNORECASE)
        
        # 处理背景图片等CSS中的图片路径
        bg_pattern = r'background(-image)?\s*:\s*url\(["\']?([^"\'\)]+)["\']?\)'
        def convert_bg_path(match):
            original_path = match.group(2)
            filename = os.path.basename(original_path)
            new_path = f'./images/{filename}'
            return match.group(0).replace(original_path, new_path)
        converted_line = re.sub(bg_pattern, convert_bg_path, converted_line, flags=re.IGNORECASE)
        
        # 3. 在body标签上添加 th:fragment="content"
        body_pattern = r'<body([^>]*)>'
        def add_th_fragment(match):
            attrs = match.group(1)
            if 'th:fragment' not in attrs:
                if attrs:
                    return f'<body{attrs} th:fragment="content">'
                else:
                    return '<body th:fragment="content">'
            return match.group(0)
        
        if '<body' in converted_line.lower():
            converted_line = re.sub(body_pattern, add_th_fragment, converted_line, flags=re.IGNORECASE)
            body_has_fragment = True
        
        # 4. 注释掉无法转换的ASPX控件
        # 匹配其他ASP.NET服务器控件
        aspx_controls = [
            (r'<asp:TextBox[^>]*?>.*?</asp:TextBox>', 'asp:TextBox'),
            (r'<asp:TextBox[^>]*?/>', 'asp:TextBox'),
            (r'<asp:Label[^>]*?>.*?</asp:Label>', 'asp:Label'),
            (r'<asp:Label[^>]*?/>', 'asp:Label'),
            (r'<asp:GridView[^>]*?>.*?</asp:GridView>', 'asp:GridView'),
            (r'<asp:GridView[^>]*?/>', 'asp:GridView'),
            (r'<asp:DropDownList[^>]*?>.*?</asp:DropDownList>', 'asp:DropDownList'),
            (r'<asp:DropDownList[^>]*?/>', 'asp:DropDownList'),
            (r'<asp:CheckBox[^>]*?>.*?</asp:CheckBox>', 'asp:CheckBox'),
            (r'<asp:CheckBox[^>]*?/>', 'asp:CheckBox'),
            (r'<asp:RadioButton[^>]*?>.*?</asp:RadioButton>', 'asp:RadioButton'),
            (r'<asp:RadioButton[^>]*?/>', 'asp:RadioButton'),
            (r'<asp:Panel[^>]*?>.*?</asp:Panel>', 'asp:Panel'),
            (r'<asp:Panel[^>]*?/>', 'asp:Panel'),
            (r'<asp:PlaceHolder[^>]*?>.*?</asp:PlaceHolder>', 'asp:PlaceHolder'),
            (r'<asp:PlaceHolder[^>]*?/>', 'asp:PlaceHolder'),
            (r'<asp:HyperLink[^>]*?>.*?</asp:HyperLink>', 'asp:HyperLink'),
            (r'<asp:HyperLink[^>]*?/>', 'asp:HyperLink'),
            (r'<asp:Image[^>]*?>.*?</asp:Image>', 'asp:Image'),
            (r'<asp:Image[^>]*?/>', 'asp:Image'),
            (r'<asp:LinkButton[^>]*?>.*?</asp:LinkButton>', 'asp:LinkButton'),
            (r'<asp:LinkButton[^>]*?/>', 'asp:LinkButton'),
        ]
        
        for pattern, control_name in aspx_controls:
            matches = re.finditer(pattern, converted_line, re.IGNORECASE | re.DOTALL)
            for match in matches:
                matched_text = match.group(0)
                # 注释掉无法转换的控件
                commented = f'<!-- 无法转换的{control_name}控件，需要手动处理: {matched_text} -->'
                converted_line = converted_line.replace(matched_text, commented)
        
        # 5. 处理服务器端代码块 <%= %> 和 <%# %> 等
        server_code_patterns = [
            (r'<%=([^%]+)%>', '服务器端表达式'),
            (r'<%#([^%]+)%>', '数据绑定表达式'),
            (r'<%\$([^%]+)%>', '资源表达式'),
            (r'<%@[^%]+%>', '指令'),
            (r'<%--[^%]+--%>', '服务器端注释'),
            (r'<script\s+runat="server"[^>]*>.*?</script>', '服务器端脚本'),
            (r'<%!?[^=][^%]*%>', '服务器端代码块'),
        ]
        
        for pattern, code_type in server_code_patterns:
            def comment_server_code(match, ct=code_type):
                return f'<!-- 无法转换的{ct}: {match.group(0)} -->'
            converted_line = re.sub(pattern, comment_server_code, converted_line, flags=re.IGNORECASE | re.DOTALL)
        
        converted_lines.append(converted_line)
    
    # 重新组合转换后的内容
    converted_content = '\n'.join(converted_lines)
    
    # 如果没有找到body标签，在文件开头添加警告
    if not body_has_fragment:
        warning = '<!-- 警告：未找到body标签，请手动添加 th:fragment="content" -->\n'
        converted_content = warning + converted_content
    
    # 生成输出文件名
    if output_file is None:
        input_path = Path(input_file)
        output_file = input_path.stem + '_converted.html'
    
    # 写入输出文件（使用utf-8编码）
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(converted_content)
        print(f"成功转换并保存到: {output_file}")
        return True
    except Exception as e:
        print(f"错误：无法写入输出文件 - {e}")
        return False

def batch_convert(directory):
    """批量转换目录中的所有ASPX文件"""
    aspx_files = list(Path(directory).glob('*.aspx'))
    if not aspx_files:
        print(f"在目录 {directory} 中未找到ASPX文件")
        return
    
    print(f"找到 {len(aspx_files)} 个ASPX文件")
    success_count = 0
    
    for aspx_file in aspx_files:
        print(f"\n正在转换: {aspx_file}")
        if convert_aspx_to_thymeleaf(str(aspx_file)):
            success_count += 1
    
    print(f"\n转换完成！成功: {success_count}/{len(aspx_files)}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  转换单个文件: python aspx_converter.py <input_file.aspx> [output_file.html]")
        print("  批量转换: python aspx_converter.py --batch <directory>")
        return
    
    if sys.argv[1] == '--batch':
        if len(sys.argv) < 3:
            print("请指定要转换的目录")
            return
        batch_convert(sys.argv[2])
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        convert_aspx_to_thymeleaf(input_file, output_file)

if __name__ == "__main__":
    main()
