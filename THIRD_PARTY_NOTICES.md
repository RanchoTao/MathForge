# 第三方边界

候选包没有捆绑第三方库、Lean、Mathlib、虚拟环境或旧 Git 对象。

运行依赖：jsonschema、attrs、jsonschema-specifications、referencing、rpds-py。此次下载的构件主许可证均为 MIT；精确版本与哈希见 requirements.lock。安装后的依赖仍受其自身许可证与归属通知约束。

构建工具 setuptools 与 wheel 的主许可证为 MIT。setuptools 的内部 vendoring 还带有其他许可证／通知；构件未并入本项目分发物，不能把其主许可证视为每个内部文件的完整授权。

可选 Lean 与 Mathlib 的版本化许可证见 [Lean 4.24.0](https://github.com/leanprover/lean4/blob/v4.24.0/LICENSE) 与 [Mathlib 4.24.0](https://github.com/leanprover-community/mathlib4/blob/v4.24.0/LICENSE)。当前排除整个分发物；若未来捆绑，需要重新审查其所有第三方组件和通知。

MathForge Core 已选择 Apache-2.0 用于维护者有权授权的原创代码与文档；第三方内容始终保留各自授权。本项目提取代码涉及的其他贡献者／机构权利，以及初始图片素材权利，仍须发布前核实。Logo 和 Banner 不是 Apache-2.0 软件授权的一部分；参见 [BRANDING.md](BRANDING.md)。本声明不授权分发私有工作区或任何无权授权的内容。
