"""
属性名中英文对照模块
提供属性名的中文别名映射功能
"""

class AttributeMapping:
    """属性名中英文对照类"""
    
    # 属性名到中文别名的映射字典
    ATTRIBUTE_ALIAS_MAP = {
        # 基础参数
        'width': '日期宽度',
        'start_option': '开始日期值选择',
        'shift': '前移天数',
        'inc_rate': '止盈递增率',
        'op_days': '操作天数',
        'after_gt_end_edit': '止盈后值大于结束值比例',
        'after_gt_prev_edit': '止盈后值大于前值比例',
        'n_days': '第1组后N最大值逻辑',
        'n_days_max': '前1组结束地址后N日的最大值',
        'range_value': '开始日到结束日之间最高价/最低价小于',
        'continuous_abs_threshold': '连续绝对值阈值',
        'ops_change': '操作变化',
        'expr': '表达式',
        'last_select_count': '最后选择数量',
        'last_sort_mode': '最后排序方式',
        'direction': '方向',
        'analysis_start_date': '分析开始日期',
        'analysis_end_date': '分析结束日期',
        'component_analysis_start_date': '组合分析开始日期',
        'component_analysis_end_date': '组合分析结束日期',
        'cpu_cores': 'CPU核心数',
        'trade_mode': '交易模式',
        
        # 创新高新低参数
        'new_before_high_start': '创前新高开始',
        'new_before_high_range': '创前新高范围',
        'new_before_high_span': '创前新高跨度',
        'new_before_high_logic': '创前新高逻辑',
        'new_before_high2_start': '创前新高2开始',
        'new_before_high2_range': '创前新高2范围',
        'new_before_high2_span': '创前新高2跨度',
        'new_before_high2_logic': '创前新高2逻辑',
        'new_after_high_start': '创后新高开始',
        'new_after_high_range': '创后新高范围',
        'new_after_high_span': '创后新高跨度',
        'new_after_high_logic': '创后新高逻辑',
        'new_after_high2_start': '创后新高2开始',
        'new_after_high2_range': '创后新高2范围',
        'new_after_high2_span': '创后新高2跨度',
        'new_after_high2_logic': '创后新高2逻辑',
        'new_before_low_start': '创前新低开始',
        'new_before_low_range': '创前新低范围',
        'new_before_low_span': '创前新低跨度',
        'new_before_low_logic': '创前新低逻辑',
        'new_before_low2_start': '创前新低2开始',
        'new_before_low2_range': '创前新低2范围',
        'new_before_low2_span': '创前新低2跨度',
        'new_before_low2_logic': '创前新低2逻辑',
        'new_after_low_start': '创后新低开始',
        'new_after_low_range': '创后新低范围',
        'new_after_low_span': '创后新低跨度',
        'new_after_low_logic': '创后新低逻辑',
        'new_after_low2_start': '创后新低2开始',
        'new_after_low2_range': '创后新低2范围',
        'new_after_low2_span': '创后新低2跨度',
        'new_after_low2_logic': '创后新低2逻辑',
        'valid_abs_sum_threshold': '有效绝对值总和阈值',
        
        # 创新高新低标志
        'new_before_high_flag': '创前新高标志',
        'new_before_high2_flag': '创前新高2标志',
        'new_after_high_flag': '创后新高标志',
        'new_after_high2_flag': '创后新高2标志',
        'new_before_low_flag': '创前新低标志',
        'new_before_low2_flag': '创前新低2标志',
        'new_after_low_flag': '创后新低标志',
        'new_after_low2_flag': '创后新低2标志',
        
        # 组合分析特有参数
        'sort_mode': '排序方式',
        'increment_rate': '止盈递增率',
        
        # 日期相关
        'date': '日期',
        
        # 其他参数
        'formula': '公式',
        'plan_id': '方案ID',
        'plan_name': '方案名称',
        'selected_vars': '参加组合排序参数',
        'adjusted_value': '调整值',
        'total_sum': '总分',
        'valid_count': '有效数',
        'avg_sum': '平均分',
        'generate_time': '生成时间',
        'description': '描述'
    }
    
    @classmethod
    def get_chinese_alias(cls, attribute_name):
        """
        获取属性的中文别名
        
        Args:
            attribute_name (str): 英文属性名
            
        Returns:
            str: 中文别名，如果没有找到则返回原属性名
        """
        return cls.ATTRIBUTE_ALIAS_MAP.get(attribute_name, attribute_name)
    
    @classmethod
    def get_chinese_alias_dict(cls, params_dict):
        """
        将参数字典中的键转换为中文别名
        
        Args:
            params_dict (dict): 参数字典
            
        Returns:
            dict: 键为中文别名的参数字典
        """
        result = {}
        for key, value in params_dict.items():
            chinese_key = cls.get_chinese_alias(key)
            result[chinese_key] = value
        return result
    
    @classmethod
    def format_param_display(cls, attribute_name, value):
        """
        格式化参数显示，返回 "中文别名: 值" 的格式
        
        Args:
            attribute_name (str): 英文属性名
            value: 属性值
            
        Returns:
            str: 格式化后的显示字符串
        """
        chinese_alias = cls.get_chinese_alias(attribute_name)
        return f"{chinese_alias}: {value}"
    
    @classmethod
    def get_all_aliases(cls):
        """
        获取所有属性别名映射
        
        Returns:
            dict: 完整的属性别名映射字典
        """
        return cls.ATTRIBUTE_ALIAS_MAP.copy()


# 便捷函数
def get_chinese_alias(attribute_name):
    """获取属性的中文别名"""
    return AttributeMapping.get_chinese_alias(attribute_name)


def get_chinese_alias_dict(params_dict):
    """将参数字典中的键转换为中文别名"""
    return AttributeMapping.get_chinese_alias_dict(params_dict)


def format_param_display(attribute_name, value):
    """格式化参数显示"""
    return AttributeMapping.format_param_display(attribute_name, value)


def get_all_aliases():
    """获取所有属性别名映射"""
    return AttributeMapping.get_all_aliases() 