#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASPX to Thymeleaf 辅助转换脚本
用法: python aspx2thymeleaf.py input.aspx output.html
"""

import re
import sys
from html.parser import HTMLParser
from collections import OrderedDict

# ---------- 映射表 ----------
TAG_MAP = {
    'asp:Label': 'span',          # 默认转为span，也可以保留为label
    'asp:TextBox': 'input',
    'asp:Button': 'button',
    'asp:HyperLink': 'a',
    'asp:Image': 'img',
    'asp:Panel': 'div',
    'asp:PlaceHolder': 'div',
}

# 属性映射 (asp属性 -> thymeleaf属性)
ATTR_MAP = {
    'Text': 'th:text',
    'CssClass': 'class',
    'NavigateUrl': 'th:href',
    'ImageUrl': 'th:src',
    'ToolTip': 'title',
    'Enabled': 'th:disabled',     # 需要处理 true/false
}

# 需要移除的属性
REMOVE_ATTRS = ['runat', 'ID', 'OnClick', 'OnLoad', 'DataSourceID', 'AutoGenerateColumns']

# 数据绑定表达式转换
BIND_PATTERN = re.compile(r'<%#\s*Eval\(["\']([^"\']+)["\']\)\s*%>')
BIND_PATTERN2 = re.compile(r'<%#\s*Bind\(["\']([^"\']+)["\']\)\s*%>')

def convert_bind_expr(match):
    field = match.group(1)
    # 假设循环变量名为 item
    return f'${{item.{field}}}'

def process_bindings(text):
    text = BIND_PATTERN.sub(convert_bind_expr, text)
    text = BIND_PATTERN2.sub(convert_bind_expr, text)
    return text

# ---------- 简单的标签转换器 (基于正则，适用于不嵌套复杂的情况) ----------
def convert_tag(match):
    full_tag = match.group(0)
    tag_name = match.group(1)
    attrs_str = match.group(2)
    
    # 新标签名
    new_tag = TAG_MAP.get(tag_name, 'div')
    
    # 处理属性
    attrs = {}
    # 提取所有属性 name="value" 或 name='value'
    attr_re = re.compile(r'(\w+)\s*=\s*["\']([^"\']*)["\']')
    for attr_name, attr_val in attr_re.findall(attrs_str):
        if attr_name in REMOVE_ATTRS:
            continue
        if attr_name in ATTR_MAP:
            new_attr = ATTR_MAP[attr_name]
            # 转换 Text 内容
            if attr_name == 'Text':
                # 如果Text中可能包含绑定表达式
                attr_val = process_bindings(attr_val)
            attrs[new_attr] = attr_val
        else:
            # 保留其他属性（如 style, class 等）
            attrs[attr_name] = attr_val
    
    # 特殊处理 input 的 type
    if tag_name == 'asp:TextBox':
        if 'TextMode' in attrs_str:
            mode = re.search(r'TextMode\s*=\s*["\'](\w+)["\']', attrs_str)
            if mode:
                if mode.group(1).lower() == 'multiline':
                    # 变为 textarea，需要单独处理，此处简单改为 input text
                    pass
        attrs.setdefault('type', 'text')
    
    # 构建新标签
    if new_tag == 'input' and tag_name == 'asp:TextBox':
        # 自闭合标签
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<{new_tag} {attr_str} />'
    elif new_tag in ('img', 'br', 'hr'):
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<{new_tag} {attr_str} />'
    else:
        # 非自闭合，需要闭合标签，保留原内部内容
        # 由于正则无法处理嵌套，这里简单返回开标签，内部内容由外层递归处理
        # 更稳健的做法是使用栈解析，但为了简洁，我们让用户手动检查
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        # 注意：这里不包含闭合标签，我们将在整体替换后补全
        return f'<{new_tag} {attr_str}>'

def convert_aspx_to_html(content):
    # 1. 移除 <%@ ... %> 指令
    content = re.sub(r'<%@.*?%>', '', content, flags=re.DOTALL)
    
    # 2. 处理 asp:Content / asp:ContentPlaceHolder (布局相关) - 简单标记
    content = re.sub(r'<asp:ContentPlaceHolder\s+ID="(\w+)".*?>', r'<div th:fragment="\1">', content)
    content = re.sub(r'</asp:ContentPlaceHolder>', '</div>', content)
    content = re.sub(r'<asp:Content\s+ContentPlaceHolderID="(\w+)".*?>', r'<div th:replace="~{layout :: \1}">', content)
    content = re.sub(r'</asp:Content>', '</div>', content)
    
    # 3. 处理 <asp:Repeater> 和 <asp:GridView> -> th:each
    # 简单处理：将 Repeater 的 ItemTemplate 内容提取，并用 th:each 包裹
    def repl_repeater(match):
        inner = match.group(1)
        # 递归转换 inner 中的绑定
        inner = process_bindings(inner)
        # 假设数据源名称为 items，需人工调整
        return f'<div th:each="item : ${{items}}">\n{inner}\n</div>'
    
    content = re.sub(r'<asp:Repeater[^>]*>(.*?)</asp:Repeater>', repl_repeater, content, flags=re.DOTALL)
    
    # 简单处理 GridView (仅转换表格结构，实际非常复杂)
    content = re.sub(r'<asp:GridView[^>]*>(.*?)</asp:GridView>', r'<table>\1</table>', content, flags=re.DOTALL)
    
    # 4. 转换普通 asp 标签
    # 匹配 <asp:TagName ... > 或自闭合 <asp:TagName ... />
    tag_re = re.compile(r'<(asp:\w+)([^>]*?)(?:/>|>)', re.IGNORECASE)
    # 由于嵌套问题，循环多次简单替换
    for _ in range(5):  # 最多5次迭代处理嵌套
        content = tag_re.sub(convert_tag, content)
    
    # 5. 处理遗留的数据绑定表达式
    content = process_bindings(content)
    
    # 6. 移除剩余的 runat="server"
    content = re.sub(r'\s+runat="server"', '', content)
    
    # 7. 添加 Thymeleaf 命名空间和基础结构提示
    if '<html' in content.lower():
        content = re.sub(r'<html', '<html xmlns:th="http://www.thymeleaf.org"', content, count=1)
    else:
        content = '<!DOCTYPE html>\n<html xmlns:th="http://www.thymeleaf.org">\n<head><meta charset="UTF-8"><title>Converted Page</title></head>\n<body>\n' + content + '\n</body>\n</html>'
    
    # 8. 添加人工注释提醒
    warning = "<!-- 警告：此文件由脚本自动转换，仍需人工检查：\n"
    warning += " 1. 验证所有 th:each 的集合变量名是否正确\n"
    warning += " 2. 处理表单提交的 th:action 和 Controller 映射\n"
    warning += " 3. 将后端验证错误消息改为 th:errors\n"
    warning += " 4. 检查所有 th:field 是否对应正确的 Java 对象属性\n"
    warning += " 5. 将 C# 后台逻辑迁移到 Spring Controller/Service\n"
    warning += "-->\n"
    content = warning + content
    
    return content

def main():
    if len(sys.argv) < 3:
        print("用法: python aspx2thymeleaf.py input.aspx output.html")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    with open(input_file, 'r', encoding='utf-8') as f:
        aspx_content = f.read()
    
    html_content = convert_aspx_to_html(aspx_content)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"转换完成，请检查 {output_file} 并根据注释手工调整。")

if __name__ == '__main__':
    main()
