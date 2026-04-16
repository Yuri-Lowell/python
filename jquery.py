#!/usr/bin/env python3
"""
jQuery 1.4.1 → 3.7.1 自动迁移脚本
用法: python jq_upgrade.py /path/to/folder
"""

import re
import os
import sys
import json
from pathlib import Path
from datetime import datetime

class jQueryUpgrader:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.changes = []
        self.manual_check_items = []
        
    def log_change(self, filepath, line_no, old_code, new_code, reason):
        self.changes.append({
            'file': filepath,
            'line': line_no,
            'old': old_code.strip()[:100],
            'new': new_code.strip()[:100],
            'reason': reason
        })
    
    def log_manual_check(self, filepath, line_no, code, reason):
        self.manual_check_items.append({
            'file': filepath,
            'line': line_no,
            'code': code.strip()[:100],
            'reason': reason
        })
    
    def upgrade_jquery_version(self, content, filepath):
        """升级jQuery库引用"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            # 替换jQuery 1.4.1引用为3.7.1
            if 'jquery' in line.lower() and '1.4.1' in line:
                line = line.replace('1.4.1', '3.7.1')
                line = line.replace('jquery-1.4.1', 'jquery-3.7.1')
                line = line.replace('jquery.min.js', 'jquery-3.7.1.min.js')
                self.log_change(filepath, i+1, original, line, '升级jQuery版本号')
            
            # 如果没有指定版本，添加新版本（可选）
            if 'jquery' in line.lower() and '.js' in line and '3.7.1' not in line:
                if 'googleapis' in line or 'code.jquery' in line:
                    line = re.sub(r'jquery/[0-9.]+/', 'jquery/3.7.1/', line)
                    line = re.sub(r'jquery-[0-9.]+', 'jquery-3.7.1', line)
                    self.log_change(filepath, i+1, original, line, '更新CDN引用')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_event_binding(self, content, filepath):
        """修复事件绑定"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            
            # .bind() → .on()
            if re.search(r'\.bind\s*\(', line) and not re.search(r'\.bind\s*\([^)]*\)\s*;', line):
                line = re.sub(r'\.bind\s*\(', '.on(', line)
                self.log_change(filepath, i+1, original, line, '.bind() → .on()')
            
            # .unbind() → .off()
            if re.search(r'\.unbind\s*\(', line):
                line = re.sub(r'\.unbind\s*\(', '.off(', line)
                self.log_change(filepath, i+1, original, line, '.unbind() → .off()')
            
            # .live() → .on()
            live_match = re.search(r'\.live\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,', line)
            if live_match:
                event = live_match.group(1)
                # 将 .live('click', fn) 改为 .on('click', fn)
                line = re.sub(r'\.live\s*\(', '.on(', line)
                self.log_change(filepath, i+1, original, line, '.live() → .on()，需要确保事件绑定到document')
            
            # .die() → .off()
            if re.search(r'\.die\s*\(', line):
                line = re.sub(r'\.die\s*\(', '.off(', line)
                self.log_change(filepath, i+1, original, line, '.die() → .off()')
            
            # .delegate() → .on()
            if re.search(r'\.delegate\s*\(', line):
                # .delegate(selector, event, handler) → .on(event, selector, handler)
                line = re.sub(r'\.delegate\s*\(', '.on(', line)
                self.log_change(filepath, i+1, original, line, '.delegate() → .on()，参数顺序需手动检查')
                self.log_manual_check(filepath, i+1, original, '请检查.on()参数顺序是否正确')
            
            # .toggle() 事件版本（非动画）已移除
            if re.search(r'\.toggle\s*\(\s*function', line):
                self.log_manual_check(filepath, i+1, original, '.toggle(event) 在3.x中已移除，请改用.click()或其他方式')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_attr_prop(self, content, filepath):
        """修复attr和prop问题"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            
            # .removeAttr('checked/disabled/selected') → .prop()
            if re.search(r'\.removeAttr\s*\(\s*[\'"]checked[\'"]', line):
                line = re.sub(r'\.removeAttr\s*\(\s*[\'"]checked[\'"]\s*\)', '.prop("checked", false)', line)
                self.log_change(filepath, i+1, original, line, '.removeAttr("checked") → .prop("checked", false)')
            
            if re.search(r'\.removeAttr\s*\(\s*[\'"]disabled[\'"]', line):
                line = re.sub(r'\.removeAttr\s*\(\s*[\'"]disabled[\'"]\s*\)', '.prop("disabled", false)', line)
                self.log_change(filepath, i+1, original, line, '.removeAttr("disabled") → .prop("disabled", false)')
            
            # .attr('checked') → .prop('checked')
            if re.search(r'\.attr\s*\(\s*[\'"]checked[\'"]\s*\)', line):
                self.log_manual_check(filepath, i+1, original, '.attr("checked") 应改为 .prop("checked")')
            
            # .attr('value') 在某些情况下需要改为 .val()
            if re.search(r'\.attr\s*\(\s*[\'"]value[\'"]\s*,', line):
                self.log_manual_check(filepath, i+1, original, '.attr("value", val) 建议改为 .val(val)')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_ready_event(self, content, filepath):
        """修复ready事件"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            
            # $(document).ready(fn) → $(fn)
            if re.search(r'\$\(document\)\.ready\s*\(', line):
                line = re.sub(r'\$\(document\)\.ready\s*\(', '$(', line)
                self.log_change(filepath, i+1, original, line, '$(document).ready(fn) → $(fn)')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_ajax_methods(self, content, filepath):
        """修复AJAX方法"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            
            # .load() 方法签名变化
            if re.search(r'\.load\s*\(\s*[\'"]', line) and 'url' not in line.lower():
                self.log_manual_check(filepath, i+1, original, '.load() 方法在3.x中变化，请检查回调函数')
            
            # .success() / .error() → .done() / .fail()
            if re.search(r'\.success\s*\(', line):
                line = re.sub(r'\.success\s*\(', '.done(', line)
                self.log_change(filepath, i+1, original, line, '.success() → .done()')
            
            if re.search(r'\.error\s*\(', line):
                # 注意区分.error()事件方法
                if re.search(r'\$\.\w+.*\.error\s*\(', line):
                    line = re.sub(r'\.error\s*\(', '.fail(', line)
                    self.log_change(filepath, i+1, original, line, '.error() → .fail()')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_selector_changes(self, content, filepath):
        """修复选择器变化"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            
            # :checked 在3.x中更严格
            if re.search(r':checked', line):
                self.log_manual_check(filepath, i+1, original, ':checked 选择器行为变化，请测试checkbox/radio')
            
            # 属性选择器大小写敏感
            if re.search(r'\[.*=[^\]]*\]', line):
                self.log_manual_check(filepath, i+1, original, '属性选择器在3.x中大小写敏感')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_animation_changes(self, content, filepath):
        """修复动画变化"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            
            # .stop() 参数变化
            if re.search(r'\.stop\s*\(\s*true\s*,\s*true\s*\)', line):
                self.log_manual_check(filepath, i+1, original, '.stop(true, true) 在3.x中行为不同')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_browser_detection(self, content, filepath):
        """修复浏览器检测（已移除）"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            
            if re.search(r'\$\.browser', line):
                self.log_manual_check(filepath, i+1, original, '$.browser 已移除，请使用特征检测或Modernizr')
            
            if re.search(r'\$\.support', line):
                self.log_manual_check(filepath, i+1, original, '$.support 部分属性已移除')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_shorthand_methods(self, content, filepath):
        """修复简写方法"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            original = line
            
            # .click(fn), .change(fn) 等仍然支持，但需要检查
            if re.search(r'\.click\s*\(\s*function', line):
                # 这仍然有效，但记录一下
                pass
            
            # .hover() 参数变化
            if re.search(r'\.hover\s*\(\s*function\s*\([^)]*\)\s*{[^}]*}\s*,\s*function', line):
                self.log_manual_check(filepath, i+1, original, '.hover() 在3.x中只接受一个或两个函数参数')
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def upgrade_file(self, filepath):
        """升级单个HTML文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ 读取失败: {e}")
            return False
        
        original = content
        
        # 执行所有转换
        content = self.upgrade_jquery_version(content, str(filepath))
        content = self.fix_event_binding(content, str(filepath))
        content = self.fix_attr_prop(content, str(filepath))
        content = self.fix_ready_event(content, str(filepath))
        content = self.fix_ajax_methods(content, str(filepath))
        content = self.fix_selector_changes(content, str(filepath))
        content = self.fix_animation_changes(content, str(filepath))
        content = self.fix_browser_detection(content, str(filepath))
        content = self.fix_shorthand_methods(content, str(filepath))
        
        if content != original:
            if not self.dry_run:
                try:
                    # 备份原文件
                    backup_path = str(filepath) + '.bak'
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(original)
                    
                    # 写入新文件
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"  ✅ 已升级: {filepath}")
                    return True
                except Exception as e:
                    print(f"  ❌ 写入失败: {e}")
                    return False
            else:
                print(f"  🔍 模拟升级: {filepath}")
                return True
        
        print(f"  ⏭️  无需修改: {filepath}")
        return False
    
    def process_folder(self, folder_path):
        """处理文件夹内所有HTML文件"""
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"❌ 文件夹不存在: {folder_path}")
            return
        
        html_files = list(folder.rglob('*.html')) + list(folder.rglob('*.htm'))
        
        print(f"\n📁 扫描文件夹: {folder_path}")
        print(f"📄 找到 {len(html_files)} 个HTML文件\n")
        
        modified_count = 0
        
        for html_file in html_files:
            if self.upgrade_file(html_file):
                modified_count += 1
        
        # 生成报告
        self.generate_report(folder_path)
        
        print(f"\n{'='*50}")
        print(f"✅ 完成！")
        print(f"📊 升级文件: {modified_count}/{len(html_files)}")
        print(f"⚠️  需要手动检查: {len(self.manual_check_items)} 项")
        print(f"📄 详细报告: upgrade_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        if self.dry_run:
            print("\n⚠️  这是预览模式，未实际修改文件")
            print("   移除 --dry-run 参数以执行实际修改")
    
    def generate_report(self, folder_path):
        """生成JSON报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'folder': str(folder_path),
            'dry_run': self.dry_run,
            'changes': self.changes,
            'manual_check_items': self.manual_check_items
        }
        
        report_file = f"upgrade_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if not self.dry_run:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印需要手动检查的项
        if self.manual_check_items:
            print(f"\n{'='*50}")
            print("⚠️  请手动检查以下项目:")
            for item in self.manual_check_items[:20]:  # 只显示前20条
                print(f"\n  📁 {item['file']}:{item['line']}")
                print(f"    代码: {item['code']}")
                print(f"    原因: {item['reason']}")
            
            if len(self.manual_check_items) > 20:
                print(f"\n  ... 还有 {len(self.manual_check_items) - 20} 项，详见报告文件")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("用法: python jq_upgrade.py /path/to/folder [--dry-run]")
        print("\n选项:")
        print("  --dry-run    预览模式，不实际修改文件")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    
    upgrader = jQueryUpgrader(dry_run=dry_run)
    upgrader.process_folder(folder_path)


if __name__ == '__main__':
    main()
