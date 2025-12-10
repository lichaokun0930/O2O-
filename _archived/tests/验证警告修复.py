# -*- coding: utf-8 -*-
"""
Dashboard警告修复验证脚本
快速检查修复是否生效
"""

import sys
import re

def check_warnings_suppression():
    """检查警告抑制代码是否存在"""
    with open('dashboard_v2.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        '警告过滤器': 'warnings.filterwarnings',
        'Plotly模板配置': 'pio.templates.default',
        '固定margin配置': 'margin=dict',
        'autosize=False': 'autosize=False'
    }
    
    results = {}
    for name, pattern in checks.items():
        count = len(re.findall(pattern, content))
        results[name] = count
        status = '✅' if count > 0 else '❌'
        print(f"{status} {name}: {count}处")
    
    return all(v > 0 for v in results.values())

def check_callback_returns():
    """检查回调函数返回值"""
    with open('dashboard_v2.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    problematic_returns = []
    for i, line in enumerate(lines, 1):
        # 检查可能导致问题的返回语句
        if 'return []' in line and 'Output' in ''.join(lines[max(0, i-10):i]):
            problematic_returns.append((i, line.strip()))
    
    if problematic_returns:
        print(f"\n⚠️ 发现{len(problematic_returns)}处可能的问题返回值:")
        for line_num, line_content in problematic_returns[:5]:
            print(f"  第{line_num}行: {line_content}")
    else:
        print("\n✅ 未发现明显的问题返回值")
    
    return len(problematic_returns) == 0

def check_graph_configs():
    """检查图表配置完整性"""
    with open('dashboard_v2.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找所有update_layout调用
    layout_calls = re.findall(r'fig\.update_layout\([^)]+\)', content, re.DOTALL)
    
    no_margin = []
    for i, call in enumerate(layout_calls):
        if 'margin' not in call:
            no_margin.append(i+1)
    
    print(f"\n📊 图表配置检查:")
    print(f"  总计update_layout调用: {len(layout_calls)}次")
    print(f"  包含margin配置: {len(layout_calls) - len(no_margin)}次")
    
    if no_margin:
        print(f"  ⚠️ 缺少margin配置: {len(no_margin)}处")
        return False
    else:
        print(f"  ✅ 所有图表均已配置margin")
        return True

if __name__ == '__main__':
    print("=" * 60)
    print("  Dashboard v2.2.1 警告修复验证")
    print("=" * 60)
    print()
    
    print("[1/3] 检查警告抑制代码...")
    check1 = check_warnings_suppression()
    
    print("\n[2/3] 检查回调返回值...")
    check2 = check_callback_returns()
    
    print("\n[3/3] 检查图表配置...")
    check3 = check_graph_configs()
    
    print("\n" + "=" * 60)
    if all([check1, check2, check3]):
        print("✅ 所有检查通过！修复已生效")
        print("\n建议:")
        print("1. 使用 启动优化版Dashboard_静默模式.bat 启动")
        print("2. 打开浏览器F12查看控制台")
        print("3. 确认Plotly警告消失")
        sys.exit(0)
    else:
        print("⚠️ 部分检查未通过，请查看上述详情")
        sys.exit(1)
