#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASPX to Thymeleaf 转换器 - 完整修正版
修正所有语法错误，特别是正则表达式中的花括号转义
"""

import re
from pathlib import Path
from collections import defaultdict

class HTML5AttributeConverter:
    """HTML5 属性转换器"""
    
    DEPRECATED_ATTRIBUTES = {
        'align': {
            'left': 'text-align: left;',
            'right': 'text-align: right;',
            'center': 'text-align: center;',
            'justify': 'text-align: justify;',
            'top': 'vertical-align: top;',
            'middle': 'vertical-align: middle;',
            'bottom': 'vertical-align: bottom;',
        },
        'valign': {
            'top': 'vertical-align: top;',
            'middle': 'vertical-align: middle;',
            'bottom': 'vertical-align: bottom;',
        },
        'bgcolor': 'background-color: {value};',
        'background': 'background-image: url("{value}");',
        'width': 'width: {value}px;',
        'height': 'height: {value}px;',
        'cellspacing': 'border-spacing: {value}px;',
        'cellpadding': 'padding: {value}px;',
        'border': 'border: {value}px solid;',
        'hspace': 'margin-left: {value}px; margin-right: {value}px;',
        'vspace': 'margin-top: {value}px; margin-bottom: {value}px;',
        'color': 'color: {value};',
        'face': 'font-family: {value};',
        'size': {
            '1': 'font-size: 12px;',
            '2': 'font-size: 14px;',
            '3': 'font-size: 16px;',
            '4': 'font-size: 18px;',
            '5': 'font-size: 20px;',
            '6': 'font-size: 24px;',
            '7': 'font-size: 32px;',
        },
        'type': {
            'disc': 'list-style-type: disc;',
            'circle': 'list-style-type: circle;',
            'square': 'list-style-type: square;',
            '1': 'list-style-type: decimal;',
            'A': 'list-style-type: upper-alpha;',
            'a': 'list-style-type: lower-alpha;',
            'I': 'list-style-type: upper-roman;',
            'i': 'list-style-type: lower-roman;',
        },
        'nowrap': 'white-space: nowrap;',
        'noshade': 'border: none; background-color: #cccccc; height: 2px;',
    }
    
    def __init__(self):
        self.conversion_log = []
    
    def convert_attributes_to_style(self, tag_name, attributes):
        """将废弃属性转换为 style 属性"""
        styles = []
        new_attributes = {}
        
        for attr_name, attr_value in attributes.items():
            attr_lower = attr_name.lower()
            
            if attr_lower == 'style':
                if attr_value and not attr_value.isspace():
                    styles.append(attr_value.rstrip(';'))
                continue
            
            if attr_lower in self.DEPRECATED_ATTRIBUTES:
                rule = self.DEPRECATED_ATTRIBUTES[attr_lower]
                if isinstance(rule, dict):
                    if str(attr_value) in rule:
                        styles.append(rule[str(attr_value)])
                        self._log_conversion(tag_name, attr_name, attr_value, rule[str(attr_value)])
                    else:
                        new_attributes[attr_name] = attr_value
                elif isinstance(rule, str):
                    css = rule.format(value=attr_value)
                    styles.append(css)
                    self._log_conversion(tag_name, attr_name, attr_value, css)
                else:
                    new_attributes[attr_name] = attr_value
            else:
                if attr_lower not in ['runat']:
                    new_attributes[attr_name] = attr_value
        
        if styles:
            new_attributes['style'] = '; '.join(styles)
        
        return new_attributes
    
    def convert_inline_tags(self, content):
        """转换内联样式标签"""
        def convert_font(match):
            attrs = self._parse_attributes(match.group(1))
            styles = []
            if 'color' in attrs:
                styles.append(f'color: {attrs["color"]};')
            if 'face' in attrs:
                styles.append(f'font-family: {attrs["face"]};')
            if 'size' in attrs:
                size_map = {'1': '12px', '2': '14px', '3': '16px', 
                           '4': '18px', '5': '20px', '6': '24px', '7': '32px'}
                size = size_map.get(attrs['size'], '16px')
                styles.append(f'font-size: {size};')
            inner = match.group(2)
            if styles:
                return f'<span style="{"; ".join(styles)}">{inner}</span>'
            return inner
        
        content = re.sub(r'<font\s+([^>]*)>(.*?)</font>', convert_font, content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<center>(.*?)</center>', r'<div style="text-align: center;">\1</div>', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<strike>(.*?)</strike>', r'<span style="text-decoration: line-through;">\1</span>', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<u>(.*?)</u>', r'<span style="text-decoration: underline;">\1</span>', content, flags=re.DOTALL | re.IGNORECASE)
        
        return content
    
    def convert_table_attributes(self, content):
        """转换表格属性"""
        def convert_table(match):
            tag_content = match.group(0)
            attrs = self._parse_tag_attributes(tag_content)
            inner = re.search(r'<table[^>]*>(.*)<table>', tag_content, re.DOTALL | re.IGNORECASE)
            inner_content = inner.group(1) if inner else ''
            new_attrs = self.convert_attributes_to_style('table', attrs)
            attr_str = self._build_attributes(new_attrs)
            return f'<table{attr_str}>{inner_content}</table>'
        
        content = re.sub(r'<table[^>]*>.*?</table>', convert_table, content, flags=re.DOTALL | re.IGNORECASE)
        
        def convert_cell(match, tag='td'):
            attrs = self._parse_tag_attributes(match.group(0))
            new_attrs = self.convert_attributes_to_style(tag, attrs)
            attr_str = self._build_attributes(new_attrs)
            return f'<{tag}{attr_str}>'
        
        content = re.sub(r'<td[^>]*>', lambda m: convert_cell(m, 'td'), content, flags=re.IGNORECASE)
        content = re.sub(r'<th[^>]*>', lambda m: convert_cell(m, 'th'), content, flags=re.IGNORECASE)
        content = re.sub(r'<tr[^>]*>', lambda m: convert_cell(m, 'tr'), content, flags=re.IGNORECASE)
        
        return content
    
    def convert_img_attributes(self, content):
        """转换图片属性"""
        def convert_img(match):
            attrs = self._parse_tag_attributes(match.group(0))
            styles = []
            if 'border' in attrs:
                styles.append(f'border: {attrs["border"]}px solid;')
            if 'hspace' in attrs:
                styles.append(f'margin-left: {attrs["hspace"]}px; margin-right: {attrs["hspace"]}px;')
            if 'vspace' in attrs:
                styles.append(f'margin-top: {attrs["vspace"]}px; margin-bottom: {attrs["vspace"]}px;')
            if 'align' in attrs:
                align_map = {'left': 'float: left;', 'right': 'float: right;', 
                            'top': 'vertical-align: top;', 'middle': 'vertical-align: middle;', 
                            'bottom': 'vertical-align: bottom;'}
                if attrs['align'] in align_map:
                    styles.append(align_map[attrs['align']])
            
            new_attrs = {k: v for k, v in attrs.items() if k not in ['border', 'hspace', 'vspace', 'align']}
            if styles:
                new_attrs['style'] = '; '.join(styles)
            attr_str = self._build_attributes(new_attrs)
            return f'<img{attr_str} />'
        
        content = re.sub(r'<img[^>]*/?>', convert_img, content, flags=re.IGNORECASE)
        return content
    
    def convert_hr_attributes(self, content):
        """转换水平线属性"""
        def convert_hr(match):
            attrs = self._parse_tag_attributes(match.group(0))
            styles = []
            if 'size' in attrs:
                styles.append(f'height: {attrs["size"]}px;')
            if 'width' in attrs:
                width = attrs['width']
                if width.endswith('%'):
                    styles.append(f'width: {width};')
                else:
                    styles.append(f'width: {width}px;')
            if 'color' in attrs:
                styles.append(f'background-color: {attrs["color"]};')
            if 'noshade' in attrs:
                styles.append('border: none;')
            if 'align' in attrs:
                align_styles = {
                    'left': 'margin-left: 0; margin-right: auto;',
                    'center': 'margin-left: auto; margin-right: auto;',
                    'right': 'margin-left: auto; margin-right: 0;'
                }
                if attrs['align'] in align_styles:
                    styles.append(align_styles[attrs['align']])
            
            if styles:
                return f'<hr style="{"; ".join(styles)}" />'
            return '<hr />'
        
        content = re.sub(r'<hr[^>]*/?>', convert_hr, content, flags=re.IGNORECASE)
        return content
    
    def convert_generic_attributes(self, content):
        """通用属性转换"""
        def convert_generic_tag(match):
            tag_name = match.group(1)
            attrs_str = match.group(2)
            closing = match.group(3) or ''
            
            if tag_name.lower() in ['meta', 'link', 'br', 'hr', 'img', 'input', '!DOCTYPE']:
                return match.group(0)
            
            attrs = self._parse_attributes(attrs_str)
            new_attrs = self.convert_attributes_to_style(tag_name, attrs)
            attr_str = self._build_attributes(new_attrs)
            return f'<{tag_name}{attr_str}{closing}>'
        
        pattern = r'<(\w+)(\s+[^>]*?)(\s*/?)>'
        content = re.sub(pattern, convert_generic_tag, content, flags=re.IGNORECASE)
        return content
    
    def convert_all(self, content):
        """执行所有转换"""
        content = self.convert_inline_tags(content)
        content = self.convert_table_attributes(content)
        content = self.convert_img_attributes(content)
        content = self.convert_hr_attributes(content)
        content = self.convert_generic_attributes(content)
        return content
    
    def _parse_attributes(self, attr_str):
        """解析属性字符串"""
        attrs = {}
        pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))'
        for match in re.finditer(pattern, attr_str):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4) or ''
            attrs[key.lower()] = value
        return attrs
    
    def _parse_tag_attributes(self, tag_str):
        """解析标签中的属性"""
        attr_match = re.search(r'<[^>\s]+\s+([^>]*)>', tag_str)
        if attr_match:
            return self._parse_attributes(attr_match.group(1))
        return {}
    
    def _build_attributes(self, attrs):
        """构建属性字符串"""
        if not attrs:
            return ''
        attr_parts = []
        for key, value in attrs.items():
            if value is True or value == '':
                attr_parts.append(key)
            else:
                value = str(value).replace('"', '&quot;')
                attr_parts.append(f'{key}="{value}"')
        return ' ' + ' '.join(attr_parts) if attr_parts else ''
    
    def _log_conversion(self, tag, attr, value, css):
        """记录转换日志"""
        self.conversion_log.append({
            'tag': tag,
            'attribute': attr,
            'value': value,
            'converted_to': css
        })
    
    def get_conversion_report(self):
        """获取转换报告"""
        if not self.conversion_log:
            return "未发现需要转换的 HTML5 废弃属性"
        report = ["\n=== HTML5 属性转换报告 ===\n", f"共转换 {len(self.conversion_log)} 个废弃属性\n"]
        stats = defaultdict(lambda: defaultdict(int))
        for log in self.conversion_log:
            stats[log['tag']][log['attribute']] += 1
        for tag, attrs in stats.items():
            report.append(f"<{tag}> 标签:")
            for attr, count in attrs.items():
                report.append(f"  - {attr}: {count} 次")
        return '\n'.join(report)


class CompleteConverter:
    """完整转换器"""
    
    def __init__(self):
        self.html5_converter = HTML5AttributeConverter()
        self.conversion_count = 0
        self.error_count = 0
    
    def extract_attributes(self, tag_content):
        """提取标签属性"""
        attributes = {}
        attr_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
        for match in re.finditer(attr_pattern, tag_content):
            key, value = match.groups()
            if key.lower() == 'cssclass':
                key = 'class'
            attributes[key] = value
        return attributes
    
    def convert_binding_expression(self, value):
        """转换数据绑定表达式"""
        if not value:
            return ''
        value = re.sub(r'<%#\s*Eval\("([^"]+)"\)\s*%>', r'${item.\1 ?: ""}', value)
        value = re.sub(r'<%#\s*Bind\("([^"]+)"\)\s*%>', r'${item.\1 ?: ""}', value)
        value = re.sub(r'<%=\s*([^%]+)\s*%>', r'${\1 ?: ""}', value)
        value = re.sub(r'<%:\s*([^%]+)\s*%>', r'${\1 ?: ""}', value)
        return value
    
    def get_controller_example(self):
        """生成 Controller 示例代码"""
        return '''// ============================================================
// Spring MVC Controller 变量设置示例
// ============================================================
@Controller
public class YourController {
    
    @GetMapping("/your-page")
    public String yourPage(Model model) {
        // 1. 列表数据 (Repeater, DataList, GridView)
        List<YourEntity> dataList = yourService.getList();
        model.addAttribute("dataList", dataList);
        
        // 2. 下拉框选项 (DropDownList)
        List<SelectOption> selectOptions = Arrays.asList(
            new SelectOption("1", "选项1"),
            new SelectOption("2", "选项2")
        );
        model.addAttribute("selectOptions", selectOptions);
        
        // 3. 复选框选项 (CheckBoxList)
        model.addAttribute("checkboxOptions", selectOptions);
        
        // 4. 单选框选项 (RadioButtonList)
        model.addAttribute("radioOptions", selectOptions);
        
        // 5. 菜单项 (Menu)
        List<MenuItem> menuItems = getMenuItems();
        model.addAttribute("menuItems", menuItems);
        
        // 6. 树形节点 (TreeView)
        List<TreeNode> treeNodes = getTreeNodes();
        model.addAttribute("treeNodes", treeNodes);
        
        // 7. 面包屑 (SiteMapPath)
        List<Breadcrumb> breadcrumbs = getBreadcrumbs();
        model.addAttribute("breadcrumbs", breadcrumbs);
        
        // 8. 广告列表 (AdRotator)
        model.addAttribute("adList", adList);
        
        // 9. 表单数据 (FormView, DetailsView)
        model.addAttribute("formData", formData);
        
        // 10. 表格数据 (GridView 列定义)
        List<String> gridColumns = Arrays.asList("ID", "名称", "状态");
        model.addAttribute("gridColumns", gridColumns);
        
        return "your-page";
    }
}
'''
    
    # ==================== ASP 控件转换方法 ====================
    
    def convert_label(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = self.convert_binding_expression(attrs.get('text', ''))
        css_class = attrs.get('class', '')
        if css_class:
            return f'<span class="{css_class}" th:text="{text}"></span>'
        return f'<span th:text="{text}"></span>' if text else '<span></span>'
    
    def convert_textbox(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text_mode = attrs.get('textmode', '').lower()
        text = self.convert_binding_expression(attrs.get('text', ''))
        css_class = attrs.get('class', '')
        class_attr = f' class="{css_class}"' if css_class else ''
        
        if text_mode == 'password':
            return f'<input type="password" th:value="{text}"{class_attr} />'
        elif text_mode == 'multiline':
            return f'<textarea th:text="{text}"{class_attr}></textarea>'
        else:
            return f'<input type="text" th:value="{text}"{class_attr} />'
    
    def convert_button(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = self.convert_binding_expression(attrs.get('text', '按钮'))
        return f'<button type="submit" th:text="{text}"></button>'
    
    def convert_linkbutton(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = self.convert_binding_expression(attrs.get('text', '链接'))
        return f'<a href="javascript:void(0)" th:text="{text}"></a>'
    
    def convert_imagebutton(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        image_url = attrs.get('imageurl', '')
        alt_text = attrs.get('alternatetext', '')
        return f'<img src="{image_url}" alt="{alt_text}" style="cursor: pointer;" />'
    
    def convert_hyperlink(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = self.convert_binding_expression(attrs.get('text', ''))
        navigate_url = attrs.get('navigateurl', '#')
        return f'<a href="{navigate_url}" th:text="{text}"></a>'
    
    def convert_image(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        image_url = attrs.get('imageurl', '')
        alt_text = attrs.get('alternatetext', '')
        return f'<img src="{image_url}" alt="{alt_text}" />'
    
    def convert_panel(self, match):
        content = match.group(1) if match.groups() else ''
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        css_class = attrs.get('class', '')
        class_attr = f' class="{css_class}"' if css_class else ''
        return f'<div{class_attr}>{content}</div>'
    
    def convert_placeholder(self, match):
        content = match.group(1) if match.groups() else ''
        return content
    
    def convert_literal(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = self.convert_binding_expression(attrs.get('text', ''))
        return text
    
    def convert_checkbox(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = self.convert_binding_expression(attrs.get('text', ''))
        checked = attrs.get('checked', '').lower() == 'true'
        checked_attr = ' checked' if checked else ''
        
        if text:
            return f'<label><input type="checkbox"{checked_attr} /> <span th:text="{text}"></span></label>'
        return f'<input type="checkbox"{checked_attr} />'
    
    def convert_checkboxlist(self, match):
        return '''<!-- CheckBoxList: 使用 checkboxOptions 变量 -->
<div th:if="${checkboxOptions != null and !checkboxOptions.isEmpty()}">
    <label th:each="opt : ${checkboxOptions}" class="checkbox-item">
        <input type="checkbox" th:value="${opt.value}" />
        <span th:text="${opt.label}"></span>
    </label>
</div>
<div th:unless="${checkboxOptions != null and !checkboxOptions.isEmpty()}">
    <!-- 请在 Controller 中添加: model.addAttribute("checkboxOptions", checkboxList); -->
</div>'''
    
    def convert_radiobutton(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = self.convert_binding_expression(attrs.get('text', ''))
        group_name = attrs.get('groupname', 'radioGroup')
        checked = attrs.get('checked', '').lower() == 'true'
        checked_attr = ' checked' if checked else ''
        
        if text:
            return f'<label><input type="radio" name="{group_name}"{checked_attr} /> <span th:text="{text}"></span></label>'
        return f'<input type="radio" name="{group_name}"{checked_attr} />'
    
    def convert_radiobuttonlist(self, match):
        return '''<!-- RadioButtonList: 使用 radioOptions 变量 -->
<div th:if="${radioOptions != null and !radioOptions.isEmpty()}">
    <label th:each="opt : ${radioOptions}" class="radio-item">
        <input type="radio" name="radioGroup" th:value="${opt.value}" />
        <span th:text="${opt.label}"></span>
    </label>
</div>
<div th:unless="${radioOptions != null and !radioOptions.isEmpty()}">
    <!-- 请在 Controller 中添加: model.addAttribute("radioOptions", radioList); -->
</div>'''
    
    def convert_dropdownlist(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        css_class = attrs.get('class', '')
        class_attr = f' class="{css_class}"' if css_class else ''
        
        return f'''<!-- DropDownList: 使用 selectOptions 变量 -->
<select{class_attr} th:if="${{selectOptions != null and !selectOptions.isEmpty()}}">
    <option value="">请选择</option>
    <option th:each="opt : ${{selectOptions}}" th:value="${{opt.value}}" th:text="${{opt.label}}"></option>
</select>
<select class="disabled" disabled th:unless="${{selectOptions != null and !selectOptions.isEmpty()}}">
    <option>无数据</option>
</select>'''
    
    def convert_listbox(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        css_class = attrs.get('class', '')
        class_attr = f' class="{css_class}"' if css_class else ''
        
        return f'''<!-- ListBox: 使用 selectOptions 变量 -->
<select multiple{class_attr} th:if="${{selectOptions != null and !selectOptions.isEmpty()}}">
    <option th:each="opt : ${{selectOptions}}" th:value="${{opt.value}}" th:text="${{opt.label}}"></option>
</select>
<select multiple disabled th:unless="${{selectOptions != null and !selectOptions.isEmpty()}}">
    <option>无数据</option>
</select>'''
    
    def convert_bulletedlist(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        css_class = attrs.get('class', '')
        class_attr = f' class="{css_class}"' if css_class else ''
        
        return f'''<!-- BulletedList: 使用 listItems 变量 -->
<ul{class_attr} th:if="${{listItems != null and !listItems.isEmpty()}}">
    <li th:each="item : ${{listItems}}" th:text="${{item.label}}"></li>
</ul>
<div th:unless="${{listItems != null and !listItems.isEmpty()}}">
    <!-- 请在 Controller 中添加: model.addAttribute("listItems", itemList); -->
</div>'''
    
    def convert_repeater(self, match):
        content = match.group(1) if match.groups() else ''
        item_template = re.search(r'<ItemTemplate>(.*?)</ItemTemplate>', content, re.DOTALL)
        item_content = item_template.group(1) if item_template else '<div th:text="${item}"></div>'
        item_content = self.convert_binding_expression(item_content)
        
        return f'''<!-- Repeater: 使用 dataList 变量 -->
<div th:if="${{dataList != null and !dataList.isEmpty()}}" th:each="item : ${{dataList}}">
    {item_content}
</div>
<div th:unless="${{dataList != null and !dataList.isEmpty()}}">
    <p>暂无数据</p>
</div>'''
    
    def convert_datalist(self, match):
        return '''<!-- DataList: 使用 dataList 变量 -->
<div th:if="${dataList != null and !dataList.isEmpty()}" th:each="item : ${dataList}">
    <div th:text="${item}"></div>
</div>
<div th:unless="${dataList != null and !dataList.isEmpty()}">
    <p>暂无数据</p>
</div>'''
    
    def convert_gridview(self, match):
        return '''<!-- GridView: 使用 dataTable 和 gridColumns 变量 -->
<table class="table" th:if="${dataTable != null and !dataTable.isEmpty()}">
    <thead>
        <tr>
            <th th:each="col : ${gridColumns}" th:text="${col}"></th>
        </tr>
    </thead>
    <tbody>
        <tr th:each="row : ${dataTable}">
            <td th:each="cell : ${row}" th:text="${cell}"></td>
        </tr>
    </tbody>
</table>
<div th:unless="${dataTable != null and !dataTable.isEmpty()}">
    <p>暂无数据</p>
</div>'''
    
    def convert_detailsview(self, match):
        return '''<!-- DetailsView: 使用 detailData 变量 -->
<div th:if="${detailData != null}" class="details-view">
    <div th:each="field : ${detailData.keySet()}">
        <span class="label" th:text="${field}"></span>:
        <span class="value" th:text="${detailData[field]}"></span>
    </div>
</div>
<div th:unless="${detailData != null}">
    <p>暂无详情数据</p>
</div>'''
    
    def convert_formview(self, match):
        content = match.group(1) if match.groups() else ''
        content = self.convert_binding_expression(content)
        return f'''<!-- FormView: 使用 formData 变量 -->
<form th:action="@{{/save}}" method="post" th:object="${{formData}}" th:if="${{formData != null}}">
    {content}
</form>
<div th:unless="${{formData != null}}">
    <p>表单数据未加载</p>
</div>'''
    
    def convert_requiredvalidator(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        field_name = attrs.get('controltovalidate', 'field')
        error_msg = attrs.get('errormessage', '此字段为必填项')
        return f'<span class="error" th:if="${{#fields.hasErrors(\'{field_name}\')}}" th:errors="*{{{field_name}}}">{error_msg}</span>'
    
    def convert_regexvalidator(self, match):
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">格式错误</span>'
    
    def convert_comparevalidator(self, match):
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">比较失败</span>'
    
    def convert_rangevalidator(self, match):
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">超出范围</span>'
    
    def convert_customvalidator(self, match):
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">验证失败</span>'
    
    def convert_validationsummary(self, match):
        return '<div class="validation-summary" th:if="${#fields.hasErrors()}"><ul><li th:each="err : ${#fields.allErrors()}" th:text="${err}"></li></ul></div>'
    
    def convert_menu(self, match):
        return '''<!-- Menu: 使用 menuItems 变量 -->
<ul class="menu" th:if="${menuItems != null and !menuItems.isEmpty()}">
    <li th:each="item : ${menuItems}">
        <a th:href="${item.url}" th:text="${item.label}"></a>
    </li>
</ul>
<div th:unless="${menuItems != null and !menuItems.isEmpty()}">
    <!-- 请在 Controller 中添加: model.addAttribute("menuItems", menuList); -->
</div>'''
    
    def convert_treeview(self, match):
        return '''<!-- TreeView: 使用 treeNodes 变量 -->
<ul class="treeview" th:if="${treeNodes != null and !treeNodes.isEmpty()}">
    <li th:each="node : ${treeNodes}">
        <span th:text="${node.label}"></span>
        <ul th:if="${node.children != null and !node.children.isEmpty()}">
            <li th:each="child : ${node.children}" th:text="${child.label}"></li>
        </ul>
    </li>
</ul>
<div th:unless="${treeNodes != null and !treeNodes.isEmpty()}">
    <!-- 请在 Controller 中添加: model.addAttribute("treeNodes", treeData); -->
</div>'''
    
    def convert_sitemappath(self, match):
        return '''<!-- SiteMapPath: 使用 breadcrumbs 变量 -->
<div class="breadcrumb" th:if="${breadcrumbs != null and !breadcrumbs.isEmpty()}">
    <span th:each="node,iterStat : ${breadcrumbs}">
        <a th:if="${!iterStat.last}" th:href="${node.url}" th:text="${node.label}"></a>
        <span th:unless="${!iterStat.last}" th:text="${node.label}"></span>
        <span th:if="${!iterStat.last}"> &gt; </span>
    </span>
</div>
<div th:unless="${breadcrumbs != null and !breadcrumbs.isEmpty()}">
    <!-- 请在 Controller 中添加: model.addAttribute("breadcrumbs", breadcrumbList); -->
</div>'''
    
    def convert_login(self, match):
        return '''<!-- Login 表单 -->
<form th:action="@{/login}" method="post">
    <div class="form-group">
        <input type="text" name="username" placeholder="用户名" th:value="${username != null ? username : ''}" />
    </div>
    <div class="form-group">
        <input type="password" name="password" placeholder="密码" />
    </div>
    <div th:if="${error != null}" class="error" th:text="${error}"></div>
    <button type="submit">登录</button>
</form>'''
    
    def convert_loginview(self, match):
        return '''<div sec:authorize="isAuthenticated()">
    <!-- 已登录用户看到的内容 -->
</div>
<div sec:authorize="isAnonymous()">
    <!-- 未登录用户看到的内容 -->
</div>'''
    
    def convert_loginstatus(self, match):
        return '''<div>
    <a sec:authorize="isAnonymous()" th:href="@{/login}">登录</a>
    <span sec:authorize="isAuthenticated()">
        <span sec:authentication="name"></span>
        <a th:href="@{/logout}">注销</a>
    </span>
</div>'''
    
    def convert_loginname(self, match):
        return '<span sec:authentication="name"></span>'
    
    def convert_createuserwizard(self, match):
        return '''<!-- 注册表单 -->
<form th:action="@{/register}" method="post">
    <div><input type="text" name="username" placeholder="用户名" th:value="${user != null ? user.username : ''}" /></div>
    <div><input type="password" name="password" placeholder="密码" /></div>
    <div><input type="password" name="confirmPassword" placeholder="确认密码" /></div>
    <div th:if="${error != null}" class="error" th:text="${error}"></div>
    <button type="submit">注册</button>
</form>'''
    
    def convert_changepassword(self, match):
        return '''<!-- 修改密码表单 -->
<form th:action="@{/change-password}" method="post">
    <div><input type="password" name="oldPassword" placeholder="当前密码" /></div>
    <div><input type="password" name="newPassword" placeholder="新密码" /></div>
    <div><input type="password" name="confirmPassword" placeholder="确认新密码" /></div>
    <div th:if="${error != null}" class="error" th:text="${error}"></div>
    <button type="submit">修改密码</button>
</form>'''
    
    def convert_passwordrecovery(self, match):
        return '''<!-- 找回密码表单 -->
<form th:action="@{/forgot-password}" method="post">
    <div><input type="text" name="username" placeholder="用户名/邮箱" /></div>
    <div th:if="${message != null}" class="success" th:text="${message}"></div>
    <div th:if="${error != null}" class="error" th:text="${error}"></div>
    <button type="submit">找回密码</button>
</form>'''
    
    def convert_scriptmanager(self, match):
        return ''
    
    def convert_updatepanel(self, match):
        content = match.group(1) if match.groups() else ''
        return f'<div class="update-panel">{content}</div>'
    
    def convert_updateprogress(self, match):
        content = match.group(1) if match.groups() else ''
        return f'<div class="update-progress" style="display: none;">{content}</div>'
    
    def convert_timer(self, match):
        return '<!-- Timer 控件需要 JavaScript 实现 -->'
    
    def convert_sqldatasource(self, match):
        return '<!-- SqlDataSource 需在 Spring Data JPA 或 MyBatis 中实现 -->'
    
    def convert_objectdatasource(self, match):
        return '<!-- ObjectDataSource 需在 Spring Service 层实现 -->'
    
    def convert_calendar(self, match):
        return '<input type="date" class="calendar" />'
    
    def convert_adrotator(self, match):
        return '''<!-- AdRotator: 使用 adList 变量 -->
<div class="ad-rotator" th:if="${adList != null and !adList.isEmpty()}">
    <img th:each="ad : ${adList}" th:src="${ad.imageUrl}" th:alt="${ad.altText}" />
</div>
<div th:unless="${adList != null and !adList.isEmpty()}">
    <!-- 请在 Controller 中添加: model.addAttribute("adList", advertisementList); -->
</div>'''
    
    def convert_fileupload(self, match):
        return '<input type="file" name="file" />'
    
    def convert_hiddenfield(self, match):
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        value = self.convert_binding_expression(attrs.get('value', ''))
        return f'<input type="hidden" th:value="{value}" />'
    
    def convert_multiview(self, match):
        return '<div th:switch="${activeViewId}">\n    <!-- MultiView 内容，请使用 th:case 为每个 View 定义 -->\n</div>'
    
    def convert_view(self, match):
        content = match.group(1) if match.groups() else ''
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        view_id = attrs.get('id', 'viewId')
        return f'<div th:case="\'{view_id}\'">{content}</div>'
    
    def convert_wizard(self, match):
        return '''<!-- Wizard: 使用 wizardSteps 和 currentStep 变量 -->
<div class="wizard" th:if="${wizardSteps != null and !wizardSteps.isEmpty()}">
    <div class="wizard-steps">
        <span th:each="step,iterStat : ${wizardSteps}" 
              th:classappend="${iterStat.index == currentStep} ? 'active' : ''"
              th:text="${step.title}"></span>
    </div>
    <div class="wizard-content">
        <div th:each="step,iterStat : ${wizardSteps}" 
             th:if="${iterStat.index == currentStep}"
             th:utext="${step.content}"></div>
    </div>
</div>
<div th:unless="${wizardSteps != null and !wizardSteps.isEmpty()}">
    <!-- 请在 Controller 中添加: model.addAttribute("wizardSteps", stepList); model.addAttribute("currentStep", 0); -->
</div>'''
    
    def convert_wizardstep(self, match):
        content = match.group(1) if match.groups() else ''
        return f'<div class="wizard-step">{content}</div>'
    
    def process_file(self, file_path, output_path):
        """处理单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            print(f"处理: {file_path.name}")
            
            # ASP 控件转换映射
            asp_converters = {
                'asp:Label': self.convert_label,
                'asp:TextBox': self.convert_textbox,
                'asp:Button': self.convert_button,
                'asp:LinkButton': self.convert_linkbutton,
                'asp:ImageButton': self.convert_imagebutton,
                'asp:HyperLink': self.convert_hyperlink,
                'asp:Image': self.convert_image,
                'asp:Panel': self.convert_panel,
                'asp:PlaceHolder': self.convert_placeholder,
                'asp:Literal': self.convert_literal,
                'asp:CheckBox': self.convert_checkbox,
                'asp:CheckBoxList': self.convert_checkboxlist,
                'asp:RadioButton': self.convert_radiobutton,
                'asp:RadioButtonList': self.convert_radiobuttonlist,
                'asp:DropDownList': self.convert_dropdownlist,
                'asp:ListBox': self.convert_listbox,
                'asp:BulletedList': self.convert_bulletedlist,
                'asp:Repeater': self.convert_repeater,
                'asp:DataList': self.convert_datalist,
                'asp:GridView': self.convert_gridview,
                'asp:DetailsView': self.convert_detailsview,
                'asp:FormView': self.convert_formview,
                'asp:RequiredFieldValidator': self.convert_requiredvalidator,
                'asp:RegularExpressionValidator': self.convert_regexvalidator,
                'asp:CompareValidator': self.convert_comparevalidator,
                'asp:RangeValidator': self.convert_rangevalidator,
                'asp:CustomValidator': self.convert_customvalidator,
                'asp:ValidationSummary': self.convert_validationsummary,
                'asp:Menu': self.convert_menu,
                'asp:TreeView': self.convert_treeview,
                'asp:SiteMapPath': self.convert_sitemappath,
                'asp:Login': self.convert_login,
                'asp:LoginView': self.convert_loginview,
                'asp:LoginStatus': self.convert_loginstatus,
                'asp:LoginName': self.convert_loginname,
                'asp:CreateUserWizard': self.convert_createuserwizard,
                'asp:ChangePassword': self.convert_changepassword,
                'asp:PasswordRecovery': self.convert_passwordrecovery,
                'asp:ScriptManager': self.convert_scriptmanager,
                'asp:UpdatePanel': self.convert_updatepanel,
                'asp:UpdateProgress': self.convert_updateprogress,
                'asp:Timer': self.convert_timer,
                'asp:SqlDataSource': self.convert_sqldatasource,
                'asp:ObjectDataSource': self.convert_objectdatasource,
                'asp:Calendar': self.convert_calendar,
                'asp:AdRotator': self.convert_adrotator,
                'asp:FileUpload': self.convert_fileupload,
                'asp:HiddenField': self.convert_hiddenfield,
                'asp:MultiView': self.convert_multiview,
                'asp:View': self.convert_view,
                'asp:Wizard': self.convert_wizard,
                'asp:WizardStep': self.convert_wizardstep,
            }
            
            # 执行转换
            for tag_name, converter_func in asp_converters.items():
                # 带内容的标签
                pattern = re.compile(f'<{tag_name}[^>]*>(.*?)</{tag_name}>', re.IGNORECASE | re.DOTALL)
                content = pattern.sub(converter_func, content)
                # 自闭合标签
                pattern_self = re.compile(f'<{tag_name}[^>]*/?>', re.IGNORECASE)
                content = pattern_self.sub(converter_func, content)
            
            # 清理残留
            content = re.sub(r'<asp:\w+[^>]*>', '', content)
            content = re.sub(r'</asp:\w+>', '', content)
            content = re.sub(r'\s+runat="server"', '', content, flags=re.IGNORECASE)
            
            # HTML5 属性转换
            content = self.html5_converter.convert_all(content)
            
            # 添加文档类型和命名空间
            if '<!DOCTYPE html' not in content[:200]:
                content = '<!DOCTYPE html>\n' + content
            if '<html' in content and 'xmlns:th=' not in content:
                content = re.sub(r'(<html\s*)', r'\1xmlns:th="http://www.thymeleaf.org" xmlns:sec="http://www.thymeleaf.org/extras/spring-security" ', content)
            
            # 添加变量说明
            content = f'''<!-- 
================================================================
ASPX to Thymeleaf 转换完成
================================================================

【Controller 变量说明】
以下变量需要在 Spring MVC Controller 中设置：

1. dataList / dataTable    - 列表/表格数据 (Repeater, DataList, GridView)
2. selectOptions           - 下拉框选项 (DropDownList, ListBox)
3. checkboxOptions         - 复选框选项 (CheckBoxList)
4. radioOptions            - 单选框选项 (RadioButtonList)
5. listItems               - 列表项 (BulletedList)
6. menuItems               - 菜单项 (Menu)
7. treeNodes               - 树形节点 (TreeView)
8. breadcrumbs             - 面包屑 (SiteMapPath)
9. adList                  - 广告列表 (AdRotator)
10. formData               - 表单数据 (FormView)
11. detailData             - 详情数据 (DetailsView)
12. gridColumns            - 表格列定义 (GridView)
13. wizardSteps            - 向导步骤 (Wizard)
14. currentStep            - 当前步骤 (Wizard)
15. activeViewId           - 当前视图ID (MultiView)

================================================================
-->
''' + content
            
            # 保存文件
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 生成报告
            report_path = output_path.with_suffix('.conversion_report.txt')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(self.html5_converter.get_conversion_report())
                f.write("\n\n" + self.get_controller_example())
            
            self.conversion_count += 1
            print(f"  ✓ 已保存: {output_path}")
            return True
            
        except Exception as e:
            self.error_count += 1
            print(f"  ✗ 错误: {str(e)}")
            return False
    
    def process_directory(self, input_dir, output_dir):
        """处理整个目录"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        if not input_path.exists():
            print(f"错误: 目录不存在 - {input_dir}")
            return
        
        print(f"\n{'='*60}")
        print(f"ASPX to Thymeleaf 转换器")
        print(f"{'='*60}")
        print(f"输入目录: {input_path}")
        print(f"输出目录: {output_path}")
        print(f"{'-'*60}")
        
        aspx_files = list(input_path.rglob("*.aspx"))
        
        if not aspx_files:
            print("未找到任何 .aspx 文件")
            return
        
        print(f"找到 {len(aspx_files)} 个文件\n")
        
        for aspx_file in aspx_files:
            rel_path = aspx_file.relative_to(input_path)
            output_file = output_path / rel_path.with_suffix('.html')
            self.process_file(aspx_file, output_file)
        
        print(f"{'-'*60}")
        print(f"\n转换完成!")
        print(f"成功: {self.conversion_count} 个文件")
        print(f"失败: {self.error_count} 个文件")
        print(f"输出目录: {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='ASPX to Thymeleaf 转换器')
    parser.add_argument('input', help='输入目录路径')
    parser.add_argument('-o', '--output', help='输出目录路径', default='./thymeleaf_output')
    args = parser.parse_args()
    
    converter = CompleteConverter()
    converter.process_directory(args.input, args.output)


if __name__ == "__main__":
    main()
