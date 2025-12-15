# 门店对比分析功能需求文档

## 简介

本文档定义了O2O门店数据分析看板的"门店对比分析"功能需求。该功能允许用户在单店看板中，通过"门店PK"模式，直观对比本店与竞对门店在各个维度的表现差异，帮助用户快速识别优劣势，制定经营策略。

## 术语表

- **Dashboard**: O2O门店数据分析看板系统
- **本店**: 用户当前查看的门店数据
- **竞对**: 用户选择用于对比的竞争对手门店数据
- **对比模式**: 用户开启后，卡片内容从单店视图切换为对比视图的交互模式
- **卡片**: 看板中的独立分析模块，如"核心指标概览"、"一级分类动销分析"等
- **差异分析**: 系统自动生成的对比洞察，指出本店与竞对的关键差异和建议
- **镜像柱状图**: 左右对称的柱状图，用于直观对比两个门店的数值差异
- **分组柱状图**: 将本店和竞对的数据并排显示的柱状图
- **堆叠对比柱状图**: 展示结构占比的横向柱状图，用于对比组成部分

## 需求

### 需求 1: 全局对比模式开关

**用户故事**: 作为门店运营人员，我想要在看板顶部开启"对比模式"，以便快速切换到门店对比视图。

#### 验收标准

1. WHEN 用户访问"本店数据"TAB THEN Dashboard SHALL 在页面顶部显示"对比模式"开关和"选择竞对"下拉框
2. WHEN 对比模式为OFF状态 THEN Dashboard SHALL 显示单店数据视图，且"选择竞对"下拉框为禁用状态
3. WHEN 用户开启对比模式 THEN Dashboard SHALL 启用"选择竞对"下拉框，并提示用户选择竞对门店
4. WHEN 用户选择竞对门店后 THEN Dashboard SHALL 加载竞对数据，并将所有支持对比的卡片切换为对比视图
5. WHEN 用户关闭对比模式 THEN Dashboard SHALL 将所有卡片恢复为单店视图

### 需求 2: 核心指标概览对比

**用户故事**: 作为门店运营人员，我想要对比本店与竞对的核心KPI指标，以便快速了解整体经营差距。

#### 验收标准

1. WHEN 对比模式开启且竞对已选择 THEN Dashboard SHALL 在"核心指标概览"卡片中显示对比视图
2. WHEN 显示对比视图 THEN Dashboard SHALL 展示对比卡片，包含销售额、SKU数、动销率、毛利率四个核心指标
3. WHEN 显示对比卡片 THEN Dashboard SHALL 为每个指标显示本店数值、竞对数值、差异值和差异百分比
4. WHEN 本店指标低于竞对 THEN Dashboard SHALL 使用红色或向下箭头标识，表示落后
5. WHEN 本店指标高于竞对 THEN Dashboard SHALL 使用绿色或向上箭头标识，表示领先
6. WHEN 显示对比视图 THEN Dashboard SHALL 展示综合能力雷达图，同时显示本店和竞对的数据曲线
7. WHEN 显示对比视图 THEN Dashboard SHALL 生成差异分析洞察，指出关键差异和改进建议

### 需求 3: 一级分类动销分析对比

**用户故事**: 作为门店运营人员，我想要对比本店与竞对在各个一级分类的表现，以便识别优势分类和劣势分类。

#### 验收标准

1. WHEN 对比模式开启且竞对已选择 THEN Dashboard SHALL 在"一级分类动销分析"卡片中显示对比视图
2. WHEN 显示对比视图 THEN Dashboard SHALL 展示动销率对比的分组柱状图，本店和竞对的柱子并排显示
3. WHEN 显示对比视图 THEN Dashboard SHALL 展示SKU数量对比的镜像柱状图，本店在左侧，竞对在右侧
4. WHEN 显示对比视图 THEN Dashboard SHALL 展示销售额对比的分组柱状图，本店和竞对的柱子并排显示
5. WHEN 显示对比视图 THEN Dashboard SHALL 生成差异分析洞察，指出哪些分类本店领先、哪些分类竞对领先
6. WHEN 竞对某分类的指标高于本店 THEN Dashboard SHALL 在差异分析中提示该分类的差距和改进建议
7. WHEN 本店某分类的指标高于竞对 THEN Dashboard SHALL 在差异分析中提示该分类的优势

### 需求 4: 多规格商品供给分析对比

**用户故事**: 作为门店运营人员，我想要对比本店与竞对的多规格商品供给情况，以便优化商品结构。

