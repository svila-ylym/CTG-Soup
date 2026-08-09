"""
核心工具函数：贝叶斯平均评分、密码哈希、JWT 处理等
"""
import math

def calculate_bayesian_average(
    item_votes: int, 
    item_avg: float, 
    global_avg: float, 
    global_votes: int,
    c: float = 10.0
):
    """
    贝叶斯平均评分公式: (C * m + R * v) / (C + v)
    C: 置信度常数 (默认10，表示需要多少票才能接近真实分数)
    m: 全局平均分
    R: 物品当前平均分
    v: 物品当前票数
    """
    if item_votes == 0:
        return global_avg
    
    weighted_score = (c * global_avg) + (item_votes * item_avg)
    total_weight = c + item_votes
    
    return weighted_score / total_weight
