# 门店对比分析功能 - 实现任务列表

## 任务概述

本任务列表将门店对比分析功能的实现分解为可执行的编码任务。按照从基础架构到核心功能，再到优化测试的顺序，逐步完成功能开发。

**实现优先级**：
- 🔴 P0：基础架构和核心卡片（必须完成）
- 🟡 P1：差异分析和交互优化（重要）
- 🟢 P2：文档和部署（后续）

---

## 阶段1：基础架构

- [x] 1. 创建对比模式控制栏组件



  - 在dashboard_v2.py的"本店数据"TAB顶部添加控制栏
  - 添加对比模式Switch组件（id='comparison-mode-switch'）
  - 添加竞对选择器Dropdown组件（id='competitor-selector'）
  - 实现控制栏的固定定位（sticky positioning）
  - 使用dbc.Row和dbc.Col布局，确保响应式
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 1.1 实现对比模式开关回调


  - 创建回调函数：监听comparison-mode-switch的value变化
  - 当开关为ON时，启用competitor-selector并加载门店列表
  - 当开关为OFF时，禁用competitor-selector并清空选择
  - 更新Switch的label显示（OFF/ON）
  - _Requirements: 1.2, 1.3_

- [x] 1.2 实现竞对门店列表加载


  - 从StoreManager获取已上传的门店列表
  - 排除当前查看的门店
  - 格式化为Dropdown的options格式
  - 处理无可用门店的情况（显示提示）
  - _Requirements: 1.3_

- [x] 2. 创建对比数据加载器类


  - 在dashboard_v2.py中创建ComparisonDataLoader类
  - 实现__init__方法，初始化缓存字典
  - 实现load_competitor_data方法，加载竞对Excel数据
  - 实现缓存机制：检查缓存 → 命中返回 → 未命中加载
  - 实现clear_cache方法，支持清除指定门店或全部缓存
  - 添加日志记录（使用现有logger）
  - _Requirements: 6.1, 6.2, 6.5_

- [x] 2.1 实现竞对数据加载回调


  - 创建回调函数：监听competitor-selector的value变化
  - 调用ComparisonDataLoader.load_competitor_data加载数据
  - 提取关键数据：kpi、category、price、role
  - 存储到dcc.Store组件（id='competitor-data-cache'）
  - 处理加载失败的情况（显示错误提示）
  - _Requirements: 1.4, 6.1_

- [x] 2.2 添加对比状态管理Store组件


  - 添加dcc.Store(id='comparison-mode', data='off')
  - 添加dcc.Store(id='selected-competitor', data=None)
  - 添加dcc.Store(id='competitor-data-cache', data={})
  - 在对比模式开关回调中更新comparison-mode状态
  - 在竞对选择回调中更新selected-competitor状态
  - _Requirements: 1.4_

- [x] 3. 实现错误处理机制


  - 在load_competitor_data中添加try-except块
  - 处理报告文件不存在的情况（返回None，记录错误日志）
  - 处理Excel读取失败的情况（返回None，记录错误日志）
  - 处理数据格式不匹配的情况（记录警告日志，跳过不匹配字段）
  - 在回调中检查加载结果，失败时显示dbc.Alert错误提示
  - _Requirements: 6.3_

- [x] 4. 优化门店管理逻辑（新增）
  - 实现分目录管理：本店保存到`reports/本店/`，竞对保存到`reports/竞对门店/`
  - 修改StoreManager类，添加own_stores和competitor_stores字典
  - 实现auto_discover_stores()方法，启动时自动扫描门店
  - 修改上传回调，自动保存到对应目录
  - _Requirements: 门店管理优化_

- [x] 4.1 实现TAB切换门店逻辑（新增）
  - 修改update_store_switcher回调，监听main-tabs.active_tab
  - 本店数据看板TAB：门店切换显示本店列表
  - 竞对数据看板TAB：门店切换显示竞对列表
  - TAB切换时自动更新门店列表和选中门店
  - _Requirements: TAB切换优化_

- [x] 4.2 删除旧对比分析TAB（新增）
  - 删除"对比分析"TAB定义
  - 删除对比看板HTML区域和相关组件
  - 删除旧的对比数据Store组件
  - 删除旧的对比回调函数和render函数
  - 简化TAB切换逻辑
  - _Requirements: 代码重构_

