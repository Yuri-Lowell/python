#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASPX to Thymeleaf 转换工具
将 ASP.NET Web Forms 文件转换为 Spring Boot + Thymeleaf 模板
"""

import re
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import argparse


class ASPXToThymeleafConverter:
    """ASPX 到 Thymeleaf 转换器"""
    
    def __init__(self):
        # 存储 MasterPageFile 信息
        self.master_page_file = None
        
        # 存储需要递归处理的内容占位符
        self.content_placeholders = {}
        
    def convert_file(self, input_path: str, output_path: str = None) -> str:
        """
        转换单个 ASPX 文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径（可选）
            
        Returns:
            转换后的内容
        """
        # 读取输入文件
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 重置状态
        self.master_page_file = None
        self.content_placeholders = {}
        
        # 执行转换
        converted = self.convert(content)
        
        # 确定输出路径
        if output_path is None:
            output_path = str(Path(input_path).with_suffix('.html'))
        
        # 写入输出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(converted)
        
        print(f"✓ 转换完成: {input_path} -> {output_path}")
        return converted
    
    def convert(self, content: str) -> str:
        """
        转换 ASPX 内容为 Thymeleaf
        
        Args:
            content: ASPX 文件内容
            
        Returns:
            Thymeleaf HTML 内容
        """
        # 1. 处理页面指令
        content = self._process_directives(content)
        
        # 2. 处理服务器控件（需要递归处理）
        content = self._process_server_controls(content)
        
        # 3. 处理内联代码
        content = self._process_inline_code(content)
        
        # 4. 处理路径转换
        content = self._process_paths(content)
        
        # 5. 处理属性映射
        content = self._process_attributes(content)
        
        # 6. 处理表单
        content = self._process_forms(content)
        
        # 7. 添加 Thymeleaf 命名空间和布局配置
        content = self._add_thymeleaf_namespace(content)
        
        return content
    
    def _process_directives(self, content: str) -> str:
        """处理 ASPX 指令"""
        # 删除 Page 指令，提取 MasterPageFile
        page_pattern = r'<%@\s*Page[^%]*%>'
        master_match = re.search(r'MasterPageFile\s*=\s*"([^"]+)"', content, re.IGNORECASE)
        if master_match:
            self.master_page_file = master_match.group(1)
            # 转换 MasterPageFile 路径
            self.master_page_file = self._convert_path(self.master_page_file)
        
        content = re.sub(page_pattern, '', content, flags=re.IGNORECASE)
        
        # 删除 Master 指令
        content = re.sub(r'<%@\s*Master[^%]*%>', '', content, flags=re.IGNORECASE)
        
        # 删除 Register 指令
        content = re.sub(r'<%@\s*Register[^%]*%>', '', content, flags=re.IGNORECASE)
        
        # 删除 Content 控件标记（保留内部内容）
        # 注意：需要保留 ContentPlaceHolderID 信息用于布局
        content = re.sub(r'<asp:Content[^>]*?>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</asp:Content>', '', content, flags=re.IGNORECASE)
        
        return content
    
    def _process_server_controls(self, content: str) -> str:
        """递归处理服务器控件"""
        # 使用循环处理嵌套控件
        max_iterations = 50  # 防止无限循环
        for _ in range(max_iterations):
            original = content
            content = self._convert_controls_once(content)
            if content == original:
                break
        
        return content
    
    def _convert_controls_once(self, content: str) -> str:
        """单次转换控件（支持嵌套）"""
        
        # 1. Label 控件转换
        def convert_label(match):
            attrs = self._parse_attributes(match.group(1))
            text = attrs.get('text', '')
            css_class = attrs.get('cssclass', '')
            
            # 处理绑定表达式
            if text and ('<%#' in text or '<%=' in text):
                text = self._convert_binding_expr(text)
                return f'<span th:text="{text}" class="{css_class}"></span>'
            elif text:
                return f'<span th:text="{text}" class="{css_class}"></span>'
            else:
                return f'<span class="{css_class}"></span>'
        
        content = re.sub(r'<asp:Label\s+([^>]+?)\s*/?>', convert_label, content, flags=re.IGNORECASE)
        
        # 2. TextBox 控件转换
        def convert_textbox(match):
            attrs = self._parse_attributes(match.group(1))
            text_mode = attrs.get('textmode', '').lower()
            field_name = attrs.get('id', 'field')
            
            if text_mode == 'multiline':
                return f'<textarea th:field="*{{{field_name}}}"></textarea>'
            elif text_mode == 'password':
                return f'<input type="password" th:field="*{{{field_name}}}">'
            else:
                return f'<input type="text" th:field="*{{{field_name}}}">'
        
        content = re.sub(r'<asp:TextBox\s+([^>]+?)\s*/?>', convert_textbox, content, flags=re.IGNORECASE)
        
        # 3. Button 控件转换
        def convert_button(match):
            attrs = self._parse_attributes(match.group(1))
            text = attrs.get('text', '按钮')
            return f'<button type="submit" th:text="{text}"></button>'
        
        content = re.sub(r'<asp:Button\s+([^>]+?)\s*/?>', convert_button, content, flags=re.IGNORECASE)
        
        # 4. HyperLink 控件转换
        def convert_hyperlink(match):
            attrs = self._parse_attributes(match.group(1))
            text = attrs.get('text', '链接')
            nav_url = attrs.get('navigateurl', '#')
            nav_url = self._convert_path(nav_url)
            return f'<a th:href="@{{{nav_url}}}" th:text="{text}"></a>'
        
        content = re.sub(r'<asp:HyperLink\s+([^>]+?)\s*/?>', convert_hyperlink, content, flags=re.IGNORECASE)
        
        # 5. Image 控件转换
        def convert_image(match):
            attrs = self._parse_attributes(match.group(1))
            img_url = attrs.get('imageurl', '')
            img_url = self._convert_path(img_url)
            alt_text = attrs.get('alternatetext', '')
            return f'<img th:src="@{{{img_url}}}" alt="{alt_text}">'
        
        content = re.sub(r'<asp:Image\s+([^>]+?)\s*/?>', convert_image, content, flags=re.IGNORECASE)
        
        # 6. Repeater 控件转换
        def convert_repeater(match):
            # 提取内部内容
            inner_content = match.group(1)
            
            # 转换 ItemTemplate
            item_match = re.search(r'<ItemTemplate>(.*?)</ItemTemplate>', inner_content, re.IGNORECASE | re.DOTALL)
            if item_match:
                item_content = item_match.group(1)
            else:
                item_content = inner_content
            
            return f'<div th:each="item : ${{list}}">{item_content}</div>'
        
        content = re.sub(r'<asp:Repeater[^>]*>(.*?)</asp:Repeater>', convert_repeater, content, flags=re.IGNORECASE | re.DOTALL)
        
        # 7. GridView 转换（简化版）
        def convert_gridview(match):
            attrs = self._parse_attributes(match.group(1))
            return '<!-- TODO: GridView 需要手动转换为表格结构 -->\n<table class="table">\n    <thead>\n        <tr><th>待转换</th></tr>\n    </thead>\n    <tbody>\n        <tr th:each="item : ${list}">\n            <td th:text="${item.field}"></td>\n        </tr>\n    </tbody>\n</table>'
        
        content = re.sub(r'<asp:GridView[^>]*>(.*?)</asp:GridView>', convert_gridview, content, flags=re.IGNORECASE | re.DOTALL)
        
        # 8. DropDownList 转换
        def convert_dropdown(match):
            attrs = self._parse_attributes(match.group(1))
            field_name = attrs.get('id', 'field')
            
            # 提取 ListItem
            items = re.findall(r'<asp:ListItem[^>]*?Value="([^"]*)"[^>]*?>([^<]*)</asp:ListItem>', match.group(0), re.IGNORECASE)
            options = ''
            for value, text in items:
                options += f'<option value="{value}" th:text="{text}"></option>\n            '
            
            return f'<select th:field="*{{{field_name}}}">\n            {options}\n        </select>'
        
        content = re.sub(r'<asp:DropDownList\s+([^>]+?)>(.*?)</asp:DropDownList>', convert_dropdown, content, flags=re.IGNORECASE | re.DOTALL)
        
        # 9. CheckBox 转换
        def convert_checkbox(match):
            attrs = self._parse_attributes(match.group(1))
            field_name = attrs.get('id', 'field')
            text = attrs.get('text', '')
            return f'<input type="checkbox" th:field="*{{{field_name}}}"> <span th:text="{text}"></span>'
        
        content = re.sub(r'<asp:CheckBox\s+([^>]+?)\s*/?>', convert_checkbox, content, flags=re.IGNORECASE)
        
        # 10. Panel 控件转换
        def convert_panel(match):
            attrs = self._parse_attributes(match.group(1))
            visible = attrs.get('visible', 'true').lower()
            inner = match.group(2)
            
            if visible == 'false':
                return f'<!-- 原 Panel 已隐藏 --><div th:if="false">{inner}</div>'
            else:
                return f'<div>{inner}</div>'
        
        content = re.sub(r'<asp:Panel\s+([^>]+?)>(.*?)</asp:Panel>', convert_panel, content, flags=re.IGNORECASE | re.DOTALL)
        
        # 11. PlaceHolder 转换（移除标签，保留内容）
        content = re.sub(r'<asp:PlaceHolder[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</asp:PlaceHolder>', '', content, flags=re.IGNORECASE)
        
        return content
    
    def _process_inline_code(self, content: str) -> str:
        """处理内联代码"""
        # 处理 <%= expression %> -> th:text="${expression}"
        content = re.sub(r'<%=\s*([^%]+?)\s*%>', r'<span th:text="${\1}"></span>', content)
        
        # 处理 <%# Eval("Name") %> -> ${item.name}
        def convert_eval(match):
            expr = match.group(1).strip()
            # 处理 Eval("FieldName")
            field_match = re.search(r'Eval\("([^"]+)"\)', expr)
            if field_match:
                field = field_match.group(1)
                # 转换为驼峰命名（简单处理）
                field_lower = field[0].lower() + field[1:]
                return f'${{item.{field_lower}}}'
            return f'${{item.{expr}}}'
        
        content = re.sub(r'<%#\s*([^%]+?)\s*%>', convert_eval, content)
        
        # 处理 <%# Bind("Name") %> -> *{name}
        def convert_bind(match):
            expr = match.group(1).strip()
            field_match = re.search(r'Bind\("([^"]+)"\)', expr)
            if field_match:
                field = field_match.group(1)
                field_lower = field[0].lower() + field[1:]
                return f'*{{{field_lower}}}'
            return f'*{{{expr}}}'
        
        content = re.sub(r'<%#\s*([^%]+?)\s*%>', convert_bind, content)
        
        # 处理 <% ... %> 代码块 -> 转换为注释
        def convert_code_block(match):
            code = match.group(1)
            return f'<!-- TODO: 需手动转换代码块到 Controller\n{code}\n-->'
        
        content = re.sub(r'<%(?!@|=|#)(.*?)%>', convert_code_block, content, flags=re.DOTALL)
        
        return content
    
    def _process_paths(self, content: str) -> str:
        """处理路径转换"""
        # ~/ -> @{/
        content = re.sub(r'~/', '@{/', content)
        
        # ResolveUrl("~/path") -> @{/path}
        def convert_resolveurl(match):
            path = match.group(1)
            path = path.replace('~/', '/')
            return f'@{{{path}}}'
        
        content = re.sub(r'ResolveUrl\("([^"]+)"\)', convert_resolveurl, content)
        
        # ./page.aspx -> /page (去除扩展名)
        def convert_relative_path(match):
            path = match.group(1)
            path = re.sub(r'\./|\.\./', '/', path)
            path = re.sub(r'\.aspx$', '', path, flags=re.IGNORECASE)
            return path
        
        content = re.sub(r'(["\'])([^"\']*\.aspx[^"\']*)\1', 
                        lambda m: m.group(1) + convert_relative_path(m) + m.group(1), 
                        content, flags=re.IGNORECASE)
        
        return content
    
    def _process_attributes(self, content: str) -> str:
        """处理属性映射"""
        # CssClass -> class
        content = re.sub(r'CssClass\s*=\s*"([^"]+)"', r'class="\1"', content, flags=re.IGNORECASE)
        
        # Visible="false" -> th:if="false"
        def convert_visible(match):
            tag = match.group(0)
            if 'Visible="false"' in tag or "Visible='false'" in tag:
                # 添加 th:if="false" 属性
                tag = re.sub(r'Visible\s*=\s*["\']false["\']', '', tag, flags=re.IGNORECASE)
                if re.search(r'<[^>]+>', tag):
                    tag = re.sub(r'(<[^>\s]+)', r'\1 th:if="false"', tag)
            return tag
        
        content = re.sub(r'<[^>]*Visible\s*=\s*["\']false["\'][^>]*>', convert_visible, content, flags=re.IGNORECASE)
        
        # Enabled="false" -> disabled="disabled"
        content = re.sub(r'Enabled\s*=\s*"false"', 'disabled="disabled"', content, flags=re.IGNORECASE)
        
        # ToolTip -> title
        content = re.sub(r'ToolTip\s*=\s*"([^"]+)"', r'title="\1"', content, flags=re.IGNORECASE)
        
        # runat="server" 删除
        content = re.sub(r'\s+runat\s*=\s*["\']server["\']', '', content, flags=re.IGNORECASE)
        
        # ID 属性（添加注释以便后续使用）
        def annotate_id(match):
            tag = match.group(0)
            id_match = re.search(r'ID\s*=\s*"([^"]+)"', tag, re.IGNORECASE)
            if id_match:
                tag = re.sub(r'ID\s*=\s*"[^"]+"', '', tag, flags=re.IGNORECASE)
                tag = tag.rstrip('/>') + f' th:id="*{{{id_match.group(1)}}}" />'
            return tag
        
        content = re.sub(r'<[^>]*ID\s*=\s*"[^"]+"[^>]*>', annotate_id, content)
        
        return content
    
    def _process_forms(self, content: str) -> str:
        """处理表单转换"""
        def convert_form(match):
            form_content = match.group(1)
            # 添加 th:object 绑定
            return f'<form th:action="@{{/submit}}" th:object="${{model}}" method="post">\n{form_content}\n</form>'
        
        content = re.sub(r'<form[^>]*runat="server"[^>]*>(.*?)</form>', convert_form, content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _add_thymeleaf_namespace(self, content: str) -> str:
        """添加 Thymeleaf 命名空间和布局配置"""
        # 添加 Thymeleaf 命名空间到 html 标签
        if '<html' in content.lower():
            content = re.sub(
                r'<html([^>]*)>',
                f'<html\\1 xmlns:th="http://www.thymeleaf.org" xmlns:layout="http://www.ultraq.net.nz/thymeleaf/layout">',
                content,
                flags=re.IGNORECASE
            )
        else:
            content = f'<!DOCTYPE html>\n<html xmlns:th="http://www.thymeleaf.org" xmlns:layout="http://www.ultraq.net.nz/thymeleaf/layout">\n{content}\n</html>'
        
        # 添加布局配置
        if self.master_page_file:
            layout_comment = f'\n<!-- 原 MasterPageFile: {self.master_page_file} -->\n'
            layout_config = f'<div layout:decorate="~{{{self.master_page_file.replace(".master", "")}}}">\n'
            layout_config += '    <div layout:fragment="content">\n        \n    </div>\n</div>\n'
            content = layout_comment + layout_config + content
        
        return content
    
    def _parse_attributes(self, attr_string: str) -> Dict[str, str]:
        """解析控件属性字符串"""
        attrs = {}
        # 匹配属性名="属性值" 或 属性名='属性值'
        pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
        matches = re.findall(pattern, attr_string, re.IGNORECASE)
        for key, value in matches:
            attrs[key.lower()] = value
        return attrs
    
    def _convert_binding_expr(self, text: str) -> str:
        """转换绑定表达式"""
        # 处理 <%# Eval("Name") %>
        text = re.sub(r'<%#\s*Eval\("([^"]+)"\)\s*%>', r'${item.\1}', text)
        # 处理 <%= expression %>
        text = re.sub(r'<%=\s*([^%]+?)\s*%>', r'${\1}', text)
        return text
    
    def _convert_path(self, path: str) -> str:
        """转换路径"""
        path = path.replace('~/', '/')
        path = re.sub(r'\.aspx$', '', path, flags=re.IGNORECASE)
        return path


def convert_directory(input_dir: str, output_dir: str = None):
    """转换目录下所有 ASPX 文件"""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"错误：目录不存在 - {input_dir}")
        return
    
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    
    # 查找所有 aspx 文件
    aspx_files = list(input_path.rglob('*.aspx'))
    
    if not aspx_files:
        print(f"未找到 .aspx 文件: {input_dir}")
        return
    
    converter = ASPXToThymeleafConverter()
    
    for aspx_file in aspx_files:
        # 计算相对路径
        rel_path = aspx_file.relative_to(input_path)
        
        if output_dir:
            out_file = Path(output_dir) / rel_path.with_suffix('.html')
            out_file.parent.mkdir(parents=True, exist_ok=True)
            converter.convert_file(str(aspx_file), str(out_file))
        else:
            converter.convert_file(str(aspx_file))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='ASPX 到 Thymeleaf 模板转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s input.aspx                 # 转换单个文件
  %(prog)s ./aspx_files               # 转换目录下所有 aspx 文件
  %(prog)s input.aspx -o output.html  # 指定输出文件
  %(prog)s ./aspx_files -o ./html     # 批量转换到指定目录
        """
    )
    
    parser.add_argument('input', help='输入的 .aspx 文件路径或目录路径')
    parser.add_argument('-o', '--output', help='输出文件或目录路径', default=None)
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"错误：路径不存在 - {args.input}")
        sys.exit(1)
    
    if input_path.is_file():
        # 转换单个文件
        if not input_path.suffix.lower() == '.aspx':
            print(f"错误：文件必须是 .aspx 格式 - {args.input}")
            sys.exit(1)
        
        converter = ASPXToThymeleafConverter()
        converter.convert_file(str(input_path), args.output)
    
    elif input_path.is_dir():
        # 转换目录
        convert_directory(str(input_path), args.output)
    
    else:
        print(f"错误：无效的路径 - {args.input}")
        sys.exit(1)


if __name__ == '__main__':
    main()
