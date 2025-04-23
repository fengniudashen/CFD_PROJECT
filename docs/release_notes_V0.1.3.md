# Release Notes - V0.1.3

## 主要变更

*   **架构重构**: 开始将核心分析逻辑（包括状态管理、局部范围确定和结果合并）迁移到 C++ 实现 (`CppAnalysisManager`)，旨在大幅提升性能并简化 Python 端的逻辑。这是一个进行中的重大变更。
*   **文档更新**: 全面更新项目文档，以反映新的架构方向和当前开发状态。包括 `README.md`, `installation_guide.md`, `api_reference.md`, `self_intersection_algorithm.md` 等。

## 已知问题

*   C++ 核心管理器的实现仍在进行中，相关功能可能尚未完全可用或稳定。
*   性能数据（如 README 中的表格）可能基于旧架构，将在新架构稳定后更新。 