- [x] 5. Checkpoint - 基础架构验证
  - 确保对比模式开关正常工作
  - 确保竞对选择器正常加载门店列表
  - 确保竞对数据能够成功加载和缓存
  - 确保错误处理正常工作
  - 确保TAB切换门店逻辑正常
  - 确保门店分目录管理正常
  - 如有问题，向用户报告

---

## 阶段2：核心卡片对比功能

### 2.1 核心指标概览对比

- [x] 6. 创建对比卡片组件
  - 在DashboardComponents类中创建create_kpi_comparison_cards静态方法
  - 接收参数：own_kpi（本店KPI字典）、competitor_kpi（竞对KPI字典）
  - 创建4个对比卡片：销售额、SKU数、动销率、毛利率
  - 每个卡片显示：本店数值、竞对数值、差异值、差异百分比
  - 实现视觉反馈：本店<竞对显示红色+向下箭头，本店>竞对显示绿色+向上箭头
  - 使用dbc.Card和dbc.Row布局，确保响应式
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [x] 6.1 编写Property测试 - 核心指标对比完整性





  - **Property 4: 核心指标对比完整性**
  - 生成随机的本店和竞对KPI数据
  - 调用create_kpi_comparison_cards生成对比卡片
  - 验证返回的组件包含4个卡片
  - 验证每个卡片包含本店数值、竞对数值、差异值、差异百分比
  - **Validates: Requirements 2.2, 2.3**

- [ ] 6.2 编写Property测试 - 指标差异视觉反馈规则
  - **Property 5: 指标差异视觉反馈规则**
  - 生成随机的本店和竞对KPI数据（确保有大于和小于的情况）
  - 调用create_kpi_comparison_cards生成对比卡片
  - 验证本店<竞对的卡片包含红色样式或向下箭头
  - 验证本店>竞对的卡片包含绿色样式或向上箭头
  - **Validates: Requirements 2.4, 2.5**

- [x] 7. 创建雷达图生成函数
  - 在ComparisonChartBuilder类中创建create_radar_chart静态方法
  - 接收参数：own_kpi、competitor_kpi、metrics（指标列表）
  - 归一化数据到0-100范围（相对于最大值）
  - 创建两条Scatterpolar trace：本店（蓝色）、竞对（红色）
  - 设置fill='toself'实现填充效果
  - 添加图例，设置合适的高度（400px）
  - _Requirements: 2.6_

- [ ] 7.1 编写Property测试 - 雷达图双曲线渲染
  - **Property 6: 雷达图双曲线渲染**
  - 生成随机的本店和竞对KPI数据
  - 调用create_radar_chart生成雷达图
  - 验证返回的figure包含2条trace
  - 验证两条trace的类型为Scatterpolar
  - 验证两条trace使用不同颜色
  - 验证图表包含图例
  - **Validates: Requirements 2.6**

- [x] 8. 实现核心指标对比视图回调
  - 修改现有的update_kpi_cards回调函数
  - 添加Input: comparison-mode、selected-competitor、competitor-data-cache
  - 检查对比模式状态：OFF时返回单店视图，ON时返回对比视图
  - 对比视图包含：对比卡片 + 雷达图 + 差异分析（暂时为空，后续实现）
  - 使用dbc.Row和dbc.Col布局，确保响应式
  - _Requirements: 2.1_

### 2.2 一级分类动销分析对比

- [-] 9. 创建分组柱状图生成函数

  - 在ComparisonChartBuilder类中创建create_grouped_bar_chart静态方法
  - 接收参数：own_data、competitor_data、x_col、y_col、title
  - 创建两条Bar trace：本店（蓝色）、竞对（红色）
  - 设置barmode='group'实现并排显示
  - 添加text和textposition='outside'显示数值
  - 添加图例，设置合适的高度（400px）
  - _Requirements: 3.2, 3.4_

- [ ] 9.1 编写Property测试 - 分组柱状图双系列渲染
  - **Property 8: 分组柱状图双系列渲染**
  - 生成随机的本店和竞对分类数据
  - 调用create_grouped_bar_chart生成分组柱状图
  - 验证返回的figure包含2条trace
  - 验证两条trace的类型为Bar
  - 验证barmode为'group'
  - 验证两条trace使用不同颜色
  - 验证图表包含图例
  - **Validates: Requirements 3.2, 3.4**

