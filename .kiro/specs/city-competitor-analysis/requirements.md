# Requirements Document

## Introduction

本功能为看板新增一个"城市新增竞对分析"TAB页面，用于分析各城市5km范围内的新增竞对情况。数据来源于"城市新增竞对数据/新增竞对.xlsx"文件，包含门店基础信息、竞对数量统计、新增竞对详情（品牌、SKU数、商补率、品牌特性）等字段。该功能帮助运营人员快速了解各城市竞争态势变化，识别重点关注区域和竞对品牌。

## Glossary

- **Dashboard**: 基于Streamlit的数据分析看板系统
- **竞对**: 竞争对手门店
- **新增竞对**: 近15天内在5km范围内新开业的竞争对手门店
- **商补率**: 商家补贴率，表示竞对的补贴力度区间
- **品牌特性**: 对竞对营销策略和运营特点的文字描述
- **区域类型**: 门店所在位置分类，分为"市区"和"县城"两种
- **商圈类型**: 门店所在商圈的竞争强度，分为"强"、"中"、"弱"三种

## Requirements

### Requirement 1

**User Story:** As a 运营人员, I want to 上传并解析城市新增竞对数据文件, so that 系统能够读取和处理竞对分析所需的原始数据。

#### Acceptance Criteria

1. WHEN 用户上传Excel文件 THEN Dashboard SHALL 解析文件并识别所有必需字段（门店名称、城市、运营、商圈类型、5km内竞对数量、近15天5km内新增竞对数量、新增竞对N、品牌特性、sku数、商补率）
2. WHEN 文件包含多个新增竞对列（新增竞对1、新增竞对2等） THEN Dashboard SHALL 动态识别并解析所有竞对及其对应属性列
3. WHEN 文件格式不符合预期 THEN Dashboard SHALL 显示明确的错误提示信息
4. WHEN 数据解析完成 THEN Dashboard SHALL 将宽表格式的竞对数据转换为长表格式以便分析

### Requirement 2

**User Story:** As a 运营人员, I want to 查看城市维度的竞对汇总统计, so that 我能快速了解各城市的竞争态势。

#### Acceptance Criteria

1. WHEN 数据加载完成 THEN Dashboard SHALL 显示各城市的门店数量、5km内竞对总数、近15天新增竞对总数
2. WHEN 展示城市统计 THEN Dashboard SHALL 计算并显示各城市新增竞对数量占全部新增竞对的百分比
3. WHEN 用户查看城市汇总 THEN Dashboard SHALL 按新增竞对数量降序排列城市列表
4. WHEN 展示城市数据 THEN Dashboard SHALL 提供可视化图表（柱状图或饼图）展示城市分布

### Requirement 3

**User Story:** As a 运营人员, I want to 查看新增竞对品牌排行, so that 我能识别哪些竞对品牌扩张最积极。

#### Acceptance Criteria

1. WHEN 数据加载完成 THEN Dashboard SHALL 统计各新增竞对品牌的出现次数
2. WHEN 展示品牌排行 THEN Dashboard SHALL 按出现次数降序显示TOP10品牌列表
3. WHEN 展示品牌数据 THEN Dashboard SHALL 提供柱状图可视化品牌分布
4. WHEN 用户点击某品牌 THEN Dashboard SHALL 显示该品牌在各城市的分布详情

### Requirement 4

**User Story:** As a 运营人员, I want to 分析商圈类型与竞对的关系, so that 我能了解不同商圈强度下的竞争情况。

#### Acceptance Criteria

1. WHEN 数据加载完成 THEN Dashboard SHALL 按商圈类型（强/中/弱）分组统计竞对数量
2. WHEN 展示商圈分析 THEN Dashboard SHALL 显示各商圈类型的平均竞对数量和新增竞对数量
3. WHEN 展示商圈数据 THEN Dashboard SHALL 提供分组柱状图对比不同商圈类型的竞争强度

### Requirement 5

**User Story:** As a 运营人员, I want to 查看竞对详情表, so that 我能了解每个新增竞对的具体信息。

#### Acceptance Criteria

1. WHEN 数据加载完成 THEN Dashboard SHALL 显示包含门店名称、城市、新增竞对名称、品牌特性、SKU数、商补率的详情表
2. WHEN 展示详情表 THEN Dashboard SHALL 支持按城市、商圈类型、竞对品牌进行筛选
3. WHEN 展示详情表 THEN Dashboard SHALL 支持按SKU数、商补率进行排序
4. WHEN 品牌特性字段有值 THEN Dashboard SHALL 完整显示品牌特性描述文本

### Requirement 6

**User Story:** As a 运营人员, I want to 区分市区和县城的竞对分布, so that 我能针对不同区域类型制定差异化策略。

#### Acceptance Criteria

1. WHEN 数据加载完成 THEN Dashboard SHALL 基于门店名称和行政区划数据自动识别区域类型（市区/县城）
2. WHEN 识别区域类型 THEN Dashboard SHALL 使用预定义的县级行政区划名单和市区区名列表进行匹配
3. WHEN 无法通过名单匹配 THEN Dashboard SHALL 使用关键词规则（县、镇、乡=县城；区、路、街、广场=市区）进行识别
4. WHEN 展示区域分析 THEN Dashboard SHALL 显示市区和县城的竞对数量对比
5. WHEN 展示区域分析 THEN Dashboard SHALL 提供按区域类型筛选的功能

### Requirement 7

**User Story:** As a 运营人员, I want to 获取竞对品牌特性洞察, so that 我能了解竞对的营销策略特点。

#### Acceptance Criteria

1. WHEN 数据包含品牌特性描述 THEN Dashboard SHALL 汇总展示所有品牌特性标签
2. WHEN 展示品牌特性 THEN Dashboard SHALL 提取关键词并统计出现频次
3. WHEN 展示品牌洞察 THEN Dashboard SHALL 以词云或标签云形式可视化品牌特性关键词
