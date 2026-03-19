### **Consensus-Engine MCP：跨环境共识引擎需求文档 (Final Optimized PRD)**

这份 PRD 在原有基础上增加了 **“本地文件持久化”** 逻辑：要求 MCP 在完成多模型博弈后，自动将共识结论和讨论摘要写入项目根目录下的 `docs/` 文件夹中（例如 `docs/plans/` 或 `docs/reviews/`），实现决策过程的可追溯性。

---

### **1. 产品目标 (Vision)**
构建一个“专家委员会”决策中枢。通过 MCP 协议，在云端并发调用 2-5 个廉价大模型进行博弈，并将最终达成的共识结论自动持久化到本地项目的 `docs/` 目录下，为开发者提供高确定性、可存档的执行方案。

---

### **2. 核心架构设计 (System Architecture)**

#### **2.1 逻辑、配置与存储分离 (Decoupling Architecture)**
*   **云端 MCP Server**：执行并发请求、博弈算法、Prompt 模板拼装和结果汇总。
*   **本地环境注入**：模型私钥（URL, API Key）仅存在于本地机器，通过 `LOCAL_MODEL_CONFIGS` 环境变量注入。
*   **本地文件持久化 (New)**：MCP Server 必须具备文件写入权限（或通过 Claude Code 代理写入），将结论保存至本地 `docs/` 目录。

---

### **3. 核心功能需求 (Functional Requirements)**

#### **3.1 动态模型注入 (Dynamic Injection)**
*   **配置格式**：JSON 数组。包含各模型的名称、Endpoint 和 Key。
*   **验证逻辑**：启动时检查环境变量。若缺失，则通过 `stderr` 引导用户配置。

#### **3.2 三阶段博弈流程 (Debate Workflow)**
1.  **Proposal (提案)**：各模型生成初始方案。
2.  **Cross-Review (交叉评审)**：模型间互相寻找漏洞、安全风险或性能瓶颈。
3.  **Synthesis (汇总)**：由 Judge 模型整合所有观点，输出最终共识。

#### **3.3 自动存档机制 (Auto-Archiving)**
*   **存储路径规范**：
    *   `scene='planning'` -> 保存至 `docs/plans/YYYYMMDD_HHMM_plan.md`
    *   `scene='review'` -> 保存至 `docs/reviews/YYYYMMDD_HHMM_review.md`
    *   `scene='arch'/'debug'` -> 保存至 `docs/discussions/`
*   **文件内容**：包含最终共识计划、参与讨论的模型列表、以及简要的博弈摘要（Debate Summary）。

---

### **4. MCP 工具接口定义 (API Interface)**

#### **工具：`run_consensus_debate`**
*   **输入参数**：
    *   `task` (string): 核心任务。
    *   `content` (string): 相关代码或上下文。
    *   `scene` (enum): `planning` | `review` | `arch` | `debug`。
*   **输出**：返回包含 `final_plan` (Markdown) 和 `file_path` (存档路径) 的 JSON。

---

### **5. 交付指令 (Copy & Paste to Claude Code / Codex)**

**请直接复制以下内容发送给你的开发助手：**
