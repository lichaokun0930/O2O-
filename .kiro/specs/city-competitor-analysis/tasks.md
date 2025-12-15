# Implementation Plan

## 1. 创建数据处理模块

- [x] 1.1 创建CompetitorDataLoader数据加载器
  - 在modules/data/目录下创建competitor_loader.py
  - 实现load_data()方法加载Excel文件
  - 实现validate_columns()方法验证必需列
  - 处理文件不存在和格式错误的异常
  - _Requirements: 1.1, 1.3_

- [x] 1.2 创建CompetitorDataParser数据解析器
  - 实现detect_competitor_columns()动态检测竞对列
  - 实现parse_wide_to_long()宽表转长表
  - 处理多个新增竞对列（新增竞对1、新增竞对2等）
  - 正确映射每个竞对的品牌特性、sku数、商补率
  - _Requirements: 1.2, 1.4_

- [x] 1.3 编写属性测试：数据解析完整性
  - **Property 1: 数据解析完整性**
  - **Validates: Requirements 1.1, 1.2, 1.4**
  - 使用hypothesis生成包含不同数量竞对列的测试数据
  - 验证长表记录数等于原始非空竞对数
  - 验证属性字段值与原始数据一致

## 2. 创建区域分类模块

- [x] 2.1 创建RegionClassifier区域分类器
  - 在modules/utils/目录下创建region_classifier.py
  - 定义江苏安徽县级行政区划名单（COUNTY_LIST）
  - 定义市区区名列表（DISTRICT_LIST）
  - 实现classify()方法：名单匹配→关键词规则
  - 实现classify_batch()批量分类方法
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2.2 编写属性测试：区域类型识别一致性
  - **Property 6: 区域类型识别一致性**
  - **Validates: Requirements 6.1, 6.2, 6.3**
  - 验证县级名单优先于关键词规则
  - 验证市区名单优先于关键词规则
  - 验证未匹配时返回"未知"

## 3. 创建统计分析模块

- [x] 3.1 创建CompetitorAnalyzer分析器基础结构
  - 在modules/data/目录下创建competitor_analyzer.py
  - 实现__init__()接收长表格式数据
  - 实现get_city_summary()城市维度汇总
  - 计算门店数、竞对总数、新增竞对数、占比
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3.2 编写属性测试：城市统计正确性
  - **Property 2: 城市统计正确性**
  - **Validates: Requirements 2.1, 2.2, 2.3**
  - 验证各城市新增竞对数之和等于总数
  - 验证占比之和约等于100%

- [x] 3.3 实现品牌排行分析
  - 实现get_brand_ranking()方法
  - 统计各品牌出现次数
  - 按出现次数降序排列
  - 支持TOP N参数
  - _Requirements: 3.1, 3.2_

- [x] 3.4 编写属性测试：品牌排行正确性
  - **Property 3: 品牌排行正确性**
  - **Validates: Requirements 3.1, 3.2**
  - 验证排行严格降序
  - 验证计数与实际出现次数一致

- [x] 3.5 实现商圈类型分析
  - 实现get_business_circle_analysis()方法
  - 按商圈类型（强/中/弱）分组
  - 计算各组平均竞对数和新增竞对数
  - _Requirements: 4.1, 4.2_

- [x] 3.6 编写属性测试：商圈分组统计正确性
  - **Property 4: 商圈分组统计正确性**
  - **Validates: Requirements 4.1, 4.2**
  - 验证平均值计算正确

- [x] 3.7 实现区域类型分析
  - 实现get_region_analysis()方法
  - 按区域类型（市区/县城/未知）分组统计
  - _Requirements: 6.4_

- [x] 3.8 实现竞对详情查询
  - 实现get_competitor_details()方法
  - 支持多条件筛选（城市、商圈、区域、品牌）
  - 支持按SKU数、商补率排序
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 3.9 编写属性测试：详情表筛选正确性
  - **Property 5: 详情表筛选正确性**
  - **Validates: Requirements 5.2, 5.3, 6.5**
  - 验证筛选结果满足所有条件
  - 验证无遗漏

- [x] 3.10 实现品牌特性关键词提取
  - 实现extract_brand_keywords()方法
  - 使用jieba分词提取关键词
  - 统计关键词频次
  - _Requirements: 7.1, 7.2_

- [x] 3.11 编写属性测试：关键词提取完整性
  - **Property 7: 关键词提取完整性**
  - **Validates: Requirements 7.1, 7.2**
  - 验证关键词频次之和≥非空记录数

## 4. Checkpoint - 确保所有测试通过
- [x] 4.1 运行所有测试，确认数据处理和分析逻辑正确
  - Ensure all tests pass, ask the user if questions arise.

## 5. 创建UI组件

- [x] 5.1 创建城市新增竞对分析TAB页面框架
  - 在dashboard_v2.py中添加新TAB
  - 创建页面整体布局（筛选器+图表+表格）
  - 添加数据上传/加载逻辑
  - _Requirements: 1.1_

- [x] 5.2 创建筛选器面板
  - 城市下拉选择器
  - 商圈类型多选框
  - 区域类型多选框
  - 品牌搜索框
  - _Requirements: 5.2, 6.5_

- [x] 5.3 创建城市汇总图表
  - 柱状图展示各城市新增竞对数量
  - 饼图展示城市占比分布
  - 支持按新增竞对数排序
  - _Requirements: 2.4_

- [x] 5.4 创建品牌排行图表
  - 水平柱状图展示TOP10品牌
  - 显示品牌名称和出现次数
  - _Requirements: 3.3_

- [x] 5.5 创建商圈分析图表
  - 分组柱状图对比强/中/弱商圈
  - 展示平均竞对数和新增竞对数
  - _Requirements: 4.3_

- [x] 5.6 创建区域对比图表
  - 对比市区和县城的竞对分布
  - 使用双柱状图或饼图
  - _Requirements: 6.4_

- [x] 5.7 创建品牌特性词云
  - 使用wordcloud或echarts词云组件
  - 展示高频关键词
  - _Requirements: 7.3_

- [x] 5.8 创建竞对详情表
  - 使用dash_table展示详情数据
  - 支持分页和排序
  - 完整显示品牌特性文本
  - _Requirements: 5.1, 5.4_

## 6. 实现交互回调

- [x] 6.1 实现筛选器回调
  - 筛选条件变化时更新所有图表和表格
  - 支持多条件组合筛选
  - _Requirements: 5.2, 6.5_

- [x] 6.2 实现品牌点击交互
  - 点击品牌排行中的品牌时显示城市分布详情
  - _Requirements: 3.4_

- [x] 6.3 实现表格排序回调
  - 支持按SKU数、商补率列排序
  - _Requirements: 5.3_

## 7. Final Checkpoint - 确保所有测试通过
- [x] 7.1 运行所有测试，确认功能完整
  - Ensure all tests pass, ask the user if questions arise.
