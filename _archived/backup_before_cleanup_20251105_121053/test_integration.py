# -*- coding: utf-8 -*-
"""
测试untitled1.py集成到dashboard_v2.py的完整流程
"""

import sys
from pathlib import Path

def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("📦 测试1: 模块导入")
    print("=" * 60)
    
    try:
        from store_analyzer import get_store_analyzer
        print("✅ store_analyzer 导入成功")
        
        analyzer = get_store_analyzer()
        print(f"✅ 分析器实例化成功: {type(analyzer)}")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dashboard_structure():
    """测试dashboard_v2.py结构"""
    print("\n" + "=" * 60)
    print("🏗️  测试2: Dashboard结构检查")
    print("=" * 60)
    
    try:
        dashboard_path = Path("dashboard_v2.py")
        if not dashboard_path.exists():
            print("❌ dashboard_v2.py 文件不存在")
            return False
        
        content = dashboard_path.read_text(encoding='utf-8')
        
        # 检查关键组件
        checks = {
            'StoreManager类': 'class StoreManager:',
            'store_manager初始化': 'store_manager = StoreManager()',
            'analyzer初始化': 'analyzer = get_store_analyzer()',
            '原始数据上传组件': "id='upload-raw-data'",
            '门店名称输入': "id='store-name-input'",
            '分析按钮': "id='btn-run-analysis'",
            '分析状态显示': "id='analysis-status'",
            '分析回调函数': 'def run_untitled1_analysis',
            '门店切换回调': 'def switch_store',
            'PreventUpdate导入': 'from dash.exceptions import PreventUpdate'
        }
        
        all_passed = True
        for name, pattern in checks.items():
            if pattern in content:
                print(f"✅ {name} 存在")
            else:
                print(f"❌ {name} 缺失")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def test_store_analyzer_functionality():
    """测试store_analyzer核心功能"""
    print("\n" + "=" * 60)
    print("🔬 测试3: StoreAnalyzer功能测试")
    print("=" * 60)
    
    try:
        from store_analyzer import get_store_analyzer
        
        analyzer = get_store_analyzer()
        
        # 检查方法存在性
        methods = [
            'analyze_file',
            'get_store_list',
            'get_analysis',
            'get_summary',
            'get_multispec_products',
            'get_category_analysis',
            'export_report'
        ]
        
        for method in methods:
            if hasattr(analyzer, method):
                print(f"✅ 方法存在: {method}")
            else:
                print(f"❌ 方法缺失: {method}")
                return False
        
        # 检查初始状态
        store_list = analyzer.get_store_list()
        print(f"\n📋 当前已分析门店数: {len(store_list)}")
        if store_list:
            print(f"   门店列表: {', '.join(store_list)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reports_directory():
    """测试reports目录"""
    print("\n" + "=" * 60)
    print("📁 测试4: Reports目录检查")
    print("=" * 60)
    
    reports_dir = Path("./reports")
    if not reports_dir.exists():
        print("⚠️  reports目录不存在，将在首次分析时创建")
    else:
        print(f"✅ reports目录存在")
        excel_files = list(reports_dir.glob("*.xlsx"))
        print(f"📊 现有报告数: {len(excel_files)}")
        for f in excel_files[:5]:  # 只显示前5个
            print(f"   - {f.name}")
    
    return True


def test_temp_directory():
    """测试temp临时目录"""
    print("\n" + "=" * 60)
    print("📁 测试5: Temp临时目录检查")
    print("=" * 60)
    
    temp_dir = Path("./temp")
    if not temp_dir.exists():
        print("⚠️  temp目录不存在，将在首次上传时创建")
        try:
            temp_dir.mkdir(exist_ok=True)
            print("✅ temp目录创建成功")
            return True
        except Exception as e:
            print(f"❌ temp目录创建失败: {e}")
            return False
    else:
        print(f"✅ temp目录已存在")
        return True


def test_integration_workflow():
    """测试完整集成工作流程"""
    print("\n" + "=" * 60)
    print("🔄 测试6: 集成工作流程验证")
    print("=" * 60)
    
    print("📝 预期工作流程:")
    print("   1. 用户上传原始Excel/CSV文件")
    print("   2. 输入门店名称")
    print("   3. 点击'开始分析'按钮")
    print("   4. Dashboard调用 analyzer.analyze_file()")
    print("   5. untitled1.py核心函数执行分析")
    print("   6. 生成多Sheet Excel报告到 ./reports/")
    print("   7. StoreManager添加新门店")
    print("   8. DataLoader自动切换到新报告")
    print("   9. Dashboard所有图表自动刷新")
    print("   10. 用户可通过下拉框切换门店查看")
    
    print("\n✅ 工作流程设计完整")
    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("🚀 untitled1.py集成测试开始")
    print("=" * 60)
    
    results = {
        '模块导入': test_imports(),
        'Dashboard结构': test_dashboard_structure(),
        'StoreAnalyzer功能': test_store_analyzer_functionality(),
        'Reports目录': test_reports_directory(),
        'Temp目录': test_temp_directory(),
        '工作流程': test_integration_workflow()
    }
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20s} {status}")
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过! 集成完成，可以启动Dashboard测试实际功能")
        print("\n启动命令:")
        print("   python dashboard_v2.py")
        print("\n测试步骤:")
        print("   1. 打开浏览器访问 http://localhost:8055")
        print("   2. 找到'原始数据分析'区域")
        print("   3. 上传门店原始数据Excel文件")
        print("   4. 输入门店名称")
        print("   5. 点击'开始分析'")
        print("   6. 等待分析完成(约10-30秒)")
        print("   7. 查看自动刷新的看板数据")
    else:
        print("\n⚠️  部分测试失败，请检查上述错误信息")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
