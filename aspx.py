#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的 ASPX to Thymeleaf 转换器
处理所有 <asp: 开头的标签
"""

import os
import re
from pathlib import Path

class CompleteASPXConverter:
    def __init__(self):
        # 完整的 ASP 标签映射表
        self.asp_tag_mapping = {
            # 标准控件
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
            'asp:LiteralControl': self.convert_literal,
            
            # 选择控件
            'asp:CheckBox': self.convert_checkbox,
            'asp:CheckBoxList': self.convert_checkboxlist,
            'asp:RadioButton': self.convert_radiobutton,
            'asp:RadioButtonList': self.convert_radiobuttonlist,
            'asp:DropDownList': self.convert_dropdownlist,
            'asp:ListBox': self.convert_listbox,
            'asp:BulletedList': self.convert_bulletedlist,
            
            # 数据控件
            'asp:Repeater': self.convert_repeater,
            'asp:DataList': self.convert_datalist,
            'asp:GridView': self.convert_gridview,
            'asp:DetailsView': self.convert_detailsview,
            'asp:FormView': self.convert_formview,
            'asp:DataPager': self.convert_datapager,
            
            # 验证控件
            'asp:RequiredFieldValidator': self.convert_requiredvalidator,
            'asp:RegularExpressionValidator': self.convert_regexvalidator,
            'asp:CompareValidator': self.convert_comparevalidator,
            'asp:RangeValidator': self.convert_rangevalidator,
            'asp:CustomValidator': self.convert_customvalidator,
            'asp:ValidationSummary': self.convert_validationsummary,
            
            # 导航控件
            'asp:Menu': self.convert_menu,
            'asp:TreeView': self.convert_treeview,
            'asp:SiteMapPath': self.convert_sitemappath,
            'asp:SiteMapDataSource': self.convert_sitemapdatasource,
            
            # 登录控件
            'asp:Login': self.convert_login,
            'asp:LoginView': self.convert_loginview,
            'asp:LoginStatus': self.convert_loginstatus,
            'asp:LoginName': self.convert_loginname,
            'asp:CreateUserWizard': self.convert_createuserwizard,
            'asp:ChangePassword': self.convert_changepassword,
            'asp:PasswordRecovery': self.convert_passwordrecovery,
            
            # WebParts 控件
            'asp:WebPartManager': self.convert_webpartmanager,
            'asp:WebPartZone': self.convert_webpartzone,
            'asp:CatalogZone': self.convert_catalogzone,
            'asp:EditorZone': self.convert_editorzone,
            
            # AJAX 控件
            'asp:ScriptManager': self.convert_scriptmanager,
            'asp:UpdatePanel': self.convert_updatepanel,
            'asp:UpdateProgress': self.convert_updateprogress,
            'asp:Timer': self.convert_timer,
            'asp:AsyncPostBackTrigger': self.convert_asynctrigger,
            
            # 数据源控件
            'asp:SqlDataSource': self.convert_sqldatasource,
            'asp:ObjectDataSource': self.convert_objectdatasource,
            'asp:LinqDataSource': self.convert_linqdatasource,
            'asp:EntityDataSource': self.convert_entitydatasource,
            'asp:XmlDataSource': self.convert_xmldatasource,
            'asp:AccessDataSource': self.convert_accessdatasource,
            
            # HTML 控件
            'asp:HtmlGenericControl': self.convert_htmlgeneric,
            'asp:HtmlInputText': self.convert_htmlinputtext,
            'asp:HtmlInputButton': self.convert_htmlinputbutton,
            'asp:HtmlSelect': self.convert_htmlselect,
            'asp:HtmlTextArea': self.convert_htmltextarea,
            
            # 报表控件
            'asp:ReportViewer': self.convert_reportviewer,
            'asp:Chart': self.convert_chart,
            
            # 其他控件
            'asp:Calendar': self.convert_calendar,
            'asp:AdRotator': self.convert_adrotator,
            'asp:Substitution': self.convert_substitution,
            'asp:Localize': self.convert_localize,
            'asp:MultiView': self.convert_multiview,
            'asp:View': self.convert_view,
            'asp:Wizard': self.convert_wizard,
            'asp:WizardStep': self.convert_wizardstep,
            'asp:FileUpload': self.convert_fileupload,
            'asp:HiddenField': self.convert_hiddenfield,
            'asp:Xml': self.convert_xml,
        }
        
        self.conversion_count = 0

    def extract_attributes(self, tag_content):
        """提取标签中的所有属性"""
        attributes = {}
        
        # 匹配属性名="属性值" 或 属性名='属性值'
        attr_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
        matches = re.findall(attr_pattern, tag_content)
        
        for key, value in matches:
            # 转换特殊属性名
            if key.lower() == 'cssclass':
                key = 'class'
            elif key.lower() == 'imageurl':
                key = 'th:src'
            elif key.lower() == 'navigateurl':
                key = 'th:href'
            elif key.lower() == 'text':
                key = 'th:text'
            elif key.lower() == 'tooltip':
                key = 'title'
            elif key.lower() == 'onclientclick':
                key = 'onclick'
            
            # 转换数据绑定表达式
            if '<%#' in value or '<%=' in value or '<%:' in value:
                value = self.convert_binding_expression(value)
            
            attributes[key] = value
        
        return attributes

    def convert_binding_expression(self, value):
        """转换数据绑定表达式"""
        # <%# Eval("Name") %> -> ${item.name}
        value = re.sub(r'<%#\s*Eval\("([^"]+)"\)\s*%>', r'${item.\1}', value)
        # <%# Eval("Name", "{0:c}") %> -> ${#numbers.formatDecimal(item.name)}
        value = re.sub(r'<%#\s*Eval\("([^"]+)",\s*"([^"]+)"\)\s*%>', r'${#strings.format("\2", item.\1)}', value)
        # <%# Bind("Name") %> -> ${item.name}
        value = re.sub(r'<%#\s*Bind\("([^"]+)"\)\s*%>', r'${item.\1}', value)
        # <%= variable %> -> ${variable}
        value = re.sub(r'<%=\s*([^%]+)\s*%>', r'${\1}', value)
        # <%: variable %> -> ${variable}
        value = re.sub(r'<%:\s*([^%]+)\s*%>', r'${\1}', value)
        # <%# Container.DataItem %> -> ${item}
        value = re.sub(r'<%#\s*Container\.DataItem\s*%>', r'${item}', value)
        
        return value

    def convert_label(self, match):
        """转换 Label 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        text = attrs.pop('th:text', attrs.pop('text', ''))
        css_class = attrs.pop('class', '')
        
        if css_class:
            attrs['class'] = css_class
        
        attr_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items() if k not in ['id', 'runat']])
        
        if text:
            return f'<span {attr_str} th:text="{text}"></span>'
        else:
            return f'<span {attr_str}></span>'

    def convert_textbox(self, match):
        """转换 TextBox 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        text_mode = attrs.get('textmode', '').lower()
        text = attrs.pop('th:text', attrs.pop('text', ''))
        
        if text_mode == 'password':
            return f'<input type="password" th:value="{text}" />'
        elif text_mode == 'multiline':
            rows = attrs.get('rows', '3')
            cols = attrs.get('columns', '20')
            return f'<textarea rows="{rows}" cols="{cols}" th:text="{text}"></textarea>'
        else:  # SingleLine
            return f'<input type="text" th:value="{text}" />'

    def convert_button(self, match):
        """转换 Button 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        text = attrs.pop('th:text', attrs.pop('text', 'Button'))
        css_class = attrs.pop('class', '')
        
        onclick = attrs.pop('onclick', '')
        
        if css_class:
            attrs['class'] = css_class
        
        attr_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items() if k not in ['id', 'runat']])
        
        if onclick:
            return f'<button type="button" onclick="{onclick}" {attr_str} th:text="{text}"></button>'
        else:
            return f'<button type="submit" {attr_str} th:text="{text}"></button>'

    def convert_linkbutton(self, match):
        """转换 LinkButton 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        text = attrs.pop('th:text', attrs.pop('text', 'Link'))
        css_class = attrs.pop('class', '')
        onclick = attrs.pop('onclick', '')
        command_name = attrs.get('commandname', '')
        command_arg = attrs.get('commandargument', '')
        
        href = 'javascript:void(0)'
        
        if onclick:
            return f'<a href="{href}" onclick="{onclick}" class="{css_class}" th:text="{text}"></a>'
        elif command_name:
            return f'<a href="{href}" data-command="{command_name}" data-arg="{command_arg}" class="{css_class}" th:text="{text}"></a>'
        else:
            return f'<a href="{href}" class="{css_class}" th:text="{text}"></a>'

    def convert_imagebutton(self, match):
        """转换 ImageButton 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        image_url = attrs.get('th:src', attrs.get('imageurl', ''))
        alt_text = attrs.get('alternatetext', attrs.get('alt', ''))
        css_class = attrs.get('class', '')
        onclick = attrs.get('onclick', '')
        command_name = attrs.get('commandname', '')
        
        if onclick:
            return f'<img src="{image_url}" alt="{alt_text}" class="{css_class}" onclick="{onclick}" style="cursor: pointer;" />'
        elif command_name:
            return f'<img src="{image_url}" alt="{alt_text}" class="{css_class}" data-command="{command_name}" onclick="handleImageClick(this)" style="cursor: pointer;" />'
        else:
            return f'<img src="{image_url}" alt="{alt_text}" class="{css_class}" style="cursor: pointer;" />'

    def convert_hyperlink(self, match):
        """转换 HyperLink 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        text = attrs.pop('th:text', attrs.pop('text', ''))
        navigate_url = attrs.get('th:href', attrs.get('navigateurl', '#'))
        css_class = attrs.get('class', '')
        
        return f'<a href="{navigate_url}" class="{css_class}" th:text="{text}"></a>'

    def convert_image(self, match):
        """转换 Image 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        image_url = attrs.get('th:src', attrs.get('imageurl', ''))
        alt_text = attrs.get('alternatetext', attrs.get('alt', ''))
        css_class = attrs.get('class', '')
        
        return f'<img src="{image_url}" alt="{alt_text}" class="{css_class}" />'

    def convert_panel(self, match):
        """转换 Panel 控件"""
        tag_content = match.group(0)
        content = match.group(1) if len(match.groups()) > 0 else ''
        attrs = self.extract_attributes(tag_content)
        
        visible = attrs.get('visible', 'true').lower()
        css_class = attrs.get('class', '')
        
        if visible == 'false':
            return f'<div th:if="false" class="{css_class}">{content}</div>'
        else:
            return f'<div class="{css_class}">{content}</div>'

    def convert_placeholder(self, match):
        """转换 PlaceHolder 控件"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return content

    def convert_literal(self, match):
        """转换 Literal 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        text = attrs.get('th:text', attrs.get('text', ''))
        return f'<span th:text="{text}"></span>'

    def convert_checkbox(self, match):
        """转换 CheckBox 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        text = attrs.get('th:text', attrs.get('text', ''))
        checked = attrs.get('checked', '').lower()
        css_class = attrs.get('class', '')
        
        checked_attr = ' checked="checked"' if checked == 'true' else ''
        
        if text:
            return f'<label class="{css_class}"><input type="checkbox"{checked_attr} /> <span th:text="{text}"></span></label>'
        else:
            return f'<input type="checkbox"{checked_attr} class="{css_class}" />'

    def convert_checkboxlist(self, match):
        """转换 CheckBoxList 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        repeat_direction = attrs.get('repeatdirection', 'vertical')
        repeat_columns = int(attrs.get('repeatcolumns', '1'))
        
        if repeat_direction.lower() == 'horizontal':
            return f'''<div th:each="item : ${{items}}">
    <label style="display: inline-block; margin-right: 10px;">
        <input type="checkbox" th:value="${{item.value}}" th:text="${{item.text}}" />
    </label>
</div>'''
        else:
            return f'''<div th:each="item : ${{items}}">
    <label>
        <input type="checkbox" th:value="${{item.value}}" th:text="${{item.text}}" />
    </label>
</div>'''

    def convert_radiobutton(self, match):
        """转换 RadioButton 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        text = attrs.get('th:text', attrs.get('text', ''))
        group_name = attrs.get('groupname', 'radioGroup')
        checked = attrs.get('checked', '').lower()
        
        checked_attr = ' checked="checked"' if checked == 'true' else ''
        
        if text:
            return f'<label><input type="radio" name="{group_name}"{checked_attr} /> <span th:text="{text}"></span></label>'
        else:
            return f'<input type="radio" name="{group_name}"{checked_attr} />'

    def convert_radiobuttonlist(self, match):
        """转换 RadioButtonList 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        repeat_direction = attrs.get('repeatdirection', 'vertical')
        
        if repeat_direction.lower() == 'horizontal':
            return f'''<div th:each="item : ${{items}}">
    <label style="display: inline-block; margin-right: 10px;">
        <input type="radio" th:value="${{item.value}}" th:text="${{item.text}}" name="radioGroup" />
    </label>
</div>'''
        else:
            return f'''<div th:each="item : ${{items}}">
    <label>
        <input type="radio" th:value="${{item.value}}" th:text="${{item.text}}" name="radioGroup" />
    </label>
</div>'''

    def convert_dropdownlist(self, match):
        """转换 DropDownList 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        css_class = attrs.get('class', '')
        
        return f'''<select class="{css_class}">
    <option th:each="item : ${{items}}" th:value="${{item.value}}" th:text="${{item.text}}"></option>
</select>'''

    def convert_listbox(self, match):
        """转换 ListBox 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        selection_mode = attrs.get('selectionmode', 'single')
        rows = attrs.get('rows', '4')
        css_class = attrs.get('class', '')
        
        multiple = ' multiple="multiple"' if selection_mode.lower() == 'multiple' else ''
        
        return f'''<select{multiple} size="{rows}" class="{css_class}">
    <option th:each="item : ${{items}}" th:value="${{item.value}}" th:text="${{item.text}}"></option>
</select>'''

    def convert_bulletedlist(self, match):
        """转换 BulletedList 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        bullet_style = attrs.get('bulletstyle', 'disc')
        css_class = attrs.get('class', '')
        
        return f'''<ul class="{css_class}" style="list-style-type: {bullet_style};">
    <li th:each="item : ${{items}}" th:text="${{item.text}}"></li>
</ul>'''

    def convert_repeater(self, match):
        """转换 Repeater 控件"""
        tag_content = match.group(0)
        content = match.group(1) if len(match.groups()) > 0 else ''
        
        # 提取 ItemTemplate 内容
        item_template = re.search(r'<ItemTemplate>(.*?)</ItemTemplate>', content, re.DOTALL)
        item_content = item_template.group(1) if item_template else '<div th:text="${item}"></div>'
        
        # 提取 HeaderTemplate
        header_template = re.search(r'<HeaderTemplate>(.*?)</HeaderTemplate>', content, re.DOTALL)
        header = header_template.group(1) if header_template else ''
        
        # 提取 FooterTemplate
        footer_template = re.search(r'<FooterTemplate>(.*?)</FooterTemplate>', content, re.DOTALL)
        footer = footer_template.group(1) if footer_template else ''
        
        # 转换模板中的绑定表达式
        item_content = self.convert_binding_expression(item_content)
        
        return f'''{header}
<div th:each="item : ${{items}}">
    {item_content}
</div>
{footer}'''

    def convert_datalist(self, match):
        """转换 DataList 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        repeat_columns = int(attrs.get('repeatcolumns', '1'))
        repeat_direction = attrs.get('repeatdirection', 'vertical')
        
        if repeat_direction.lower() == 'horizontal':
            return f'''<table>
    <tr th:each="item,rowStat : ${{items}}" th:if="${{rowStat.index % {repeat_columns} == 0}}">
        <td th:each="i : ${{#numbers.sequence(0, {repeat_columns}-1)}}" th:with="colItem=${{items[ rowStat.index + i ]}}" th:if="${{colItem != null}}">
            <div th:text="${{colItem}}"></div>
        </td>
    </tr>
</table>'''
        else:
            return f'''<div th:each="item : ${{items}}">
    <div th:text="${{item}}"></div>
</div>'''

    def convert_gridview(self, match):
        """转换 GridView 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        
        auto_generate_columns = attrs.get('autogeneratecolumns', 'false').lower()
        css_class = attrs.get('class', 'table')
        
        if auto_generate_columns == 'true':
            return f'''<table class="{css_class}">
    <thead>
        <tr>
            <th th:each="col : ${{columns}}" th:text="${{col}}"></th>
        </tr>
    </thead>
    <tbody>
        <tr th:each="item : ${{items}}">
            <td th:each="prop : ${{item}}" th:text="${{prop}}"></td>
        </tr>
    </tbody>
</table>'''
        else:
            # 需要手动定义列
            return f'''<table class="{css_class}">
    <thead>
        <tr>
            <th th:text="列1"></th>
            <th th:text="列2"></th>
        </tr>
    </thead>
    <tbody>
        <tr th:each="item : ${{items}}">
            <td th:text="${{item.property1}}"></td>
            <td th:text="${{item.property2}}"></td>
        </tr>
    </tbody>
</table>'''

    def convert_detailsview(self, match):
        """转换 DetailsView 控件"""
        return '''<table>
    <tr th:each="field : ${fields}">
        <th th:text="${field.label}"></th>
        <td th:text="${item[field.name]}"></td>
    </tr>
</table>'''

    def convert_formview(self, match):
        """转换 FormView 控件"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        content = self.convert_binding_expression(content)
        return f'<div th:object="${{item}}">{content}</div>'

    def convert_datapager(self, match):
        """转换 DataPager 控件"""
        return f'''<div class="pagination">
    <span th:each="page : ${{pages}}">
        <a th:href="@{{?page=${{page}}}}" th:text="${{page}}" th:classappend="${{page == currentPage}} ? 'active' : ''"></a>
    </span>
</div>'''

    def convert_requiredvalidator(self, match):
        """转换 RequiredFieldValidator 控件"""
        attrs = self.extract_attributes(match.group(0))
        control_to_validate = attrs.get('controltovalidate', '')
        error_message = attrs.get('errormessage', '此字段为必填项')
        
        return f'<span class="error" th:if="${{#fields.hasErrors(\'{control_to_validate}\')}}" th:errors="*{{{control_to_validate}}}">{error_message}</span>'

    def convert_regexvalidator(self, match):
        """转换 RegularExpressionValidator 控件"""
        attrs = self.extract_attributes(match.group(0))
        validation_expression = attrs.get('validationexpression', '')
        error_message = attrs.get('errormessage', '格式不正确')
        
        return f'<span class="error" th:if="${{#fields.hasErrors(\'field\')}}" th:errors="*{{field}}">{error_message}</span>'

    def convert_comparevalidator(self, match):
        """转换 CompareValidator 控件"""
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">比较验证失败</span>'

    def convert_rangevalidator(self, match):
        """转换 RangeValidator 控件"""
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">超出范围</span>'

    def convert_customvalidator(self, match):
        """转换 CustomValidator 控件"""
        return '<span class="error" th:if="${#fields.hasErrors(\'field\')}" th:errors="*{field}">自定义验证失败</span>'

    def convert_validationsummary(self, match):
        """转换 ValidationSummary 控件"""
        return f'''<div class="validation-summary" th:if="${{#fields.hasErrors()}}">
    <ul>
        <li th:each="err : ${{#fields.allErrors()}}" th:text="${{err}}"></li>
    </ul>
</div>'''

    def convert_menu(self, match):
        """转换 Menu 控件"""
        return f'''<ul class="menu">
    <li th:each="item : ${{menuItems}}" th:class="${{item.active}} ? 'active' : ''">
        <a th:href="${{item.url}}" th:text="${{item.text}}"></a>
        <ul th:if="${{item.children}}" th:each="child : ${{item.children}}">
            <li><a th:href="${{child.url}}" th:text="${{child.text}}"></a></li>
        </ul>
    </li>
</ul>'''

    def convert_treeview(self, match):
        """转换 TreeView 控件"""
        return f'''<ul class="treeview">
    <li th:each="node : ${{treeNodes}}" th:with="hasChildren=${{node.children != null && !node.children.isEmpty()}}">
        <span th:text="${{node.text}}"></span>
        <ul th:if="${{hasChildren}}">
            <li th:each="child : ${{node.children}}" th:text="${{child.text}}"></li>
        </ul>
    </li>
</ul>'''

    def convert_sitemappath(self, match):
        """转换 SiteMapPath 控件"""
        return f'''<div class="breadcrumb">
    <span th:each="node,iterStat : ${{breadcrumbs}}">
        <a th:if="${{!iterStat.last}}" th:href="${{node.url}}" th:text="${{node.title}}"></a>
        <span th:unless="${{!iterStat.last}}" th:text="${{node.title}}"></span>
        <span th:if="${{!iterStat.last}}"> &gt; </span>
    </span>
</div>'''

    def convert_sitemapdatasource(self, match):
        """转换 SiteMapDataSource 控件"""
        return '<!-- SiteMapDataSource 转换为后台注入的 siteMap 对象 -->'

    def convert_login(self, match):
        """转换 Login 控件"""
        return f'''<form th:action="@{{/login}}" method="post" class="login-form">
    <div>
        <label>用户名：</label>
        <input type="text" name="username" th:value="${{username}}" />
    </div>
    <div>
        <label>密码：</label>
        <input type="password" name="password" />
    </div>
    <div>
        <label>
            <input type="checkbox" name="rememberMe" /> 记住我
        </label>
    </div>
    <div th:if="${{error}}" class="error" th:text="${{error}}"></div>
    <button type="submit">登录</button>
</form>'''

    def convert_loginview(self, match):
        """转换 LoginView 控件"""
        content = match.group(0)
        
        # 提取不同角色的模板
        anonymous_template = re.search(r'<AnonymousTemplate>(.*?)</AnonymousTemplate>', content, re.DOTALL)
        logged_in_template = re.search(r'<LoggedInTemplate>(.*?)</LoggedInTemplate>', content, re.DOTALL)
        role_templates = re.findall(r'<RoleGroup\s+Roles="([^"]+)">(.*?)</RoleGroup>', content, re.DOTALL)
        
        result = []
        
        if anonymous_template:
            result.append(f'<div sec:authorize="isAnonymous()">{anonymous_template.group(1)}</div>')
        
        if logged_in_template:
            result.append(f'<div sec:authorize="isAuthenticated()">{logged_in_template.group(1)}</div>')
        
        for role, template in role_templates:
            result.append(f'<div sec:authorize="hasRole(\'{role}\')">{template}</div>')
        
        return '\n'.join(result)

    def convert_loginstatus(self, match):
        """转换 LoginStatus 控件"""
        return f'''<div>
    <span sec:authorize="isAnonymous()">
        <a th:href="@{{/login}}" th:text="登录"></a>
    </span>
    <span sec:authorize="isAuthenticated()">
        <a th:href="@{{/logout}}" th:text="注销"></a>
    </span>
</div>'''

    def convert_loginname(self, match):
        """转换 LoginName 控件"""
        return '<span sec:authentication="name"></span>'

    def convert_createuserwizard(self, match):
        """转换 CreateUserWizard 控件"""
        return f'''<form th:action="@{{/register}}" method="post" class="register-form">
    <div>
        <label>用户名：</label>
        <input type="text" name="username" th:value="${{user.username}}" required />
    </div>
    <div>
        <label>密码：</label>
        <input type="password" name="password" required />
    </div>
    <div>
        <label>确认密码：</label>
        <input type="password" name="confirmPassword" required />
    </div>
    <div>
        <label>邮箱：</label>
        <input type="email" name="email" th:value="${{user.email}}" />
    </div>
    <div th:if="${{error}}" class="error" th:text="${{error}}"></div>
    <button type="submit">注册</button>
</form>'''

    def convert_changepassword(self, match):
        """转换 ChangePassword 控件"""
        return f'''<form th:action="@{{/change-password}}" method="post">
    <div>
        <label>当前密码：</label>
        <input type="password" name="oldPassword" required />
    </div>
    <div>
        <label>新密码：</label>
        <input type="password" name="newPassword" required />
    </div>
    <div>
        <label>确认新密码：</label>
        <input type="password" name="confirmPassword" required />
    </div>
    <div th:if="${{error}}" class="error" th:text="${{error}}"></div>
    <button type="submit">修改密码</button>
</form>'''

    def convert_passwordrecovery(self, match):
        """转换 PasswordRecovery 控件"""
        return f'''<form th:action="@{{/forgot-password}}" method="post">
    <div>
        <label>用户名或邮箱：</label>
        <input type="text" name="username" required />
    </div>
    <div th:if="${{message}}" class="success" th:text="${{message}}"></div>
    <div th:if="${{error}}" class="error" th:text="${{error}}"></div>
    <button type="submit">找回密码</button>
</form>'''

    def convert_webpartmanager(self, match):
        """转换 WebPartManager 控件"""
        return '<!-- WebPartManager 需要前端方案实现，如 GridStack.js -->'

    def convert_webpartzone(self, match):
        """转换 WebPartZone 控件"""
        return '<div class="webpart-zone" data-drag-drop></div>'

    def convert_catalogzone(self, match):
        """转换 CatalogZone 控件"""
        return '<div class="catalog-zone"></div>'

    def convert_editorzone(self, match):
        """转换 EditorZone 控件"""
        return '<div class="editor-zone"></div>'

    def convert_scriptmanager(self, match):
        """转换 ScriptManager 控件"""
        return '''<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<script src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.13.2/jquery-ui.min.js"></script>'''

    def convert_updatepanel(self, match):
        """转换 UpdatePanel 控件"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return f'<div class="update-panel" data-ajax="true">{content}</div>'

    def convert_updateprogress(self, match):
        """转换 UpdateProgress 控件"""
        content = match.group(1) if len(match.groups()) > 0 else ''
        return f'''<div class="update-progress" style="display: none;" data-ajax-loading>
    {content}
</div>'''

    def convert_timer(self, match):
        """转换 Timer 控件"""
        attrs = self.extract_attributes(match.group(0))
        interval = attrs.get('interval', '60000')  # 毫秒
        
        return f'''<script>
setInterval(function() {{
    // 定时刷新逻辑
    $.ajax({{
        url: '/refresh',
        success: function(data) {{
            // 更新页面
        }}
    }});
}}, {interval});
</script>'''

    def convert_asynctrigger(self, match):
        """转换 AsyncPostBackTrigger 控件"""
        return '<!-- AsyncPostBackTrigger 转换为 AJAX 调用 -->'

    def convert_sqldatasource(self, match):
        """转换 SqlDataSource 控件"""
        return '<!-- SqlDataSource 需要在 Spring Data JPA 或 MyBatis 中实现 -->'

    def convert_objectdatasource(self, match):
        """转换 ObjectDataSource 控件"""
        return '<!-- ObjectDataSource 转换为 Spring Service 层调用 -->'

    def convert_linqdatasource(self, match):
        """转换 LinqDataSource 控件"""
        return '<!-- LinqDataSource 转换为 Spring Data JPA Repository -->'

    def convert_entitydatasource(self, match):
        """转换 EntityDataSource 控件"""
        return '<!-- EntityDataSource 转换为 JPA Entity -->'

    def convert_xmldatasource(self, match):
        """转换 XmlDataSource 控件"""
        return '<!-- XmlDataSource 转换为 XML 解析服务 -->'

    def convert_accessdatasource(self, match):
        """转换 AccessDataSource 控件"""
        return '<!-- AccessDataSource 需要迁移到数据库 -->'

    def convert_htmlgeneric(self, match):
        """转换 HtmlGenericControl 控件"""
        tag_content = match.group(0)
        attrs = self.extract_attributes(tag_content)
        tag_name = attrs.get('tagname', 'div')
        inner_html = attrs.get('innerhtml', '')
        
        return f'<{tag_name} th:text="${{{inner_html}}}"></{tag_name}>'

    def convert_htmlinputtext(self, match):
        """转换 HtmlInputText 控件"""
        attrs = self.extract_attributes(match.group(0))
        value = attrs.get('value', '')
        
        return f'<input type="text" th:value="${{{value}}}" />'

    def convert_htmlinputbutton(self, match):
        """转换 HtmlInputButton 控件"""
        attrs = self.extract_attributes(match.group(0))
        value = attrs.get('value', 'Button')
        
        return f'<input type="button" th:value="${{{value}}}" />'

    def convert_htmlselect(self, match):
        """转换 HtmlSelect 控件"""
        return f'''<select>
    <option th:each="item : ${{items}}" th:value="${{item.value}}" th:text="${{item.text}}"></option>
</select>'''

    def convert_htmltextarea(self, match):
        """转换 HtmlTextArea 控件"""
        attrs = self.extract_attributes(match.group(0))
        value = attrs.get('value', '')
        
        return f'<textarea th:text="${{{value}}}"></textarea>'

    def convert_reportviewer(self, match):
        """转换 ReportViewer 控件"""
        return '<!-- ReportViewer 需要替换为 JasperReports 或其他报表方案 -->'

    def convert_chart(self, match):
        """转换 Chart 控件"""
        return '<canvas class="chart" data-chart-config></canvas>'

    def convert_calendar(self, match):
        """转换 Calendar 控件"""
        return '''<div id="calendar"></div>
<script>
$(function() {
    $("#calendar").datepicker({
        dateFormat: "yy-mm-dd"
    });
});
</script>'''

    def convert_adrotator(self, match):
        """转换 AdRotator 控件"""
        return '''<div class="ad-rotator" data-ad-rotator>
    <img th:each="ad : ${ads}" th:src="${ad.imageUrl}" th:alt="${ad.altText}" style="display: none;" />
</div>'''

    def convert_substitution(self, match):
        """转换 Substitution 控件"""
        return '<div data-substitution></div>'

    def convert_localize(self, match):
        """转换 Localize 控件"""
        attrs = self.extract_attributes(match.group(0))
        text = attrs.get('th:text', attrs.get('text', ''))
        
        return f'<span th:text="#{{{text}}}"></span>'

    def convert_multiview(self, match):
        """转换 MultiView 控件"""
        return '<div th:switch="${activeViewId}"></div>'

    def convert_view(self, match):
        """转换 View 控件"""
        attrs = self.extract_attributes(match.group(0))
        view_id = attrs.get('id', '')
        content = match.group(1) if len(match.groups()) > 0 else ''
        
        return f'<div th:case="\'{view_id}\'">{content}</div>'

    def convert_wizard(self, match):
        """转换 Wizard 控件"""
        return '''<div class="wizard" data-wizard>
    <div class="wizard-steps">
        <span th:each="step,iterStat : ${steps}" 
              th:classappend="${iterStat.index == currentStep} ? 'active' : ''"
              th:text="${step.title}"></span>
    </div>
    <div class="wizard-content" th:each="step,iterStat : ${steps}" 
         th:if="${iterStat.index == currentStep}">
        <div th:utext="${step.content}"></div>
    </div>
    <div class="wizard-buttons">
        <button onclick="prevStep()">上一步</button>
        <button onclick="nextStep()">下一步</button>
    </div>
</div>'''

    def convert_wizardstep(self, match):
        """转换 WizardStep 控件"""
        attrs = self.extract_attributes(match.group(0))
        title = attrs.get('title', 'Step')
        content = match.group(1) if len(match.groups()) > 0 else ''
        
        return f'<div class="wizard-step" data-title="{title}">{content}</div>'

    def convert_fileupload(self, match):
        """转换 FileUpload 控件"""
        return '<input type="file" name="file" />'

    def convert_hiddenfield(self, match):
        """转换 HiddenField 控件"""
        attrs = self.extract_attributes(match.group(0))
        value = attrs.get('th:text', attrs.get('value', ''))
        
        return f'<input type="hidden" th:value="${{{value}}}" />'

    def convert_xml(self, match):
        """转换 Xml 控件"""
        return '<div th:replace="xml/content"></div>'

    def process_file(self, file_path, output_path):
        """处理单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 查找所有 <asp: 开头的标签
            for tag_name, convert_func in self.asp_tag_mapping.items():
                # 匹配完整的标签（包括嵌套内容）
                if 'asp:Repeater' in tag_name or 'asp:DataList' in tag_name or 'asp:GridView' in tag_name:
                    pattern = re.compile(f'<{tag_name}[^>]*>(.*?)</{tag_name}>', re.IGNORECASE | re.DOTALL)
                else:
                    pattern = re.compile(f'<{tag_name}[^>]*/?>', re.IGNORECASE | re.DOTALL)
                
                content = pattern.sub(convert_func, content)
            
            # 移除剩余的未匹配标签
            content = re.sub(r'<asp:\w+[^>]*>', '', content)
            content = re.sub(r'</asp:\w+>', '', content)
            
            # 移除 runAt 属性
            content = re.sub(r'\s+runat="server"', '', content, flags=re.IGNORECASE)
            
            # 添加 Thymeleaf 命名空间
            if '<html' in content and 'xmlns:th=' not in content:
                content = re.sub(
                    r'(<html\s*)',
                    r'\1xmlns:th="http://www.thymeleaf.org" xmlns:sec="http://www.thymeleaf.org/extras/spring-security" ',
                    content
                )
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入转换后的文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.conversion_count += 1
            print(f"  ✓ 转换成功: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ 转换失败: {str(e)}")
            return False

    def process_directory(self, input_dir, output_dir):
        """处理整个目录"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        if not input_path.exists():
            print(f"错误: 目录不存在 - {input_dir}")
            return
        
        print(f"\n开始转换 ASPX 文件...")
        print(f"输入: {input_path}")
        print(f"输出: {output_path}")
        print("-" * 60)
        
        # 查找所有 .aspx 文件
        aspx_files = list(input_path.rglob("*.aspx"))
        
        if not aspx_files:
            print("未找到 .aspx 文件")
            return
        
        print(f"找到 {len(aspx_files)} 个文件\n")
        
        for aspx_file in aspx_files:
            rel_path = aspx_file.relative_to(input_path)
            output_file = output_path / rel_path.with_suffix('.html')
            self.process_file(aspx_file, output_file)
        
        print("-" * 60)
        print(f"\n转换完成! 成功转换 {self.conversion_count} 个文件")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='完整的 ASPX to Thymeleaf 转换器')
    parser.add_argument('input', help='输入目录')
    parser.add_argument('-o', '--output', help='输出目录', default='./thymeleaf_output')
    
    args = parser.parse_args()
    
    converter = CompleteASPXConverter()
    converter.process_directory(args.input, args.output)


if __name__ == "__main__":
    main()