#### 验收标准

1. WHEN 对比模式开启且竞对已选择 THEN Dashboard SHALL 在"多规格商品供给分析"卡片中显示对比视图
2. WHEN 显示对比视图 THEN Dashboard SHALL 展示多规格SKU数量对比的镜像柱状图，本店在左侧，竞对在右侧
3. WHEN 显示对比视图 THEN Dashboard SHALL 展示多规格占比对比的堆叠对比柱状图，显示单规格和多规格的占比
4. WHEN 显示对比视图 THEN Dashboard SHALL 生成差异分析洞察，指出多规格商品的结构性差异
5. WHEN 竞对的多规格占比高于本店 THEN Dashboard SHALL 在差异分析中提示增加多规格商品的建议
6. WHEN 本店某分类的多规格SKU数高于竞对 THEN Dashboard SHALL 在差异分析中提示该分类的优势

### 需求 5: 差异分析自动生成

**用户故事**: 作为门店运营人员，我想要系统自动生成差异分析洞察，以便快速了解关键差异和改进方向。

#### 验收标准

1. WHEN 对比视图显示时 THEN Dashboard SHALL 自动分析本店与竞对的数据差异
2. WHEN 竞对某指标的数值高于本店 THEN Dashboard SHALL 生成"竞对领先"的洞察，包含具体数值和百分比
3. WHEN 本店某指标的数值高于竞对 THEN Dashboard SHALL 生成"本店领先"的洞察，包含具体数值和百分比
4. WHEN 生成差异洞察 THEN Dashboard SHALL 提供改进建议，如"建议增加XX分类商品"
5. WHEN 差异洞察超过3条 THEN Dashboard SHALL 只显示最重要的3条洞察
6. WHEN 差异洞察包含数值 THEN Dashboard SHALL 使用易读的格式，如"竞对的SKU数是本店的2倍（20 vs 10）"

### 需求 6: 竞对数据加载与缓存

**用户故事**: 作为门店运营人员，我想要系统快速加载竞对数据，以便流畅地进行对比分析。

#### 验收标准

1. WHEN 用户选择竞对门店 THEN Dashboard SHALL 从已上传的门店数据中加载竞对报告
2. WHEN 竞对数据加载成功 THEN Dashboard SHALL 缓存竞对数据，避免重复加载
3. WHEN 竞对数据加载失败 THEN Dashboard SHALL 显示错误提示，并保持单店视图
4. WHEN 竞对数据正在加载 THEN Dashboard SHALL 显示加载动画，提示用户等待
5. WHEN 用户切换竞对门店 THEN Dashboard SHALL 清除旧的竞对数据缓存，加载新的竞对数据

### 需求 7: 对比视图的图表渲染

**用户故事**: 作为门店运营人员，我想要对比视图的图表清晰美观，以便快速理解数据差异。

#### 验收标准

1. WHEN 渲染分组柱状图 THEN Dashboard SHALL 使用不同颜色区分本店和竞对，并添加图例
2. WHEN 渲染镜像柱状图 THEN Dashboard SHALL 将本店数据显示在左侧，竞对数据显示在右侧，中间为0刻度线
3. WHEN 渲染堆叠对比柱状图 THEN Dashboard SHALL 使用不同颜色区分不同组成部分，并显示百分比
4. WHEN 渲染雷达图 THEN Dashboard SHALL 使用不同颜色和线型区分本店和竞对，并添加图例
5. WHEN 图表数据为空 THEN Dashboard SHALL 显示"暂无数据"提示，而不是空白图表
6. WHEN 图表渲染失败 THEN Dashboard SHALL 显示错误提示，并记录错误日志

### 需求 8: 对比模式的交互体验

**用户故事**: 作为门店运营人员，我想要对比模式的交互流畅自然，以便高效完成对比分析。

#### 验收标准

1. WHEN 用户开启对比模式 THEN Dashboard SHALL 平滑过渡到对比视图，避免页面闪烁
2. WHEN 用户关闭对比模式 THEN Dashboard SHALL 平滑过渡回单店视图，保持页面滚动位置
3. WHEN 用户切换竞对门店 THEN Dashboard SHALL 只更新对比数据，不重新渲染整个页面
4. WHEN 对比视图加载时间超过2秒 THEN Dashboard SHALL 显示进度提示
5. WHEN 用户在对比模式下滚动页面 THEN Dashboard SHALL 保持"对比模式"开关和"选择竞对"下拉框固定在顶部
