"""
网格检测算法包
"""

# 导入所有算法类，方便外部使用
from .base_algorithm import BaseAlgorithm
from .algorithm_utils import AlgorithmUtils, OctreeNode

# 导入所有已创建的算法
from .free_edges_algorithm import FreeEdgesAlgorithm
from .overlapping_edges_algorithm import OverlappingEdgesAlgorithm
from .self_intersection_algorithm import SelfIntersectionAlgorithm
from .pierced_faces_algorithm import PiercedFacesAlgorithm
from .face_quality_algorithm import FaceQualityAlgorithm
from .overlapping_points_algorithm import OverlappingPointsAlgorithm
from .non_manifold_vertices_algorithm import NonManifoldVerticesAlgorithm

# 版本信息
__version__ = "0.0.9" 