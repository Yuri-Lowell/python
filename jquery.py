#!/usr/bin/env python3
"""
jQuery 1.4.1 → 3.7.1 自动迁移脚本
使用前请备份代码！
"""

import re
import os
import json
from pathlib import Path
from datetime import datetime

class jQueryUpgrader:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.changes = []
        self.manual_check_items = []
        
    def log_change(self, filepath, line_no, old_code, new_code, reason):
        """记录修改"""
        self.changes.append({
            'file': filepath,
            'line': line_no,
            'old': old_code.strip(),
            'new': new_code.strip(),
            'reason': reason
        })
    
    def log_manual_check(self, filepath, line_no, code, reason):
        """记录需要手动检查的项目"""
        self.manual_check_items.append({
            'file': filepath,
            'line': line_no,
            'code': code.strip(),
            'reason': reason
        })
    
    def fix_event_binding(self, content, filepath):
        """修复事件绑定方法"""
        lines = content.split('\n')
        new_lines = []
        
        # .bind() → .on()
        # .unbind() → .off()
        # .delegate() → .on()
        # .undelegate() → .off()
        
        for i, line in enumerate(lines):
            original = line
            
            # .bind(events, handler) → .on(events, handler)
            if re.search(r'\.bind\s*\(', line):
                line = re.sub(r'\.bind\s*\(', '.on(', line)
                self.log_change(filepath, i+1, original, line, '.bind() 已废弃，使用 .on() 替代')
            
            # .unbind() → .off()
            if re.search(r'\.unbind\s*\(', line):
                line = re.sub(r'\.unbind\s*\(', '.off(', line)
                self.log_change(filepath, i+1, original, line, '.unbind() 已废弃，使用 .off() 替代')
            
            # .delegate(selector, events, handler) → .on(events, selector, handler)
            delegate_match = re.search(r'\.delegate\s*\(\s*([^,]+),\s*([^,]+),\s*(.+)\)', line)
            if delegate_match:
                selector = delegate_match.group(1)
                events = delegate_match.group(2)
