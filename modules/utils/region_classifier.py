# -*- coding: utf-8 -*-
"""
区域分类器
根据门店名称智能识别区域类型（市区/县城）
支持：行政区划名单 + cpca解析 + 关键词规则 + 默认县城
"""

import pandas as pd
import logging

logger = logging.getLogger('dashboard')

# 尝试导入cpca
try:
    import cpca
    CPCA_AVAILABLE = True
    logger.info("✅ cpca库已加载")
except ImportError:
    CPCA_AVAILABLE = False
    logger.warning("⚠️ cpca库未安装，将使用简化的区域识别")


class RegionClassifier:
    """区域分类器 - 识别门店所在区域类型
    
    四层识别机制：
    1. 行政区划名单匹配（优先级最高）
    2. cpca地址解析
    3. 关键词规则
    4. 默认归为县城（兜底）
    """
    
    # 江苏安徽县级行政区划名单（县/县级市）
    COUNTY_LIST = [
        # 江苏县级市/县
        '句容', '丹阳', '扬中', '沛县', '丰县', '睢宁', '新沂', '邳州',
        '溧阳', '金坛', '如皋', '海门', '启东', '如东', '海安', '东台',
        '大丰', '射阳', '建湖', '阜宁', '滨海', '响水', '沭阳', '泗阳',
        '泗洪', '宝应', '高邮', '仪征', '靖江', '泰兴', '兴化',
        # 安徽县级市/县
        '肥东', '肥西', '长丰', '庐江', '巢湖', '无为', '含山', '和县',
        '当涂', '繁昌', '南陵', '芜湖县', '怀远', '五河', '固镇',
        '濉溪', '蒙城', '涡阳', '利辛', '砀山', '萧县', '灵璧', '泗县',
        '天长', '明光', '来安', '全椒', '定远', '凤阳', '凤台', '寿县',
        '霍邱', '舒城', '金寨', '霍山', '桐城', '怀宁', '太湖', '宿松',
        '望江', '岳西', '潜山', '广德', '宁国', '郎溪', '绩溪', '旌德', '泾县'
    ]
    
    # 市区区名列表
    DISTRICT_LIST = [
        # 南京
        '江宁', '建邺', '鼓楼', '玄武', '秦淮', '栖霞', '雨花', '浦口', '六合', '溧水', '高淳',
        '仙林', '江浦', '大厂', '桥北', '马群', '尧化', '板桥', '油坊桥',
        # 苏州
        '姑苏', '吴中', '相城', '吴江', '虎丘', '工业园', '昆山', '太仓', '常熟', '张家港',
        # 无锡
        '梁溪', '锡山', '惠山', '滨湖', '新吴', '江阴', '宜兴',
        # 常州
        '天宁', '钟楼', '新北', '武进',
        # 合肥
        '蜀山', '庐阳', '包河', '瑶海', '高新', '经开', '新站',
        # 芜湖
        '弋江', '镜湖', '鸠江',
        # 蚌埠
        '龙子湖', '蚌山', '禹会', '淮上',
        # 徐州
        '铜山', '云龙', '泉山', '贾汪',
        # 南通
        '崇川', '港闸', '通州',
        # 泰州
        '海陵', '高港', '姜堰',
        # 盐城
        '亭湖', '盐都',
        # 淮安
        '清江浦', '淮阴', '淮安区', '洪泽',
        # 宿迁
        '宿城', '宿豫',
        # 镇江
        '京口', '润州', '丹徒',
        # 扬州
        '广陵', '邗江', '江都'
    ]
    
    # 县城关键词
    COUNTY_KEYWORDS = ['县', '镇', '乡']
    
    # 市区关键词
    CITY_KEYWORDS = ['区', '路', '街', '广场', '大道', '万达', '吾悦', '万象']
    
    def __init__(self):
        """初始化分类器"""
        self._county_set = set(self.COUNTY_LIST)
        self._district_set = set(self.DISTRICT_LIST)
    
    def _classify_by_cpca(self, store_name: str, city: str = None) -> str:
        """使用cpca解析地址"""
        if not CPCA_AVAILABLE:
            return None
        
        try:
            # 构造地址字符串
            address = store_name
            if city:
                address = f"{city}{store_name}"
            
            # 使用cpca解析
            result = cpca.transform([address])
            if result is not None and len(result) > 0:
                area = result.iloc[0].get('区', '')
                if area:
                    area = str(area)
                    # 判断是区还是县
                    if area.endswith('区'):
                        return '市区'
                    elif area.endswith('县') or area.endswith('市'):
                        # 县级市也归为县城
                        return '县城'
        except Exception as e:
            logger.debug(f"cpca解析失败: {store_name}, 错误: {e}")
        
        return None
    
    def classify(self, store_name: str, city: str = None) -> str:
        """识别门店区域类型
        
        四层识别机制：
        1. 行政区划名单匹配（优先级最高）
        2. cpca地址解析
        3. 关键词规则
        4. 默认归为县城（兜底）
        
        Args:
            store_name: 门店名称
            city: 城市名称（可选）
            
        Returns:
            '市区' | '县城'
        """
        if store_name is None or (isinstance(store_name, str) and store_name == ''):
            return '县城'  # 默认县城
        try:
            if pd.isna(store_name):
                return '县城'
        except (TypeError, ValueError):
            pass
        
        store_name = str(store_name)
        
        # 第1层：县级名单匹配
        for county in self._county_set:
            if county in store_name:
                return '县城'
        
        # 第2层：市区名单匹配
        for district in self._district_set:
            if district in store_name:
                return '市区'
        
        # 第3层：cpca解析
        cpca_result = self._classify_by_cpca(store_name, city)
        if cpca_result:
            return cpca_result
        
        # 第4层：关键词规则
        for keyword in self.COUNTY_KEYWORDS:
            if keyword in store_name:
                return '县城'
        
        for keyword in self.CITY_KEYWORDS:
            if keyword in store_name:
                return '市区'
        
        # 第5层：默认归为县城
        return '县城'
    
    def classify_batch(self, df: pd.DataFrame, 
                       store_col: str = '门店名称',
                       city_col: str = '城市') -> pd.DataFrame:
        """批量识别区域类型"""
        result_df = df.copy()
        
        result_df['区域类型'] = result_df.apply(
            lambda row: self.classify(
                row.get(store_col), 
                row.get(city_col)
            ),
            axis=1
        )
        
        counts = result_df['区域类型'].value_counts()
        logger.info(f"✅ 区域分类完成: {dict(counts)}")
        
        return result_df


_classifier = None

def get_region_classifier() -> RegionClassifier:
    """获取区域分类器单例"""
    global _classifier
    if _classifier is None:
        _classifier = RegionClassifier()
    return _classifier
