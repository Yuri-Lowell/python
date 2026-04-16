#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASPX to Thymeleaf Converter with jQuery Upgrade
将.aspx文件转换为Thymeleaf模板，同时升级jQuery从1.4.1到3.7.1
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

class ASPXToThymeleafConverter:
    def __init__(self):
        # jQuery 1.4.1 到 3.7.1 的兼容性映射
        self.jquery_upgrade_rules = [
            # .live() 替换为 .on()
            (r'\.live\(([^)]+)\)', r'.on(\1)'),
            # .die() 替换为 .off()
            (r'\.die\(([^)]*)\)', r'.off(\1)'),
            # .bind() 推荐改为 .on()
            (r'\.bind\(([^)]+)\)', r'.on(\1)'),
            # .unbind() 推荐改为 .off()
            (r'\.unbind\(([^)]*)\)', r'.off(\1)'),
            # .delegate() 改为 .on()
            (r'\.delegate\(([^,]+),\s*([^,]+),\s*([^)]+)\)', r'.on(\2, \1, \3)'),
            # .undelegate() 改为 .off()
            (r'\.undelegate\(([^)]+)\)', r'.off(\1)'),
            # .click() 等快捷方法仍可用，但建议检查
            # .attr('checked') 改为 .prop('checked')
            (r'\.attr\([\'"]checked[\'"]\)', r'.prop("checked")'),
            (r'\.attr\([\'"]disabled[\'"]\)', r'.prop("disabled")'),
            (r'\.attr\([\'"]selected[\'"]\)', r'.prop("selected")'),
            (r'\.attr\([\'"]readonly[\'"]\)', r'.prop("readonly")'),
            # .removeAttr('checked') 改为 .prop('checked', false)
            (r'\.removeAttr\([\'"]checked[\'"]\)', r'.prop("checked", false)'),
            # .val() 对于 select 多个值时的处理
            # $.browser 已移除
            (r'\$\.browser', r'false /* $.browser removed in jQuery 1.9+ */'),
            (r'\$\.browser\.([a-z]+)', r'navigator.userAgent.indexOf("\1") !== -1'),
            # .size() 改为 .length
            (r'\.size\(\)', r'.length'),
            # .andSelf() 改为 .addBack()
            (r'\.andSelf\(\)', r'.addBack()'),
            # .error() 改为 .on('error')
            (r'\.error\(([^)]+)\)', r'.on("error", \1)'),
            # .load() 事件改为 .on('load')
            (r'\.load\(function\(([^)]*)\)', r'.on("load", function(\1)'),
            # .unload() 事件改为 .on('unload')
            (r'\.unload\(([^)]+)\)', r'.on("unload", \1)'),
            # .toggle() 事件处理程序已改变
            (r'\.toggle\(([^,]+),\s*([^)]+)\)', r'.click(function() { if($(this).data("clickCount")) { \2(); $(this).data("clickCount", false); } else { \1(); $(this).data("clickCount", true); } })'),
        ]
        
        # ASPX 标签到 Thymeleaf 的转换规则
        self.aspx_rules = [
            # 服务器控件转换
            (r'<asp:Label\s+([^>]*?)ID="([^"]+)"\s*([^>]*?)Text="([^"]+)"\s*([^>]*?)/?>', 
             r'<span th:text="\4" \1\3\5></span>'),
            (r'<asp:Label\s+([^>]*?)Text="<%#\s*Eval\("([^"]+)"\)\s*%>"\s*([^>]*?)/?>', 
             r'<span th:text="${item.\2}" \1\3></span>'),
            (r'<asp:Label\s+([^>]*?)Text="<%=([^%]+)%>"\s*([^>]*?)/?>', 
             r'<span th:text="\2" \1\3></span>'),
            
            # TextBox 转换
            (r'<asp:TextBox\s+([^>]*?)ID="([^"]+)"\s*([^>]*?)Text="([^"]+)"\s*([^>]*?)/?>', 
             r'<input type="text" th:value="\4" id="\2" \1\3\5 />'),
            (r'<asp:TextBox\s+([^>]*?)TextMode="Password"\s*([^>]*?)/?>', 
             r'<input type="password" \1\2 />'),
            (r'<asp:TextBox\s+([^>]*?)TextMode="MultiLine"\s*([^>]*?)/?>', 
             r'<textarea \1\2></textarea>'),
            
            # Button 转换
            (r'<asp:Button\s+([^>]*?)Text="([^"]+)"\s*([^>]*?)/?>', 
             r'<button type="submit" th:text="\2" \1\3></button>'),
            
            # HyperLink 转换
            (r'<asp:HyperLink\s+([^>]*?)NavigateUrl="([^"]+)"\s*([^>]*?)Text="([^"]+)"\s*([^>]*?)/?>', 
             r'<a th:href="\2" th:text="\4" \1\3\5></a>'),
            (r'<asp:HyperLink\s+([^>]*?)NavigateUrl="<%#\s*Eval\("([^"]+)"\)\s*%>"\s*([^>]*?)Text="([^"]+)"\s*([^>]*?)/?>', 
             r'<a th:href="@{${item.\2}}" th:text="\4" \1\3\5></a>'),
            
            # Image 转换
            (r'<asp:Image\s+([^>]*?)ImageUrl="([^"]+)"\s*([^>]*?)/?>', 
             r'<img th:src="\2" \1\3 />'),
            (r'<asp:Image\s+([^>]*?)ImageUrl="<%#\s*Eval\("([^"]+)"\)\s*%>"\s*([^>]*?)/?>', 
             r'<img th:src="${item.\2}" \1\3 />'),
            
            # CheckBox 转换
            (r'<asp:CheckBox\s+([^>]*?)Text="([^"]+)"\s*([^>]*?)/?>', 
             r'<label><input type="checkbox" \1\3 /> <span th:text="\2"></span></label>'),
            (r'<asp:CheckBox\s+([^>]*?)Checked="true"\s*([^>]*?)/?>', 
             r'<input type="checkbox" checked="checked" \1\2 />'),
            
            # RadioButton 转换
            (r'<asp:RadioButton\s+([^>]*?)Text="([^"]+)"\s*([^>]*?)/?>', 
             r'<label><input type="radio" \1\3 /> <span th:text="\2"></span></label>'),
            
            # DropDownList 转换
            (r'<asp:DropDownList\s+([^>]*?)ID="([^"]+)"\s*([^>]*?)/?>', 
             r'<select id="\2" \1\3>\n    <option th:each="opt : ${options}" th:value="${opt.value}" th:text="${opt.label}"></option>\n</select>'),
            
            # Panel 转换
            (r'<asp:Panel\s+([^>]*?)Visible="false"\s*([^>]*?)>(.*?)</asp:Panel>', 
             r'<div th:if="false" \1\2>\3</div>'),
            (r'<asp:Panel\s+([^>]*?)>(.*?)</asp:Panel>', 
             r'<div \1>\2</div>'),
            
            # PlaceHolder 转换
            (r'<asp:PlaceHolder\s+([^>]*?)>(.*?)</asp:PlaceHolder>', 
             r'\2'),
            
            # Repeater 转换
            (r'<asp:Repeater\s+([^>]*?)ID="([^"]+)"\s*([^>]*?)>', 
             r'<div th:each="item : ${items}">'),
            (r'<asp:Repeater>', r'<div th:each="item : ${items}">'),
            (r'</asp:Repeater>', r'</div>'),
            (r'<ItemTemplate>(.*?)</ItemTemplate>', r'\1'),
            (r'<AlternatingItemTemplate>(.*?)</AlternatingItemTemplate>', r'\1'),
            (r'<HeaderTemplate>(.*?)</HeaderTemplate>', r'\1'),
            (r'<FooterTemplate>(.*?)</FooterTemplate>', r'\1'),
            
            # 数据绑定表达式
            (r'<%#\s*Eval\("([^"]+)"\)\s*%>', r'${item.\1}'),
            (r'<%#\s*Eval\("([^"]+)",\s*"([^"]+)"\)\s*%>', r'${#strings.defaultString(item.\1, "\2")}'),
            (r'<%=([^%]+)%>', r'${(\1)}'),
            (r'<%:([^%]+)%>', r'${(\1)}'),
            
            # 条件语句
            (r'<% if\s*\(([^)]+)\)\s*{ %>', r'<div th:if="\1">'),
            (r'<% } else if\s*\(([^)]+)\)\s*{ %>', r'</div><div th:if="\1">'),
            (r'<% } else { %>', r'</div><div th:unless="condition">'),
            (r'<% } %>', r'</div>'),
            
            # 循环语句
            (r'<% foreach\s*\(\s*var\s+(\w+)\s+in\s+(\w+)\s*\)\s*{ %>', 
             r'<div th:each="\1 : ${\2}">'),
            (r'<% for\s*\(\s*int\s+(\w+)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\w+)\s*;\s*\1\+\+\s*\)\s*{ %>', 
             r'<div th:each="\1 : ${#numbers.sequence(\2, \3)}">'),
            
            # 注释转换
            (r'<%--(.*?)--%>', r'<!--/* \1 */-->'),
            
            # 移除 runAt="server"
            (r'\s+runat="server"', ''),
            
            # CssClass 转换为 class
            (r'CssClass="([^"]+)"', r'class="\1"'),
        ]
        
        self.conversion_count = 0
        self.error_count = 0

    def upgrade_jquery_code(self, content):
        """升级 jQuery 代码从 1.4.1 到 3.7.1"""
        
        # 替换 jQuery 版本引用
        content = re.sub(
            r'jquery[.-]1\.4\.1\.min\.js',
            'jquery-3.7.1.min.js',
            content,
            flags=re.IGNORECASE
        )
        content = re.sub(
            r'jquery[.-]1\.4\.1\.js',
            'jquery-3.7.1.min.js',
            content,
            flags=re.IGNORECASE
        )
        content = re.sub(
            r'["\']1\.4\.1["\']',
            '"3.7.1"',
            content
        )
        
        # 应用 jQuery API 升级规则
        for pattern, replacement in self.jquery_upgrade_rules:
            try:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
            except re.error:
                continue
        
        # 添加兼容性检查脚本（如果需要）
        if '<script' in content and 'jQuery' in content:
            compatibility_script = '''
<script>
// jQuery 3.x 兼容性补丁
if (typeof jQuery !== 'undefined') {
    // 确保 jQuery 3.x 兼容旧代码
    jQuery.fn.load = function(callback) {
        if (typeof callback === 'function') {
            this.on('load', callback);
        }
        return this;
    };
}
</script>
'''
            # 在第一个 script 标签前插入兼容脚本
            content = content.replace('<script', compatibility_script + '<script', 1)
        
        return content

    def convert_aspx_to_thymeleaf(self, content):
        """转换 ASPX 标签为 Thymeleaf"""
        
        # 记录原始内容长度
        original_length = len(content)
        
        # 应用转换规则
        for pattern, replacement in self.aspx_rules:
            try:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE | re.DOTALL)
            except re.error as e:
                print(f"  警告: 正则表达式错误 - {pattern}: {e}")
                continue
        
        # 处理特殊的 jQuery 升级
        content = self.upgrade_jquery_code(content)
        
        # 添加 Thymeleaf 命名空间（如果没有）
        if 'xmlns:th=' not in content and '<html' in content:
            content = re.sub(
                r'(<html\s*)',
                r'\1xmlns:th="http://www.thymeleaf.org" ',
                content
            )
        
        # 添加标准 Thymeleaf 布局声明
        if '<!DOCTYPE html>' in content and 'thymeleaf' not in content:
            content = content.replace(
                '<!DOCTYPE html>',
                '<!DOCTYPE html>\n<!-- Thymeleaf Template - Converted from ASPX -->'
            )
        
        print(f"    转换: {original_length} -> {len(content)} 字符")
        return content

    def process_file(self, file_path, output_path):
        """处理单个文件"""
        try:
            print(f"处理: {file_path}")
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 转换内容
            converted_content = self.convert_aspx_to_thymeleaf(content)
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入转换后的文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(converted_content)
            
            self.conversion_count += 1
            print(f"  ✓ 已保存: {output_path}")
            
            # 创建转换日志
            log_path = output_path.with_suffix('.conversion.log')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"转换时间: {datetime.now()}\n")
                f.write(f"源文件: {file_path}\n")
                f.write(f"目标文件: {output_path}\n")
                f.write(f"原始大小: {len(content)} 字符\n")
                f.write(f"转换后大小: {len(converted_content)} 字符\n")
            
            return True
            
        except Exception as e:
            self.error_count += 1
            print(f"  ✗ 错误: {str(e)}")
            return False

    def process_directory(self, input_dir, output_dir=None, recursive=True):
        """处理整个目录"""
        input_path = Path(input_dir)
        
        if not input_path.exists():
            print(f"错误: 目录不存在 - {input_dir}")
            return
        
        # 设置输出目录
        if output_dir is None:
            output_path = input_path.parent / f"{input_path.name}_thymeleaf"
        else:
            output_path = Path(output_dir)
        
        print(f"\n开始转换 ASPX 文件...")
        print(f"输入目录: {input_path}")
        print(f"输出目录: {output_path}")
        print(f"递归处理: {'是' if recursive else '否'}")
        print("-" * 60)
        
        # 查找所有 .aspx 文件
        if recursive:
            aspx_files = list(input_path.rglob("*.aspx"))
        else:
            aspx_files = list(input_path.glob("*.aspx"))
        
        if not aspx_files:
            print("未找到任何 .aspx 文件")
            return
        
        print(f"找到 {len(aspx_files)} 个 .aspx 文件\n")
        
        # 处理每个文件
        for aspx_file in aspx_files:
            # 计算相对路径
            rel_path = aspx_file.relative_to(input_path)
            # 生成输出路径（改为 .html 扩展名）
            output_file = output_path / rel_path.with_suffix('.html')
            # 处理文件
            self.process_file(aspx_file, output_file)
        
        # 复制其他资源文件（可选）
        self.copy_resources(input_path, output_path)
        
        # 打印统计信息
        print("-" * 60)
        print(f"\n转换完成!")
        print(f"成功: {self.conversion_count} 个文件")
        print(f"失败: {self.error_count} 个文件")
        print(f"输出目录: {output_path}")
        
        # 生成转换报告
        self.generate_report(output_path)

    def copy_resources(self, input_path, output_path):
        """复制 JS、CSS 等资源文件"""
        resource_extensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico']
        
        for ext in resource_extensions:
            for resource_file in input_path.rglob(f"*{ext}"):
                if '.aspx' not in str(resource_file).lower():
                    rel_path = resource_file.relative_to(input_path)
                    dest_file = output_path / rel_path
                    
                    # 复制文件
                    if not dest_file.exists():
                        try:
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(resource_file, dest_file)
                            print(f"  复制资源: {rel_path}")
                        except Exception as e:
                            print(f"  复制失败 {rel_path}: {e}")

    def generate_report(self, output_path):
        """生成转换报告"""
        report_path = output_path / "CONVERSION_REPORT.md"
        
        report_content = f"""# ASPX to Thymeleaf 转换报告

生成时间: {datetime.now()}

## 转换统计
- 转换文件数: {self.conversion_count}
- 错误文件数: {self.error_count}
- jQuery 升级: 1.4.1 → 3.7.1

## 转换说明

### ASPX 到 Thymeleaf 映射
- `asp:Label` → `<span th:text="...">`
- `asp:TextBox` → `<input type="text" th:value="...">`
- `asp:Button` → `<button type="submit">`
- `asp:HyperLink` → `<a th:href="...">`
- `asp:Repeater` → `<div th:each="...">`
- `<%= ... %>` → `${...}`
- `<%# Eval(...) %>` → `${{item...}}`

### jQuery 升级变更
- `.live()` → `.on()`
- `.die()` → `.off()`
- `.bind()` → `.on()`
- `.attr('checked')` → `.prop('checked')`
- `.size()` → `.length`
- `$.browser` → 已移除，使用特性检测

## 后续手动检查项
1. 检查数据绑定表达式是否正确
2. 验证事件处理程序
3. 测试 jQuery 选择器兼容性
4. 更新 AJAX 请求 URL
5. 处理 ViewState 相关代码
6. 调整 CSS 类名映射

## 注意事项
- 服务器端代码已移除，需要在 Controller 中实现
- 事件处理需要在后端重新绑定
- 需要配置 Thymeleaf 视图解析器
- 建议测试所有交互功能

---
*此报告由 ASPX to Thymeleaf Converter 自动生成*
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\n转换报告已生成: {report_path}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ASPX to Thymeleaf Converter with jQuery Upgrade')
    parser.add_argument('input', help='输入目录路径')
    parser.add_argument('-o', '--output', help='输出目录路径（默认为 input_thymeleaf）')
    parser.add_argument('--no-recursive', action='store_true', help='不递归处理子目录')
    parser.add_argument('--copy-resources', action='store_true', help='复制资源文件（JS/CSS/图片）')
    
    args = parser.parse_args()
    
    # 创建转换器并执行
    converter = ASPXToThymeleafConverter()
    converter.process_directory(
        args.input,
        args.output,
        recursive=not args.no_recursive
    )


if __name__ == "__main__":
    main()
