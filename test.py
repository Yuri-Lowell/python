#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版：ASPX to Thymeleaf 转换器
正确处理开标签、自闭合标签、闭合标签
"""

import re
import sys
from html.parser import HTMLParser
import xml.etree.ElementTree as ET

# ---------- 配置 ----------
TAG_MAP = {
    'asp:Label': 'span',
    'asp:TextBox': 'input',
    'asp:Button': 'button',
    'asp:HyperLink': 'a',
    'asp:Image': 'img',
    'asp:Panel': 'div',
    'asp:PlaceHolder': 'div',
    'asp:Literal': 'span',
    'asp:CheckBox': 'input',
    'asp:RadioButton': 'input',
}

ATTR_MAP = {
    'Text': 'th:text',
    'CssClass': 'class',
    'NavigateUrl': 'th:href',
    'ImageUrl': 'th:src',
    'ToolTip': 'title',
    'Enabled': 'th:disabled',
    'Visible': 'th:if',
}

REMOVE_ATTRS = ['runat', 'ID', 'OnClick', 'OnLoad', 'OnClientClick', 'DataSourceID', 'AutoGenerateColumns']

# 数据绑定表达式转换
BIND_PATTERN = re.compile(r'<%#\s*Eval\(["\']([^"\']+)["\']\)\s*%>')
BIND_PATTERN2 = re.compile(r'<%#\s*Bind\(["\']([^"\']+)["\']\)\s*%>')

def convert_bind_expr(match):
    field = match.group(1)
    return f'${{item.{field}}}'

def process_bindings(text):
    text = BIND_PATTERN.sub(convert_bind_expr, text)
    text = BIND_PATTERN2.sub(convert_bind_expr, text)
    # 处理简单 <%# 表达式 %>
    text = re.sub(r'<%#\s*([^%]+?)\s*%>', r'${\1}', text)
    return text

# ---------- 核心转换：使用栈解析确保标签正确闭合 ----------
class AspxToThymeleafConverter:
    def __init__(self):
        self.output = []
        self.tag_stack = []
    
    def convert(self, content):
        # 先移除 <%@ ... %> 指令
        content = re.sub(r'<%@.*?%>', '', content, flags=re.DOTALL)
        # 移除注释 <%-- ... --%>
        content = re.sub(r'<%--.*?--%>', '', content, flags=re.DOTALL)
        
        # 逐行或逐段处理？更好的办法：整体正则替换
        # 方案：用正则分别处理开标签、自闭合标签、闭合标签
        
        # 1. 处理自闭合标签 <asp:TextBox ... />
        def replace_self_closing(match):
            full = match.group(0)
            tag = match.group(1)
            attrs = match.group(2)
            return self._convert_open_tag(tag, attrs, self_closing=True)
        
        content = re.sub(r'<(asp:\w+)([^>]*?)\s*/>', replace_self_closing, content)
        
        # 2. 处理开标签 <asp:Label ... >
        def replace_open_tag(match):
            full = match.group(0)
            tag = match.group(1)
            attrs = match.group(2)
            return self._convert_open_tag(tag, attrs, self_closing=False)
        
        content = re.sub(r'<(asp:\w+)([^>]*?)>', replace_open_tag, content)
        
        # 3. 处理闭合标签 </asp:Label>
        def replace_close_tag(match):
            tag = match.group(1)
            new_tag = TAG_MAP.get(tag, 'div')
            return f'</{new_tag}>'
        
        content = re.sub(r'</(asp:\w+)>', replace_close_tag, content)
        
        # 4. 处理特殊容器（Repeater, GridView 等）
        content = self._process_containers(content)
        
        # 5. 处理数据绑定表达式
        content = process_bindings(content)
        
        # 6. 移除剩余的 runat="server"
        content = re.sub(r'\s+runat="server"', '', content)
        
        # 7. 添加 Thymeleaf 命名空间
        if '<html' in content.lower():
            content = re.sub(r'<html', '<html xmlns:th="http://www.thymeleaf.org"', content, count=1)
        else:
            content = '<!DOCTYPE html>\n<html xmlns:th="http://www.thymeleaf.org">\n<head><meta charset="UTF-8"><title>Converted</title></head>\n<body>\n' + content + '\n</body>\n</html>'
        
        # 8. 添加警告注释
        warning = """<!-- 
  ⚠️ 警告：此文件由脚本自动生成，仍需人工检查以下内容：
  1. 所有 th:each 的集合变量名（脚本默认为 items）
  2. 表单提交的 th:action 和 Controller 映射路径
  3. 验证错误显示改为 th:errors
  4. th:field 对应的 Java 对象属性名
  5. 母版页/内容页的布局关系（th:fragment / th:replace）
  6. 移除脚本注释中残留的 C# 代码