- [ ] 10. 创建镜像柱状图生成函数
  - 在ComparisonChartBuilder类中创建create_mirror_bar_chart静态方法
  - 接收参数：own_data、competitor_data、category_col、value_col、title
  - 创建两条Bar trace：本店（负值，蓝色）、竞对（正值，红色）
  - 设置orientation='h'实现横向显示
  - 设置barmode='overlay'实现重叠显示
  - 自定义x轴刻度：显示绝对值（如-30显示为30）
  - 添加图例，设置合适的高度（500px）
  - _Requirements: 3.3_

- [ ] 10.1 编写Property测试 - 镜像柱状图布局规则
  - **Property 9: 镜像柱状图布局规则**
  - 生成随机的本店和竞对分类数据
  - 调用create_mirror_bar_chart生成镜像柱状图
  - 验证本店trace的x值全部为负数
  - 验证竞对trace的x值全部为正数
  - 验证barmode为'overlay'
  - 验证orientation为'h'
  - **Validates: Requirements 3.3**

- [x] 11. 实现一级分类动销分析对比视图回调



  - 修改现有的update_category_analysis回调函数
  - 添加Input: comparison-mode、selected-competitor、competitor-data-cache
  - 检查对比模式状态：OFF时返回单店视图，ON时返回对比视图
  - 对比视图包含：
    - 动销率对比（分组柱状图）
    - SKU数量对比（镜像柱状图）
    - 销售额对比（分组柱状图）
  - 使用dbc.Row和dbc.Col布局，确保响应式
  - _Requirements: 3.1_

### 2.3 多规格商品供给分析对比

- [-] 12. 创建堆叠对比柱状图生成函数
  - 在ComparisonChartBuilder类中创建create_stacked_comparison_bar静态方法
  - 接收参数：own_data、competitor_data、title
  - 创建4条Bar trace：
    - 本店-单规格（蓝色）
    - 本店-多规格（浅蓝色）
    - 竞对-单规格（红色）
    - 竞对-多规格（浅红色）
  - 设置barmode='stack'实现堆叠显示
  - 设置orientation='h'实现横向显示
  - 添加text显示百分比，textposition='inside'
  - 添加图例，设置合适的高度（200px）
  - _Requirements: 4.3_
  - **状态**: 已存在，无需重新实现（第804-873行）

- [ ] 12.1 编写Property测试 - 堆叠图结构完整性
  - **Property 11: 堆叠图结构完整性**
  - 生成随机的本店和竞对多规格数据（包含单规格和多规格占比）
  - 调用create_stacked_comparison_bar生成堆叠图
  - 验证返回的figure包含4条trace
  - 验证barmode为'stack'
  - 验证每条trace包含百分比文本
  - 验证本店和竞对的单规格+多规格占比之和为100%
  - **Validates: Requirements 4.3**

- [x] 13. 实现多规格商品供给分析对比视图回调
  - 修改现有的update_multispec_supply回调函数
  - 添加Input: comparison-mode、selected-competitor、competitor-data-cache
  - 检查对比模式状态：OFF时返回单店视图，ON时返回对比视图
  - 对比视图包含：
    - 多规格SKU数量对比（镜像柱状图）
    - 多规格占比对比（堆叠对比柱状图）
  - 使用dbc.Row和dbc.Col布局，确保响应式
  - _Requirements: 4.1_
  - **完成时间**: 2025-12-14
  - **实现位置**: 
    - 回调函数: 第6083行（update_multispec_supply）
    - 辅助函数: 第1039行（create_multispec_comparison_view）

- [ ] 14. Checkpoint - 核心卡片对比功能验证
  - 确保核心指标概览对比正常显示
  - 确保一级分类动销分析对比正常显示
  - 确保多规格商品供给分析对比正常显示
  - 确保所有图表渲染正确
  - 如有问题，向用户报告

---

## 阶段3：差异分析引擎

- [x] 15. 创建差异分析生成器类





  - 在dashboard_v2.py中创建DifferenceAnalyzer类
  - 实现analyze_kpi_differences静态方法
    - 接收参数：own_kpi、competitor_kpi
    - 对比4个核心指标：销售额、SKU数、动销率、毛利率
    - 只有竞对>本店时才生成洞察
    - 计算差异值和差异百分比
    - 格式化洞察文本（如"竞对的销售额比本店高 ¥180,000（26.5%）"）
    - 返回洞察列表（最多3条）
  - _Requirements: 5.1, 5.2_

