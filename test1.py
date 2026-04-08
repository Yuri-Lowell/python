#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业ASPX到Thymeleaf转换器
支持各种ASP.NET控件到Thymeleaf的智能转换
"""

import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class ASPXToThymeleafConverter:
    """ASPX到Thymeleaf转换器主类"""
    
    def __init__(self):
        self.conversion_log = []
        self.warning_count = 0
        self.success_count = 0
        
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        log_entry = f"[{level}] {message}"
        self.conversion_log.append(log_entry)
        print(log_entry)
    
    def extract_attributes(self, tag_content: str) -> Dict[str, str]:
        """提取HTML/ASPX标签中的所有属性"""
        attributes = {}
        # 匹配属性名="属性值" 或 属性名='属性值'
        attr_pattern = r'(\w+(?:-\w+)?)\s*=\s*["\']([^"\']*)["\']'
        for match in re.finditer(attr_pattern, tag_content):
            attr_name = match.group(1)
            attr_value = match.group(2)
            attributes[attr_name.lower()] = attr_value
        return attributes
    
    def convert_asp_label(self, match) -> str:
        """转换 asp:Label 到 th 标签"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        # 提取ID和Text
        label_id = attrs.get('id', '')
        text = attrs.get('text', '')
        css_class = attrs.get('cssclass', '')
        
        # 构建th标签
        th_attrs = []
        if label_id:
            th_attrs.append(f'th:id="{label_id}"')
        if css_class:
            th_attrs.append(f'class="{css_class}"')
        
        # 获取标签内容（如果不是自闭合）
        content_match = re.search(r'<asp:Label[^>]*>(.*?)</asp:Label>', full_tag, re.DOTALL)
        if content_match:
            inner_content = content_match.group(1)
            if inner_content.strip():
                text = inner_content
        
        attrs_str = ' ' + ' '.join(th_attrs) if th_attrs else ''
        
        if text:
            return f'<span{attrs_str} th:text="{text}"></span>'
        else:
            return f'<span{attrs_str}></span>'
    
    def convert_asp_textbox(self, match) -> str:
        """转换 asp:TextBox 到 input 标签"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        # 提取属性
        textbox_id = attrs.get('id', '')
        text_mode = attrs.get('textmode', 'SingleLine').lower()
        css_class = attrs.get('cssclass', '')
        max_length = attrs.get('maxlength', '')
        width = attrs.get('width', '')
        enabled = attrs.get('enabled', 'true')
        text = attrs.get('text', '')
        
        # 确定input类型
        input_type = 'text'
        if text_mode == 'multiline':
            # 多行文本使用textarea
            th_attrs = []
            if textbox_id:
                th_attrs.append(f'th:id="{textbox_id}"')
            if css_class:
                th_attrs.append(f'class="{css_class}"')
            if max_length:
                th_attrs.append(f'maxlength="{max_length}"')
            if width:
                th_attrs.append(f'style="width: {width};"')
            if enabled == 'false':
                th_attrs.append('disabled')
            
            attrs_str = ' ' + ' '.join(th_attrs) if th_attrs else ''
            
            if text:
                return f'<textarea{attrs_str} th:text="{text}"></textarea>'
            else:
                return f'<textarea{attrs_str}></textarea>'
        else:
            # 单行文本框
            th_attrs = []
            if textbox_id:
                th_attrs.append(f'th:id="{textbox_id}"')
            if css_class:
                th_attrs.append(f'class="{css_class}"')
            if max_length:
                th_attrs.append(f'maxlength="{max_length}"')
            if width:
                th_attrs.append(f'style="width: {width};"')
            if enabled == 'false':
                th_attrs.append('disabled')
            if text:
                th_attrs.append(f'th:value="{text}"')
            
            attrs_str = ' ' + ' '.join(th_attrs) if th_attrs else ''
            return f'<input type="{input_type}"{attrs_str} />'
    
    def convert_asp_button(self, match) -> str:
        """转换 asp:Button 到 md-outlined-button"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        button_id = attrs.get('id', '')
        text = attrs.get('text', 'Button')
        css_class = attrs.get('cssclass', '')
        onclick = attrs.get('onclick', '')
        enabled = attrs.get('enabled', 'true')
        
        # 构建md-outlined-button属性
        md_attrs = []
        if button_id:
            md_attrs.append(f'th:id="{button_id}"')
        if css_class:
            md_attrs.append(f'class="{css_class}"')
        if onclick:
            # 转换onclick事件
            onclick = re.sub(r'this\.', 'this.', onclick)
            md_attrs.append(f'th:onclick="{|{onclick}|}"')
        if enabled == 'false':
            md_attrs.append('disabled')
        
        attrs_str = ' ' + ' '.join(md_attrs) if md_attrs else ''
        return f'<md-outlined-button{attrs_str}>{text}</md-outlined-button>'
    
    def convert_asp_linkbutton(self, match) -> str:
        """转换 asp:LinkButton 到 a 标签"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        link_id = attrs.get('id', '')
        text = attrs.get('text', '')
        css_class = attrs.get('cssclass', '')
        onclick = attrs.get('onclick', '')
        enabled = attrs.get('enabled', 'true')
        
        # 构建a标签属性
        a_attrs = []
        if link_id:
            a_attrs.append(f'th:id="{link_id}"')
        if css_class:
            a_attrs.append(f'class="{css_class}"')
        if onclick:
            a_attrs.append(f'th:onclick="{|{onclick}|}"')
        if enabled == 'false':
            a_attrs.append('disabled')
        
        a_attrs.append('href="javascript:void(0)"')
        
        attrs_str = ' ' + ' '.join(a_attrs) if a_attrs else ''
        return f'<a{attrs_str} th:text="{text}"></a>'
    
    def convert_asp_dropdownlist(self, match) -> str:
        """转换 asp:DropDownList 到 select 标签"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        ddl_id = attrs.get('id', '')
        css_class = attrs.get('cssclass', '')
        enabled = attrs.get('enabled', 'true')
        
        # 提取选项
        options = []
        items_pattern = r'<asp:ListItem[^>]*>(.*?)</asp:ListItem>'
        for item_match in re.finditer(items_pattern, full_tag, re.DOTALL):
            item_attrs = self.extract_attributes(item_match.group(0))
            item_text = item_match.group(1) if item_match.group(1) else item_attrs.get('text', '')
            item_value = item_attrs.get('value', item_text)
            selected = item_attrs.get('selected', 'false') == 'true'
            
            selected_attr = ' selected' if selected else ''
            options.append(f'<option value="{item_value}"{selected_attr}>{item_text}</option>')
        
        # 构建select标签
        select_attrs = []
        if ddl_id:
            select_attrs.append(f'th:id="{ddl_id}"')
        if css_class:
            select_attrs.append(f'class="{css_class}"')
        if enabled == 'false':
            select_attrs.append('disabled')
        
        attrs_str = ' ' + ' '.join(select_attrs) if select_attrs else ''
        
        options_html = '\n            '.join(options) if options else '<option>请选择</option>'
        
        return f'<select{attrs_str}>\n            {options_html}\n        </select>'
    
    def convert_asp_checkbox(self, match) -> str:
        """转换 asp:CheckBox 到 input checkbox"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        chk_id = attrs.get('id', '')
        text = attrs.get('text', '')
        css_class = attrs.get('cssclass', '')
        checked = attrs.get('checked', 'false') == 'true'
        enabled = attrs.get('enabled', 'true')
        
        # 构建checkbox
        checkbox_attrs = []
        if chk_id:
            checkbox_attrs.append(f'th:id="{chk_id}"')
        if css_class:
            checkbox_attrs.append(f'class="{css_class}"')
        if checked:
            checkbox_attrs.append('checked')
        if enabled == 'false':
            checkbox_attrs.append('disabled')
        
        checkbox_attrs.append('type="checkbox"')
        
        attrs_str = ' ' + ' '.join(checkbox_attrs) if checkbox_attrs else ''
        
        if text:
            return f'<label><input{attrs_str} /> <span th:text="{text}"></span></label>'
        else:
            return f'<input{attrs_str} />'
    
    def convert_asp_radiobutton(self, match) -> str:
        """转换 asp:RadioButton 到 input radio"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        radio_id = attrs.get('id', '')
        group_name = attrs.get('groupname', '')
        text = attrs.get('text', '')
        css_class = attrs.get('cssclass', '')
        checked = attrs.get('checked', 'false') == 'true'
        enabled = attrs.get('enabled', 'true')
        
        # 构建radio
        radio_attrs = []
        if radio_id:
            radio_attrs.append(f'th:id="{radio_id}"')
        if group_name:
            radio_attrs.append(f'name="{group_name}"')
        if css_class:
            radio_attrs.append(f'class="{css_class}"')
        if checked:
            radio_attrs.append('checked')
        if enabled == 'false':
            radio_attrs.append('disabled')
        
        radio_attrs.append('type="radio"')
        
        attrs_str = ' ' + ' '.join(radio_attrs) if radio_attrs else ''
        
        if text:
            return f'<label><input{attrs_str} /> <span th:text="{text}"></span></label>'
        else:
            return f'<input{attrs_str} />'
    
    def convert_asp_image(self, match) -> str:
        """转换 asp:Image 到 img 标签"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        image_id = attrs.get('id', '')
        image_url = attrs.get('imageurl', '')
        alternate_text = attrs.get('alternatetext', '')
        css_class = attrs.get('cssclass', '')
        width = attrs.get('width', '')
        height = attrs.get('height', '')
        
        # 处理图片路径
        if image_url:
            # 提取文件名
            filename = os.path.basename(image_url)
            image_url = f'./images/{filename}'
        
        # 构建img标签
        img_attrs = []
        if image_id:
            img_attrs.append(f'th:id="{image_id}"')
        if image_url:
            img_attrs.append(f'th:src="@{{{image_url}}}"')
        if alternate_text:
            img_attrs.append(f'th:alt="{alternate_text}"')
        if css_class:
            img_attrs.append(f'class="{css_class}"')
        if width:
            img_attrs.append(f'width="{width}"')
        if height:
            img_attrs.append(f'height="{height}"')
        
        attrs_str = ' ' + ' '.join(img_attrs) if img_attrs else ''
        return f'<img{attrs_str} />'
    
    def convert_asp_hyperlink(self, match) -> str:
        """转换 asp:HyperLink 到 a 标签"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        link_id = attrs.get('id', '')
        navigate_url = attrs.get('navigateurl', '#')
        text = attrs.get('text', '')
        css_class = attrs.get('cssclass', '')
        target = attrs.get('target', '')
        
        # 构建a标签
        a_attrs = []
        if link_id:
            a_attrs.append(f'th:id="{link_id}"')
        if navigate_url and navigate_url != '#':
            # 处理URL路径
            if not navigate_url.startswith('http') and not navigate_url.startswith('/'):
                navigate_url = f'./{navigate_url}'
            a_attrs.append(f'th:href="@{{{navigate_url}}}"')
        else:
            a_attrs.append('href="javascript:void(0)"')
        if css_class:
            a_attrs.append(f'class="{css_class}"')
        if target:
            a_attrs.append(f'target="{target}"')
        
        attrs_str = ' ' + ' '.join(a_attrs) if a_attrs else ''
        
        if text:
            return f'<a{attrs_str} th:text="{text}"></a>'
        else:
            # 获取标签内容
            content_match = re.search(r'<asp:HyperLink[^>]*>(.*?)</asp:HyperLink>', full_tag, re.DOTALL)
            if content_match:
                inner_content = content_match.group(1)
                return f'<a{attrs_str}>{inner_content}</a>'
            return f'<a{attrs_str}></a>'
    
    def convert_asp_panel(self, match) -> str:
        """转换 asp:Panel 到 div 标签"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        panel_id = attrs.get('id', '')
        css_class = attrs.get('cssclass', '')
        visible = attrs.get('visible', 'true')
        
        # 构建div标签
        div_attrs = []
        if panel_id:
            div_attrs.append(f'th:id="{panel_id}"')
        if css_class:
            div_attrs.append(f'class="{css_class}"')
        if visible == 'false':
            div_attrs.append('th:style="display: none"')
        
        # 获取面板内容
        content_match = re.search(r'<asp:Panel[^>]*>(.*?)</asp:Panel>', full_tag, re.DOTALL)
        inner_content = content_match.group(1) if content_match else ''
        
        attrs_str = ' ' + ' '.join(div_attrs) if div_attrs else ''
        return f'<div{attrs_str}>{inner_content}</div>'
    
    def convert_asp_placeholder(self, match) -> str:
        """转换 asp:PlaceHolder 到 div 标签"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        ph_id = attrs.get('id', '')
        
        # 获取占位符内容
        content_match = re.search(r'<asp:PlaceHolder[^>]*>(.*?)</asp:PlaceHolder>', full_tag, re.DOTALL)
        inner_content = content_match.group(1) if content_match else ''
        
        if ph_id:
            return f'<div th:id="{ph_id}">{inner_content}</div>'
        else:
            return inner_content
    
    def convert_asp_repeater(self, match) -> str:
        """转换 asp:Repeater 到 th:each 循环"""
        full_tag = match.group(0)
        attrs = self.extract_attributes(full_tag)
        
        repeater_id = attrs.get('id', '')
        data_source = attrs.get('datasourceid', '')
        
        # 提取模板
        item_template = re.search(r'<ItemTemplate>(.*?)</ItemTemplate>', full_tag, re.DOTALL)
        alternating_item_template = re.search(r'<AlternatingItemTemplate>(.*?)</AlternatingItemTemplate>', full_tag, re.DOTALL)
        
        template_content = item_template.group(1) if item_template else ''
        
        # 创建循环容器
        container_attrs = []
        if repeater_id:
            container_attrs.append(f'th:id="{repeater_id}"')
        if data_source:
            container_attrs.append(f'th:each="item : ${{{data_source}}}"')
        
        attrs_str = ' ' + ' '.join(container_attrs) if container_attrs else ''
        
        # 转换模板中的绑定表达式
        template_content = self.convert_bindings(template_content)
        
        return f'<div{attrs_str}>{template_content}</div>'
    
    def convert_bindings(self, content: str) -> str:
        """转换数据绑定表达式"""
        # 转换 <%# Eval("Field") %> 到 ${item.field}
        content = re.sub(r'<%#\s*Eval\(["\']([^"\']+)["\']\)\s*%>', r'${item.\1}', content)
        # 转换 <%# Bind("Field") %> 到 *{field}
        content = re.sub(r'<%#\s*Bind\(["\']([^"\']+)["\']\)\s*%>', r'*{\1}', content)
        # 转换 <%= expression %> 到 [[${expression}]]
        content = re.sub(r'<%=([^%]+)%>', r'[[${\1}]]', content)
        
        return content
    
    def process_image_paths(self, content: str) -> str:
        """处理所有图片路径"""
        # 处理img标签中的src
        def replace_img_src(match):
            full_tag = match.group(0)
            src_match = re.search(r'src=["\']([^"\']+)["\']', full_tag)
            if src_match:
                old_path = src_match.group(1)
                filename = os.path.basename(old_path)
                new_path = f'./images/{filename}'
                return full_tag.replace(old_path, new_path)
            return full_tag
        
        content = re.sub(r'<img[^>]*src=["\'][^"\']*["\'][^>]*>', replace_img_src, content, flags=re.IGNORECASE)
        
        # 处理CSS中的背景图片
        content = re.sub(r'url\(["\']?([^"\'\)]+)["\']?\)', 
                        lambda m: f'url(./images/{os.path.basename(m.group(1))})', 
                        content)
        
        return content
    
    def add_thymeleaf_namespace(self, content: str) -> str:
        """添加Thymeleaf命名空间"""
        if 'xmlns:th="http://www.thymeleaf.org"' not in content:
            # 在html标签中添加命名空间
            content = re.sub(
                r'<html([^>]*)>',
                r'<html\1 xmlns:th="http://www.thymeleaf.org">',
                content,
                count=1,
                flags=re.IGNORECASE
            )
        return content
    
    def add_fragment_to_body(self, content: str) -> str:
        """在body标签中添加fragment"""
        if 'th:fragment' not in content:
            content = re.sub(
                r'<body([^>]*)>',
                r'<body\1 th:fragment="content">',
                content,
                flags=re.IGNORECASE
            )
        return content
    
    def convert_aspx_to_thymeleaf(self, input_file: str, output_file: Optional[str] = None) -> bool:
        """主转换方法"""
        self.log(f"开始转换文件: {input_file}")
        
        # 读取输入文件
        try:
            with open(input_file, 'r', encoding='shift-jis') as f:
                content = f.read()
            self.log("成功读取文件（Shift-JIS编码）")
        except UnicodeDecodeError:
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.log("成功读取文件（UTF-8编码）")
            except Exception as e:
                self.log(f"读取文件失败: {e}", "ERROR")
                return False
        
        original_content = content
        
        # 定义转换规则（按顺序执行）
        conversions = [
            (r'<asp:Label\b[^>]*>.*?</asp:Label>', self.convert_asp_label, 'Label'),
            (r'<asp:Label\b[^>]*?/>', self.convert_asp_label, 'Label'),
            (r'<asp:TextBox\b[^>]*>.*?</asp:TextBox>', self.convert_asp_textbox, 'TextBox'),
            (r'<asp:TextBox\b[^>]*?/>', self.convert_asp_textbox, 'TextBox'),
            (r'<asp:Button\b[^>]*>.*?</asp:Button>', self.convert_asp_button, 'Button'),
            (r'<asp:Button\b[^>]*?/>', self.convert_asp_button, 'Button'),
            (r'<asp:LinkButton\b[^>]*>.*?</asp:LinkButton>', self.convert_asp_linkbutton, 'LinkButton'),
            (r'<asp:LinkButton\b[^>]*?/>', self.convert_asp_linkbutton, 'LinkButton'),
            (r'<asp:DropDownList\b[^>]*>.*?</asp:DropDownList>', self.convert_asp_dropdownlist, 'DropDownList'),
            (r'<asp:CheckBox\b[^>]*>.*?</asp:CheckBox>', self.convert_asp_checkbox, 'CheckBox'),
            (r'<asp:CheckBox\b[^>]*?/>', self.convert_asp_checkbox, 'CheckBox'),
            (r'<asp:RadioButton\b[^>]*>.*?</asp:RadioButton>', self.convert_asp_radiobutton, 'RadioButton'),
            (r'<asp:RadioButton\b[^>]*?/>', self.convert_asp_radiobutton, 'RadioButton'),
            (r'<asp:Image\b[^>]*>.*?</asp:Image>', self.convert_asp_image, 'Image'),
            (r'<asp:Image\b[^>]*?/>', self.convert_asp_image, 'Image'),
            (r'<asp:HyperLink\b[^>]*>.*?</asp:HyperLink>', self.convert_asp_hyperlink, 'HyperLink'),
            (r'<asp:Panel\b[^>]*>.*?</asp:Panel>', self.convert_asp_panel, 'Panel'),
            (r'<asp:PlaceHolder\b[^>]*>.*?</asp:PlaceHolder>', self.convert_asp_placeholder, 'PlaceHolder'),
            (r'<asp:Repeater\b[^>]*>.*?</asp:Repeater>', self.convert_asp_repeater, 'Repeater'),
        ]
        
        # 执行转换
        for pattern, converter, control_name in conversions:
            try:
                new_content = re.sub(pattern, converter, content, flags=re.IGNORECASE | re.DOTALL)
                if new_content != content:
                    self.log(f"转换 {control_name} 控件", "SUCCESS")
                    self.success_count += 1
                    content = new_content
            except Exception as e:
                self.log(f"转换 {control_name} 失败: {e}", "WARNING")
                self.warning_count += 1
        
        # 注释掉无法转换的ASPX代码
        aspx_pattern = r'<asp:\w+[^>]*>.*?</asp:\w+>|<asp:\w+[^>]*?/>'
        def comment_aspx(match):
            matched = match.group(0)
            self.log(f"注释无法转换的ASPX代码: {matched[:100]}...", "WARNING")
            self.warning_count += 1
            return f'<!-- 需要手动处理: {matched} -->'
        
        content = re.sub(aspx_pattern, comment_aspx, content, flags=re.IGNORECASE | re.DOTALL)
        
        # 处理服务器端代码
        server_patterns = [
            (r'<%=([^%]+)%>', r'[[${\1}]]', '服务器端表达式'),
            (r'<%#([^%]+)%>', r'[[${\1}]]', '数据绑定'),
            (r'<%@[^%]+%>', '', '指令'),
            (r'<%--[^%]+--%>', '', '服务器注释'),
            (r'<script\s+runat="server"[^>]*>.*?</script>', '', '服务器脚本'),
        ]
        
        for pattern, replacement, code_type in server_patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE | re.DOTALL)
        
        # 处理图片路径
        content = self.process_image_paths(content)
        
        # 添加Thymeleaf命名空间
        content = self.add_thymeleaf_namespace(content)
        
        # 添加body fragment
        content = self.add_fragment_to_body(content)
        
        # 生成输出文件名
        if output_file is None:
            input_path = Path(input_file)
            output_file = input_path.stem + '.html'
        
        # 写入输出文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log(f"转换完成！输出文件: {output_file}", "SUCCESS")
            self.log(f"统计: 成功转换 {self.success_count} 个控件, {self.warning_count} 个警告", "INFO")
            return True
        except Exception as e:
            self.log(f"写入文件失败: {e}", "ERROR")
            return False

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python aspx_converter.py <input.aspx> [output.html]")
        print("\n示例:")
        print("  python aspx_converter.py page.aspx")
        print("  python aspx_converter.py page.aspx converted.html")
        return
    
    converter = ASPXToThymeleafConverter()
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = converter.convert_aspx_to_thymeleaf(input_file, output_file)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
