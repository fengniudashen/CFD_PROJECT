"""
网格检测算法包
"""

# 导入所有算法类，方便外部使用
from .base_algorithm import BaseAlgorithm
from .algorithm_utils import AlgorithmUtils, OctreeNode

# 导入所有已创建的算法
from .free_edges_algorithm import FreeEdgesAlgorithm
from .overlapping_edges_algorithm import OverlappingEdgesAlgorithm
from .face_quality_algorithm import FaceQualityAlgorithm
from .combined_intersection_algorithm import CombinedIntersectionAlgorithm  # 现在仅支持穿刺面检测
from .merged_vertex_detection_algorithm import MergedVertexDetectionAlgorithm

# 版本信息
__version__ = "0.1.0" 