- [x] 15.1 编写Property测试 - 差异分析自动生成


  - **Property 7: 差异分析自动生成**
  - 生成随机的本店和竞对KPI数据（确保竞对某些指标>本店）
  - 调用analyze_kpi_differences生成差异分析
  - 验证返回的洞察列表不为空
  - 验证每条洞察包含"竞对"关键词
  - 验证每条洞察包含数值和百分比
  - **Validates: Requirements 5.1, 5.2**

- [x] 16. 实现分类差异分析方法




  - 在DifferenceAnalyzer类中实现analyze_category_differences静态方法
    - 接收参数：own_category、competitor_category
    - 转换为DataFrame并合并数据
    - 计算每个分类的差异值和差异百分比
    - 找出竞对领先的TOP3分类
    - 格式化洞察文本（如"竞对在'服饰鞋包'的SKU数是本店的2倍（20 vs 10）"）
    - 返回洞察列表（最多3条）
  - _Requirements: 5.1, 5.2_

- [x] 16.1 编写Property测试 - 分类级差异识别





  - **Property 10: 分类级差异识别**
  - 生成随机的本店和竞对分类数据（确保竞对某些分类>本店）
  - 调用analyze_category_differences生成差异分析
  - 验证返回的洞察列表不为空
  - 验证每条洞察包含分类名称
  - 验证每条洞察包含差异倍数或差异值
  - **Validates: Requirements 3.6**

- [x] 17. 实现改进建议生成方法





  - 在DifferenceAnalyzer类中实现generate_recommendations静态方法
    - 接收参数：insights（洞察列表）
    - 基于洞察内容生成改进建议
    - 规则：
      - 包含"SKU数"→建议增加商品数量
      - 包含"动销率"→建议优化滞销商品
      - 包含"销售额"→建议加大促销力度
    - 返回建议列表（最多2条）
  - _Requirements: 5.4_

- [x] 18. 实现洞察格式化和限制





  - 在DifferenceAnalyzer类中实现format_insight静态方法
    - 接收参数：metric_name、own_value、competitor_value、format_type
    - 根据format_type格式化数值（currency、percent、number）
    - 计算差异值和差异百分比
    - 返回格式化的洞察文本
  - 在analyze_kpi_differences和analyze_category_differences中应用格式化
  - 确保洞察数量不超过3条（使用[:3]切片）
  - _Requirements: 5.5, 5.6_

- [x] 18.1 编写Property测试 - 洞察数量限制


  - **Property 12: 差异洞察数量限制**
  - 生成随机的本店和竞对数据（确保能生成超过3条洞察）
  - 调用差异分析方法生成洞察
  - 验证返回的洞察列表长度不超过3
  - **Validates: Requirements 5.5**

- [x] 18.2 编写Property测试 - 洞察格式规范


  - **Property 13: 差异洞察格式规范**
  - 生成随机的本店和竞对数据
  - 调用差异分析方法生成洞察
  - 验证每条洞察符合格式规范（包含数值对比，如"20 vs 10"）
  - 验证每条洞察包含百分比或倍数
  - **Validates: Requirements 5.6**

- [x] 19. 集成差异分析到对比视图





  - 在核心指标概览对比视图中添加差异分析面板
  - 调用DifferenceAnalyzer.analyze_kpi_differences生成KPI洞察
  - 调用DifferenceAnalyzer.generate_recommendations生成改进建议
  - 使用DashboardComponents.create_insights_panel渲染洞察面板
  - 在一级分类动销分析对比视图中添加差异分析面板
  - 调用DifferenceAnalyzer.analyze_category_differences生成分类洞察
  - _Requirements: 2.7, 3.5_

- [x] 20. Checkpoint - 差异分析引擎验证





  - 确保KPI差异分析正常生成
  - 确保分类差异分析正常生成
  - 确保改进建议正常生成
  - 确保洞察格式正确且数量不超过3条
  - 如有问题，向用户报告

---

## 阶段4：交互优化和测试

