#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASPX to Thymeleaf 转换器
功能：
1. 转换所有 <asp: 开头的控件
2. 将 HTML5 不支持的属性转换为 style
"""

import os
import re
from pathlib import Path
from collections import defaultdict

class ASPXToThymeleafConverter:
    """ASPX 到 Thymeleaf 转换器"""
    
    def __init__(self):
        self.conversion_count = 0
        self.error_count = 0
        self.asp_tags_found = []
        
        # ASP 控件转换映射表
        self.asp_converters = {
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


class HTML5AttributeConverter:
    """HTML5 属性转换器 - 将废弃属性转为 style"""
    
    # 废弃属性到 CSS 的映射表
    DEPRECATED_ATTRIBUTES = {
        # 布局属性
        'align': {
            'left': 'text-align: left;',
            'right': 'text-align: right;',
            'center': 'text-align: center;',
            'justify': 'text-align: justify;',
            'top': 'vertical-align: top;',
            'middle': 'vertical-align: middle;',
            'bottom': 'vertical-align: bottom;',
            'baseline': 'vertical-align: baseline;',
        },
        'valign': {
            'top': 'vertical-align: top;',
            'middle': 'vertical-align: middle;',
            'bottom': 'vertical-align: bottom;',
            'baseline': 'vertical-align: baseline;',
        },
        'bgcolor': 'background-color: {value};',
        'background': 'background-image: url({value});',
        
        # 尺寸属性
        'width': 'width: {value}px;',
        'height': 'height: {value}px;',
        'cellspacing': 'border-spacing: {value}px;',
        'cellpadding': 'padding: {value}px;',
        'border': 'border: {value}px solid;',
        'hspace': 'margin-left: {value}px; margin-right: {value}px;',
        'vspace': 'margin-top: {value}px; margin-bottom: {value}px;',
        
        # 文本属性
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
        
        # 列表属性
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
        
        # 边框属性
        'bordercolor': 'border-color: {value};',
        'bordercolorlight': 'border-top-color: {value}; border-left-color: {value};',
        'bordercolordark': 'border-bottom-color: {value}; border-right-color: {value};',
        
        # 其他属性
        'clear': {
            'left': 'clear: left;',
            'right': 'clear: right;',
            'all': 'clear: both;',
            'both': 'clear: both;',
            'none': 'clear: none;',
        },
        'nowrap': 'white-space: nowrap;',
        'noshade': 'border: none; background-color: #cccccc; height: 2px;',
        'scrolling': 'overflow: {value};',
        'frameborder': 'border: {value}px solid;',
        'marginwidth': 'margin-left: {value}px; margin-right: {value}px;',
        'marginheight': 'margin-top: {value}px; margin-bottom: {value}px;',
    }
    
    def __init__(self):
        self.conversion_log = []
    
    def convert_attributes_to_style(self, tag_name, attributes):
        """将废弃属性转换为 style 属性"""
        styles = []
        new_attributes = {}
        
        for attr_name, attr_value in attributes.items():
            attr_lower = attr_name.lower()
            
            # 如果是 style 属性，保留并合并
            if attr_lower == 'style':
                if attr_value and not attr_value.isspace():
                    styles.append(attr_value.rstrip(';'))
                continue
            
            # 检查是否为废弃属性
            if attr_lower in self.DEPRECATED_ATTRIBUTES:
                rule = self.DEPRECATED_ATTRIBUTES[attr_lower]
                
                if isinstance(rule, dict):
                    # 映射表类型
                    if str(attr_value) in rule:
                        styles.append(rule[str(attr_value)])
                        self._log_conversion(tag_name, attr_name, attr_value, rule[str(attr_value)])
                    else:
                        new_attributes[attr_name] = attr_value
                elif isinstance(rule, str):
                    # 模板类型
                    css = rule.format(value=attr_value)
                    styles.append(css)
                    self._log_conversion(tag_name, attr_name, attr_value, css)
                else:
                    new_attributes[attr_name] = attr_value
            else:
                # 保留 HTML5 支持的属性
                if attr_lower not in ['runat', 'id'] or attr_lower == 'id':
                    new_attributes[attr_name] = attr_value
        
        # 合并 style
        if styles:
            new_attributes['style'] = '; '.join(styles)
        
        return new_attributes
    
    def convert_inline_tags(self, content):
        """转换内联样式标签"""
        
        # 转换 <font> 标签
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
        
        # 转换 <center> 标签
        content = re.sub(r'<center>(.*?)</center>', r'<div style="text-align: center;">\1</div>', 
                        content, flags=re.DOTALL | re.IGNORECASE)
        
        # 转换 <strike> 和 <s> 标签
        content = re.sub(r'<strike>(.*?)</strike>', r'<span style="text-decoration: line-through;">\1</span>', 
                        content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<s>(.*?)</s>', r'<span style="text-decoration: line-through;">\1</span>', 
                        content, flags=re.DOTALL | re.IGNORECASE)
        
        # 转换 <u> 标签
        content = re.sub(r'<u>(.*?)</u>', r'<span style="text-decoration: underline;">\1</span>', 
                        content, flags=re.DOTALL | re.IGNORECASE)
        
        # 转换 <big> 标签
        content = re.sub(r'<big>(.*?)</big>', r'<span style="font-size: larger;">\1</span>', 
                        content, flags=re.DOTALL | re.IGNORECASE)
        
        # 转换 <small> 标签
        content = re.sub(r'<small>(.*?)</small>', r'<span style="font-size: smaller;">\1</span>', 
                        content, flags=re.DOTALL | re.IGNORECASE)
        
        # 转换 <tt> 标签
        content = re.sub(r'<tt>(.*?)</tt>', r'<span style="font-family: monospace;">\1</span>', 
                        content, flags=re.DOTALL | re.IGNORECASE)
        
        return content
    
    def convert_table_attributes(self, content):
        """转换表格属性"""
        
        # 转换 <table> 标签
        def convert_table(match):
            tag_content = match.group(0)
            attrs = self._parse_tag_attributes(tag_content)
            
            inner = re.search(r'<table[^>]*>(.*)<tr>', tag_content, re.DOTALL | re.IGNORECASE)
            inner_content = inner.group(1) if inner else ''
            
            new_attrs = self.convert_attributes_to_style('table', attrs)
            attr_str = self._build_attributes(new_attrs)
            return f'<table{attr_str}>{inner_content}</table>'
        
        content = re.sub(r'<table[^>]*>.*?</table>', convert_table, content, flags=re.DOTALL | re.IGNORECASE)
        
        # 转换 <table> 和 <th> 标签
        for cell_tag in ['td', 'th']:
            def convert_cell(match, tag=cell_tag):
                attrs = self._parse_tag_attributes(match.group(0))
                new_attrs = self.convert_attributes_to_style(tag, attrs)
                attr_str = self._build_attributes(new_attrs)
                return f'<{tag}{attr_str}>'
            
            content = re.sub(f'<{cell_tag}[^>]*>', convert_cell, content, flags=re.IGNORECASE)
        
        # 转换 <tr> 标签
        def convert_row(match):
            attrs = self._parse_tag_attributes(match.group(0))
            new_attrs = self.convert_attributes_to_style('tr', attrs)
            attr_str = self._build_attributes(new_attrs)
            return f'<tr{attr_str}>'
        
        content = re.sub(r'<tr[^>]*>', convert_row, content, flags=re.IGNORECASE)
        
        return content
    
    def convert_hr_attributes(self, content):
        """转换 <hr> 标签属性"""
        
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
                if attrs['align'] == 'left':
                    styles.append('margin-left: 0; margin-right: auto;')
                elif attrs['align'] == 'right':
                    styles.append('margin-left: auto; margin-right: 0;')
                elif attrs['align'] == 'center':
                    styles.append('margin-left: auto; margin-right: auto;')
            
            if styles:
                return f'<hr style="{"; ".join(styles)}" />'
            return '<hr />'
        
        content = re.sub(r'<hr[^>]*/?>', convert_hr, content, flags=re.IGNORECASE)
        return content
    
    def convert_img_attributes(self, content):
        """转换图片标签属性"""
        
        def convert_img(match):
            attrs = self._parse_tag_attributes(match.group(0))
            styles = []
            
            if 'border' in attrs:
                styles.append(f'border: {attrs["border"]}px solid;')
                del attrs['border']
            
            if 'hspace' in attrs:
                styles.append(f'margin-left: {attrs["hspace"]}px; margin-right: {attrs["hspace"]}px;')
                del attrs['hspace']
            
            if 'vspace' in attrs:
                styles.append(f'margin-top: {attrs["vspace"]}px; margin-bottom: {attrs["vspace"]}px;')
                del attrs['vspace']
            
            if 'align' in attrs:
                align_map = {
                    'left': 'float: left; margin-right: 10px;',
                    'right': 'float: right; margin-left: 10px;',
                    'top': 'vertical-align: top;',
                    'middle': 'vertical-align: middle;',
                    'bottom': 'vertical-align: bottom;',
                }
                if attrs['align'] in align_map:
                    styles.append(align_map[attrs['align']])
                del attrs['align']
            
            if styles:
                if 'style' in attrs:
                    attrs['style'] = attrs['style'] + '; ' + '; '.join(styles)
                else:
                    attrs['style'] = '; '.join(styles)
            
            attr_str = self._build_attributes(attrs)
            return f'<img{attr_str} />'
        
        content = re.sub(r'<img[^>]*/?>', convert_img, content, flags=re.IGNORECASE)
        return content
    
    def convert_body_attributes(self, content):
        """转换 body 标签属性"""
        
        def convert_body(match):
            attrs = self._parse_tag_attributes(match.group(0))
            styles = []
            
            body_attrs = {
                'text': 'color',
                'bgcolor': 'background-color',
                'background': 'background-image',
                'link': 'color',
                'vlink': 'color',
                'alink': 'color',
                'leftmargin': 'margin-left',
                'topmargin': 'margin-top',
            }
            
            for attr, css_prop in body_attrs.items():
                if attr in attrs:
                    if css_prop == 'background-image':
                        styles.append(f'{css_prop}: url("{attrs[attr]}");')
                    else:
                        styles.append(f'{css_prop}: {attrs[attr]};')
                    del attrs[attr]
            
            if styles:
                attrs['style'] = '; '.join(styles)
            
            attr_str = self._build_attributes(attrs)
            return f'<body{attr_str}>'
        
        content = re.sub(r'<body[^>]*>', convert_body, content, flags=re.IGNORECASE)
        return content
    
    def convert_iframe_attributes(self, content):
        """转换 iframe 标签属性"""
        
        def convert_iframe(match):
            attrs = self._parse_tag_attributes(match.group(0))
            styles = []
            
            if 'frameborder' in attrs:
                if attrs['frameborder'] == '0':
                    styles.append('border: none;')
                else:
                    styles.append('border: 1px solid;')
                del attrs['frameborder']
            
            if 'scrolling' in attrs:
                overflow_map = {'yes': 'auto', 'no': 'hidden', 'auto': 'auto'}
                overflow = overflow_map.get(attrs['scrolling'], 'auto')
                styles.append(f'overflow: {overflow};')
                del attrs['scrolling']
            
            if 'marginwidth' in attrs:
                styles.append(f'margin-left: {attrs["marginwidth"]}px; margin-right: {attrs["marginwidth"]}px;')
                del attrs['marginwidth']
            
            if 'marginheight' in attrs:
                styles.append(f'margin-top: {attrs["marginheight"]}px; margin-bottom: {attrs["marginheight"]}px;')
                del attrs['marginheight']
            
            if styles:
                if 'style' in attrs:
                    attrs['style'] = attrs['style'] + '; ' + '; '.join(styles)
                else:
                    attrs['style'] = '; '.join(styles)
            
            attr_str = self._build_attributes(attrs)
            return f'<iframe{attr_str}></iframe>'
        
        content = re.sub(r'<iframe[^>]*>', convert_iframe, content, flags=re.IGNORECASE)
        return content
    
    def convert_list_attributes(self, content):
        """转换列表标签属性"""
        
        for list_tag in ['ul', 'ol']:
            def convert_list(match, tag=list_tag):
                attrs = self._parse_tag_attributes(match.group(0))
                if 'type' in attrs:
                    type_map = {
                        'disc': 'disc', 'circle': 'circle', 'square': 'square',
                        '1': 'decimal', 'A': 'upper-alpha', 'a': 'lower-alpha',
                        'I': 'upper-roman', 'i': 'lower-roman'
                    }
                    list_type = type_map.get(attrs['type'], 'disc')
                    attrs['style'] = f'list-style-type: {list_type};'
                    del attrs['type']
                
                attr_str = self._build_attributes(attrs)
                return f'<{tag}{attr_str}>'
            
            content = re.sub(f'<{list_tag}[^>]*>', convert_list, content, flags=re.IGNORECASE)
        
        return content
    
    def convert_generic_attributes(self, content):
        """通用属性转换"""
        
        def convert_generic_tag(match):
            tag_name = match.group(1)
            attrs_str = match.group(2)
            closing = match.group(3) or ''
            
            # 跳过自闭合标签和特殊标签
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
        content = self.convert_body_attributes(content)
        content = self.convert_hr_attributes(content)
        content = self.convert_img_attributes(content)
        content = self.convert_iframe_attributes(content)
        content = self.convert_list_attributes(content)
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
        
        report = ["\n=== HTML5 属性转换报告 ===\n"]
        report.append(f"共转换 {len(self.conversion_log)} 个废弃属性\n")
        
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
        value = re.sub(r'<%#\s*Eval\("([^"]+)"\)\s*%>', r'${item.\1}', value)
        value = re.sub(r'<%#\s*Bind\("([^"]+)"\)\s*%>', r'${item.\1}', value)
        value = re.sub(r'<%=\s*([^%]+)\s*%>', r'${\1}', value)
        value = re.sub(r'<%:\s*([^%]+)\s*%>', r'${\1}', value)
        return value
    
    def convert_label(self, match):
        """转换 Label 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = attrs.get('text', '')
        css_class = attrs.get('class', '')
        
        text = self.convert_binding_expression(text)
        
        if css_class:
            return f'<span class="{css_class}" th:text="{text}"></span>'
        return f'<span th:text="{text}"></span>'
    
    def convert_textbox(self, match):
        """转换 TextBox 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text_mode = attrs.get('textmode', '').lower()
        text = attrs.get('text', '')
        
        text = self.convert_binding_expression(text)
        
        if text_mode == 'password':
            return f'<input type="password" th:value="{text}" />'
        elif text_mode == 'multiline':
            return f'<textarea th:text="{text}"></textarea>'
        else:
            return f'<input type="text" th:value="{text}" />'
    
    def convert_button(self, match):
        """转换 Button 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = attrs.get('text', 'Button')
        text = self.convert_binding_expression(text)
        return f'<button type="submit" th:text="{text}"></button>'
    
    def convert_linkbutton(self, match):
        """转换 LinkButton 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = attrs.get('text', 'Link')
        text = self.convert_binding_expression(text)
        return f'<a href="javascript:void(0)" th:text="{text}"></a>'
    
    def convert_imagebutton(self, match):
        """转换 ImageButton 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        image_url = attrs.get('imageurl', '')
        alt_text = attrs.get('alternatetext', '')
        return f'<img src="{image_url}" alt="{alt_text}" style="cursor: pointer;" />'
    
    def convert_hyperlink(self, match):
        """转换 HyperLink 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = attrs.get('text', '')
        navigate_url = attrs.get('navigateurl', '#')
        text = self.convert_binding_expression(text)
        return f'<a href="{navigate_url}" th:text="{text}"></a>'
    
    def convert_image(self, match):
        """转换 Image 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        image_url = attrs.get('imageurl', '')
        alt_text = attrs.get('alternatetext', '')
        return f'<img src="{image_url}" alt="{alt_text}" />'
    
    def convert_panel(self, match):
        """转换 Panel 控件"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return f'<div>{content}</div>'
    
    def convert_placeholder(self, match):
        """转换 PlaceHolder 控件"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return content
    
    def convert_literal(self, match):
        """转换 Literal 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = attrs.get('text', '')
        text = self.convert_binding_expression(text)
        return text
    
    def convert_checkbox(self, match):
        """转换 CheckBox 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = attrs.get('text', '')
        text = self.convert_binding_expression(text)
        
        if text:
            return f'<label><input type="checkbox" /> <span th:text="{text}"></span></label>'
        return '<input type="checkbox" />'
    
    def convert_checkboxlist(self, match):
        """转换 CheckBoxList 控件"""
        return '<div th:each="item : ${items}"><label><input type="checkbox" th:value="${item.value}" /> <span th:text="${item.text}"></span></label></div>'
    
    def convert_radiobutton(self, match):
        """转换 RadioButton 控件"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        text = attrs.get('text', '')
        group_name = attrs.get('groupname', 'radioGroup')
        text = self.convert_binding_expression(text)
        
        if text:
            return f'<label><input type="radio" name="{group_name}" /> <span th:text="{text}"></span></label>'
        return f'<input type="radio" name="{group_name}" />'
    
    def convert_radiobuttonlist(self, match):
        """转换 RadioButtonList 控件"""
        return '<div th:each="item : ${items}"><label><input type="radio" name="radioGroup" th:value="${item.value}" /> <span th:text="${item.text}"></span></label></div>'
    
    def convert_dropdownlist(self, match):
        """转换 DropDownList 控件"""
        return '<select><option th:each="item : ${items}" th:value="${item.value}" th:text="${item.text}"></option></select>'
    
    def convert_listbox(self, match):
        """转换 ListBox 控件"""
        return '<select multiple><option th:each="item : ${items}" th:value="${item.value}" th:text="${item.text}"></option></select>'
    
    def convert_bulletedlist(self, match):
        """转换 BulletedList 控件"""
        return '<ul><li th:each="item : ${items}" th:text="${item.text}"></li></ul>'
    
    def convert_repeater(self, match):
        """转换 Repeater 控件"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        
        item_template = re.search(r'<ItemTemplate>(.*?)</ItemTemplate>', content, re.DOTALL)
        item_content = item_template.group(1) if item_template else '<div th:text="${item}"></div>'
        item_content = self.convert_binding_expression(item_content)
        
        return f'<div th:each="item : ${items}">{item_content}</div>'
    
    def convert_datalist(self, match):
        """转换 DataList 控件"""
        return '<div th:each="item : ${items}"><div th:text="${item}"></div></div>'
    
    def convert_gridview(self, match):
        """转换 GridView 控件"""
        return '''<table class="table">
    <thead>
        <tr><th th:each="col : ${columns}" th:text="${col}"></th></tr>
    </thead>
    <tbody>
        <tr th:each="item : ${items}">
            <td th:each="prop : ${item}" th:text="${prop}"></td>
        </tr>
    </tbody>
</table>'''
    
    def convert_detailsview(self, match):
        """转换 DetailsView 控件"""
        return '<div th:each="field : ${fields}"><span th:text="${field.label}"></span>: <span th:text="${item[field.name]}"></span></div>'
    
    def convert_formview(self, match):
        """转换 FormView 控件"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        content = self.convert_binding_expression(content)
        return f'<div th:object="${item}">{content}</div>'
    
    def convert_requiredvalidator(self, match):
        """转换 RequiredFieldValidator"""
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">必填</span>'
    
    def convert_regexvalidator(self, match):
        """转换 RegularExpressionValidator"""
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">格式错误</span>'
    
    def convert_comparevalidator(self, match):
        """转换 CompareValidator"""
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">比较失败</span>'
    
    def convert_rangevalidator(self, match):
        """转换 RangeValidator"""
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">超出范围</span>'
    
    def convert_customvalidator(self, match):
        """转换 CustomValidator"""
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">验证失败</span>'
    
    def convert_validationsummary(self, match):
        """转换 ValidationSummary"""
        return '<div class="validation-summary" th:if="${#fields.hasErrors()}"><ul><li th:each="err : ${#fields.allErrors()}" th:text="${err}"></li></ul></div>'
    
    def convert_menu(self, match):
        """转换 Menu"""
        return '<ul class="menu"><li th:each="item : ${menuItems}"><a th:href="${item.url}" th:text="${item.text}"></a></li></ul>'
    
    def convert_treeview(self, match):
        """转换 TreeView"""
        return '<ul class="treeview"><li th:each="node : ${treeNodes}"><span th:text="${node.text}"></span></li></ul>'
    
    def convert_sitemappath(self, match):
        """转换 SiteMapPath"""
        return '<div class="breadcrumb"><span th:each="node : ${breadcrumbs}"><a th:href="${node.url}" th:text="${node.title}"></a> &gt; </span></div>'
    
    def convert_login(self, match):
        """转换 Login"""
        return '''<form th:action="@{/login}" method="post">
    <input type="text" name="username" placeholder="用户名" />
    <input type="password" name="password" placeholder="密码" />
    <button type="submit">登录</button>
</form>'''
    
    def convert_loginview(self, match):
        """转换 LoginView"""
        return '<div sec:authorize="isAuthenticated()">已登录</div><div sec:authorize="isAnonymous()">未登录</div>'
    
    def convert_loginstatus(self, match):
        """转换 LoginStatus"""
        return '<a sec:authorize="isAnonymous()" th:href="@{/login}">登录</a><a sec:authorize="isAuthenticated()" th:href="@{/logout}">注销</a>'
    
    def convert_loginname(self, match):
        """转换 LoginName"""
        return '<span sec:authentication="name"></span>'
    
    def convert_createuserwizard(self, match):
        """转换 CreateUserWizard"""
        return '''<form th:action="@{/register}" method="post">
    <input type="text" name="username" placeholder="用户名" />
    <input type="password" name="password" placeholder="密码" />
    <button type="submit">注册</button>
</form>'''
    
    def convert_changepassword(self, match):
        """转换 ChangePassword"""
        return '''<form th:action="@{/change-password}" method="post">
    <input type="password" name="oldPassword" placeholder="当前密码" />
    <input type="password" name="newPassword" placeholder="新密码" />
    <button type="submit">修改密码</button>
</form>'''
    
    def convert_passwordrecovery(self, match):
        """转换 PasswordRecovery"""
        return '''<form th:action="@{/forgot-password}" method="post">
    <input type="text" name="username" placeholder="用户名" />
    <button type="submit">找回密码</button>
</form>'''
    
    def convert_scriptmanager(self, match):
        """转换 ScriptManager"""
        return ''
    
    def convert_updatepanel(self, match):
        """转换 UpdatePanel"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return f'<div class="update-panel">{content}</div>'
    
    def convert_updateprogress(self, match):
        """转换 UpdateProgress"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return f'<div class="update-progress" style="display: none;">{content}</div>'
    
    def convert_timer(self, match):
        """转换 Timer"""
        return ''
    
    def convert_sqldatasource(self, match):
        """转换 SqlDataSource"""
        return '<!-- SqlDataSource 需在后台实现 -->'
    
    def convert_objectdatasource(self, match):
        """转换 ObjectDataSource"""
        return '<!-- ObjectDataSource 需在后台实现 -->'
    
    def convert_calendar(self, match):
        """转换 Calendar"""
        return '<input type="date" />'
    
    def convert_adrotator(self, match):
        """转换 AdRotator"""
        return '<div class="ad-rotator"></div>'
    
    def convert_fileupload(self, match):
        """转换 FileUpload"""
        return '<input type="file" name="file" />'
    
    def convert_hiddenfield(self, match):
        """转换 HiddenField"""
        tag = match.group(0)
        attrs = self.extract_attributes(tag)
        value = attrs.get('value', '')
        value = self.convert_binding_expression(value)
        return f'<input type="hidden" th:value="{value}" />'
    
    def convert_multiview(self, match):
        """转换 MultiView"""
        return '<div th:switch="${activeView}"></div>'
    
    def convert_view(self, match):
        """转换 View"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return f'<div th:case="viewId">{content}</div>'
    
    def convert_wizard(self, match):
        """转换 Wizard"""
        return '<div class="wizard"><div th:each="step : ${steps}" th:text="${step}"></div></div>'
    
    def convert_wizardstep(self, match):
        """转换 WizardStep"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return f'<div class="wizard-step">{content}</div>'
    
    def process_file(self, file_path, output_path):
        """处理单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            print(f"处理: {file_path.name}")
            
            # 1. 转换 ASPX 控件
            for tag_name, converter in self.asp_converters.items():
                pattern = re.compile(f'<{tag_name}[^>]*>(.*?)</{tag_name}>', re.IGNORECASE | re.DOTALL)
                content = pattern.sub(converter, content)
                
                # 自闭合标签
                pattern_self = re.compile(f'<{tag_name}[^>]*/?>', re.IGNORECASE)
                content = pattern_self.sub(converter, content)
            
            # 2. 清理残留的 ASPX 标签
            content = re.sub(r'<asp:\w+[^>]*>', '', content)
            content = re.sub(r'</asp:\w+>', '', content)
            content = re.sub(r'\s+runat="server"', '', content, flags=re.IGNORECASE)
            
            # 3. 转换 HTML5 废弃属性
            content = self.html5_converter.convert_all(content)
            
            # 4. 添加 HTML5 文档类型
            if '<!DOCTYPE html' not in content[:200]:
                content = '<!DOCTYPE html>\n' + content
            
            # 5. 添加 Thymeleaf 命名空间
            if '<html' in content and 'xmlns:th=' not in content:
                content = re.sub(
                    r'(<html\s*)',
                    r'\1xmlns:th="http://www.thymeleaf.org" xmlns:sec="http://www.thymeleaf.org/extras/spring-security" ',
                    content
                )
            
            # 保存文件
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 生成转换报告
            report_path = output_path.with_suffix('.conversion_report.txt')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(self.html5_converter.get_conversion_report())
            
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
        
        # 查找所有 .aspx 文件
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
    
    parser = argparse.ArgumentParser(description='ASPX to Thymeleaf 转换器（不含 jQuery 升级）')
    parser.add_argument('input', help='输入目录路径')
    parser.add_argument('-o', '--output', help='输出目录路径', default='./thymeleaf_output')
    
    args = parser.parse_args()
    
    converter = CompleteConverter()
    converter.process_directory(args.input, args.output)


if __name__ == "__main__":
    main()