-->
"""
        content = warning + content
        return content
    
    def _convert_open_tag(self, tag, attrs_str, self_closing=False):
        """转换开标签或自闭合标签"""
        new_tag = TAG_MAP.get(tag, 'div')
        
        # 解析属性
        attrs = {}
        attr_re = re.compile(r'(\w+)\s*=\s*["\']([^"\']*)["\']')
        for attr_name, attr_val in attr_re.findall(attrs_str):
            if attr_name in REMOVE_ATTRS:
                continue
            if attr_name in ATTR_MAP:
                new_attr = ATTR_MAP[attr_name]
                # 转换 Text 属性中的绑定表达式
                if attr_name == 'Text':
                    attr_val = process_bindings(attr_val)
                attrs[new_attr] = attr_val
            else:
                # 保留普通属性（如 style, class）
                attrs[attr_name] = attr_val
        
        # 特殊处理 TextBox 的 TextMode
        if tag == 'asp:TextBox':
            mode_match = re.search(r'TextMode\s*=\s*["\'](\w+)["\']', attrs_str, re.IGNORECASE)
            if mode_match:
                mode = mode_match.group(1).lower()
                if mode == 'multiline':
                    new_tag = 'textarea'
                    # 移除 type 属性
                    attrs.pop('type', None)
                elif mode == 'password':
                    attrs['type'] = 'password'
                else:
                    attrs.setdefault('type', 'text')
            else:
                attrs.setdefault('type', 'text')
        
        # 特殊处理 CheckBox / RadioButton
        if tag == 'asp:CheckBox':
            attrs['type'] = 'checkbox'
        if tag == 'asp:RadioButton':
            attrs['type'] = 'radio'
            # 处理 GroupName
            group = re.search(r'GroupName\s*=\s*["\'](\w+)["\']', attrs_str)
            if group:
                attrs['name'] = group.group(1)
        
        # 构建属性字符串
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        
        if self_closing:
            # 自闭合标签
            if new_tag in ('input', 'img', 'br', 'hr'):
                return f'<{new_tag} {attr_str} />'
            else:
                # 非自闭合标签不能自闭合，转为开标签+闭合标签
                return f'<{new_tag} {attr_str}></{new_tag}>'
        else:
            return f'<{new_tag} {attr_str}>'
    
    def _process_containers(self, content):
        """处理 Repeater、GridView 等容器控件"""
        # 处理 Repeater: 将 <asp:Repeater>...ItemTemplate...</asp:Repeater> 转为 th:each
        def repl_repeater(match):
            inner = match.group(1)
            # 提取 ItemTemplate 内的内容
            item_match = re.search(r'<ItemTemplate>(.*?)</ItemTemplate>', inner, re.DOTALL | re.IGNORECASE)
            if item_match:
                inner_content = item_match.group(1)
            else:
                inner_content = inner
            # 递归转换内部内容
            inner_content = self._convert_inner(inner_content)
            # 假设数据源名称为 items，添加 TODO 注释
            return f'<div th:each="item : ${{items}}" class="repeater-item">\n{inner_content}\n</div>\n<!-- TODO: 请将 items 替换为实际集合变量名 -->'
        
        content = re.sub(r'<asp:Repeater[^>]*>(.*?)</asp:Repeater>', repl_repeater, content, flags=re.DOTALL | re.IGNORECASE)
        
        # 处理 GridView: 简单转为表格结构（需人工完善）
        def repl_gridview(match):
            inner = match.group(1)
            # 尝试提取 Columns 定义
            col_match = re.findall(r'<asp:BoundField\s+DataField="(\w+)"\s+HeaderText="([^"]+)"', inner, re.IGNORECASE)
            if col_match:
                # 生成表头
                thead = '<thead>\n<table>'
                for field, header in col_match:
                    thead += f'<th>{header}</th>'
                thead += '</tr>\n</thead>\n'
                # 生成表体（使用 th:each）
                tbody = '<tbody>\n<tr th:each="item : ${items}">\n'
                for field, _ in col_match:
                    tbody += f'<td th:text="${{item.{field}}}"></td>\n'
                tbody += '</tr>\n</tbody>\n'
                return f'<table class="gridview">\n{thead}{tbody}</table>\n<!-- TODO: 请将 items 替换为实际集合 -->'
            else:
                return '<table class="gridview">\n<!-- TODO: 请手动定义列和绑定 -->\n</table>'
        
        content = re.sub(r'<asp:GridView[^>]*>(.*?)</asp:GridView>', repl_gridview, content, flags=re.DOTALL | re.IGNORECASE)
        
        return content
    
    def _convert_inner(self, content):
        """递归转换内部内容（用于容器内）"""
        # 先转换标签
        content = re.sub(r'<(asp:\w+)([^>]*?)\s*/>', self._convert_open_tag_self_closing, content)
        content = re.sub(r'<(asp:\w+)([^>]*?)>', self._convert_open_tag_only, content)
        content = re.sub(r'</(asp:\w+)>', lambda m: f'</{TAG_MAP.get(m.group(1), "div")}>', content)
        # 转换绑定
        content = process_bindings(content)
        return content
    
    def _convert_open_tag_self_closing(self, match):
        tag = match.group(1)
        attrs = match.group(2)
        return self._convert_open_tag(tag, attrs, self_closing=True)
    
    def _convert_open_tag_only(self, match):
        tag = match.group(1)
        attrs = match.group(2)
        return self._convert_open_tag(tag, attrs, self_closing=False)

# ---------- 主函数 ----------
def main():
    if len(sys.argv) < 3:
        print("用法: python aspx2thymeleaf_fixed.py input.aspx output.html")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    with open(input_file, 'r', encoding='utf-8') as f:
        aspx_content = f.read()
    
    converter = AspxToThymeleafConverter()
    html_content = converter.convert(aspx_content)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 转换完成: {output_file}")
    print("⚠️ 请检查闭合标签是否正确，并根据注释完善动态数据绑定。")

if __name__ == '__main__':
    main()