- [ ] 21. 优化视图切换体验
  - 在对比模式开关回调中添加平滑过渡效果
  - 使用CSS transition实现淡入淡出效果
  - 在视图切换时保存当前滚动位置
  - 在视图切换完成后恢复滚动位置
  - _Requirements: 8.1, 8.2_

- [ ] 21.1 编写Property测试 - 滚动位置保持
  - **Property 16: 滚动位置保持**
  - 模拟页面滚动到特定位置
  - 触发对比模式切换
  - 验证切换后滚动位置保持不变
  - **Validates: Requirements 8.2**

- [ ] 22. 实现增量更新机制
  - 在竞对选择回调中添加防抖逻辑
  - 检查新选择的竞对是否与当前相同，相同则跳过更新
  - 在卡片回调中添加条件判断，只更新需要更新的部分
  - 使用dash.no_update避免不必要的重新渲染
  - _Requirements: 8.3_

- [ ] 22.1 编写Property测试 - 增量更新机制
  - **Property 17: 增量更新机制**
  - 模拟竞对切换操作
  - 记录渲染次数
  - 验证只有必要的组件被重新渲染
  - **Validates: Requirements 8.3**

- [ ] 23. 实现加载状态反馈
  - 创建加载动画组件（使用dbc.Spinner）
  - 在竞对数据加载回调中添加加载状态
  - 使用dcc.Loading包裹对比视图
  - 实现加载超时检测（2秒）
  - 超时时显示进度提示
  - _Requirements: 6.4, 8.4_

- [ ] 24. 实现固定控制栏定位
  - 为对比模式控制栏添加CSS样式
  - 设置position: sticky和top: 0
  - 设置z-index确保在最上层
  - 添加背景色和阴影效果
  - 测试滚动时控制栏是否保持固定
  - _Requirements: 8.5_

- [ ] 24.1 编写Property测试 - 固定控制栏定位
  - **Property 18: 固定控制栏定位**
  - 模拟页面滚动操作
  - 验证控制栏的position样式为sticky或fixed
  - 验证控制栏始终在视口顶部
  - **Validates: Requirements 8.5**

- [ ] 25. 编写集成测试
  - 创建test_comparison_integration.py文件
  - 测试完整对比流程：
    1. 开启对比模式
    2. 选择竞对门店
    3. 加载竞对数据
    4. 渲染对比视图
    5. 生成差异分析
    6. 关闭对比模式
  - 验证每个步骤的输出正确
  - _Requirements: All_

- [ ] 26. 性能优化
  - 使用cProfile分析性能瓶颈
  - 优化数据加载性能（目标<2秒）
  - 优化图表渲染性能（目标<0.5秒）
  - 优化缓存命中率（目标>90%）
  - 记录性能指标到日志
  - _Requirements: All_

- [ ] 27. Checkpoint - 最终验证
  - 确保所有Property测试通过
  - 确保所有集成测试通过
  - 确保性能测试通过
  - 确保交互体验流畅
  - 如有问题，向用户报告

---

## 阶段5：文档和部署

- [ ] 28. 编写用户文档
  - 创建门店对比分析功能使用指南
  - 包含功能介绍、操作步骤、注意事项
  - 添加截图和示例
  - 更新README.md

- [ ] 29. 代码审查和优化
  - 代码审查：检查代码质量、命名规范、注释完整性
  - 代码优化：移除冗余代码、优化算法、提升可读性
  - 安全检查：检查输入验证、错误处理、日志脱敏

- [ ] 30. 部署和验收
  - 部署到生产环境
  - 用户验收测试
  - 收集用户反馈
  - 修复发现的问题

---

## 任务统计

- **总任务数**: 30个主任务（新增3个优化任务）
- **已完成任务**: 11个（阶段1全部完成 + 阶段2部分完成）
- **Property测试任务**: 13个（全部必做）
- **Checkpoint任务**: 4个
- **预计剩余工时**: 5.5周

## 注意事项

1. **任务执行顺序**: 必须按照阶段顺序执行，不可跳过
2. **Checkpoint任务**: 遇到Checkpoint任务时，必须确保前面的任务全部完成且测试通过
3. **Property测试**: 所有Property测试任务都是必做的，确保代码质量
4. **错误处理**: 每个任务都应包含适当的错误处理和日志记录
5. **代码风格**: 遵循现有代码的风格和命名规范
6. **测试优先**: 在实现功能前，先思考如何测试该功能
