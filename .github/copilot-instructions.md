# O2O门店数据分析项目 Copilot 指南

## 架构与核心流程

- **主分析引擎**：`untitled1.py`，负责数据加载、清洗、分析与报告生成。
- **数据流**：原始 Excel/CSV → 列名映射/校验 → 多规格识别 → 分类统计 → 多Sheet Excel 报告（输出至 `reports/`）。
- **关键算法**：多规格商品识别（基于商品名、规格、条码三重信号，详见 `identify_multi_spec_products` 及 `_normalize_base_name`）。
- **商品角色分类**：通过价格带与销量规则自动分配（见 `assign_product_role`）。
- **报告结构**：多Sheet，含核心指标、角色分析、价格带、分类明细、多规格SKU、数据一致性校验等。

## 主要开发工作流

- **环境配置**：使用虚拟环境，推荐命令：
    ```powershell
    cd "D:\Python1\O2O_Analysis\O2O数据分析"
    .\.venv\Scripts\python.exe 门店基础数据分析\untitled1.py
    ```
- **数据输入**：支持`.csv`/`.xlsx`，需包含商品名、售价、销量、分类、原价、库存等列（中英文均可，自动映射）。
- **配置变量**：在 `untitled1.py` 顶部可调整门店列表、输出文件名、消费场景关键词等。
- **输出**：所有分析报告自动存储于 `reports/` 目录。

## 项目约定与特色

- **列名映射**：`potential_col_names` 字典支持多变体，遇新列名需补充。
- **多规格识别**：正则与分组结合，详见 `_extract_inferred_spec`。
- **数据一致性**：多级排序去重（销量降序→价格升序→库存降序→规格升序），多规格SKU统计与主表严格一致。
- **异常处理**：自动检测 Excel 锁文件（`~$`），被占用时自动生成带时间戳备份，xlsxwriter→openpyxl 自动降级。
- **性能优化**：pandas 向量化、分块处理大数据集。

## 扩展与调试建议

- **新增分析维度**：在 `analyze_store_performance` 中按现有 groupby 模式扩展。
- **输出格式扩展**：在 `export_full_report_to_excel` 的 `get_sheet_pct_cols` 白名单中添加新百分比列。
- **常见调试点**：列名映射失败、多规格识别异常、销售额统计不一致。

## 关键文件/目录

- `untitled1.py`：主逻辑与所有核心函数
- `reports/`：所有输出报告
- `requirements_dashboard.txt`：依赖包列表

如需扩展功能或修复异常，优先参考上述文件与函数结构。