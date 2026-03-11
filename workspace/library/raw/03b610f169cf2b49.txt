 ## 小说编辑部 Agent（本地CLI）
 
 这是一个本地运行的“小说编辑部式”智能体：支持**喂小说→学习笔记→索引检索**，以及**客户需求→大纲迭代→分章大纲→章节生成→审校→交付打包**的完整流程。
 
 ### 快速开始
 
 - **安装**
 
 ```bash
 python -m venv .venv
 source .venv/bin/activate
 pip install -U pip
 pip install -e .
 ```
 
 - **初始化工作区（默认在 `./workspace`）**
 
 ```bash
 novelagent init
 ```
 
 - **查看命令**
 
 ```bash
 novelagent --help
 ```
 
 ### 工作区结构（落盘可追踪）
 
- `workspace/library/`：学习素材库（raw/chunks/notes/index）
- `workspace/projects/`：客户项目（brief/outlines/chapter_outlines/drafts/reviews/delivery）
 ### 配置
 
复制并编辑 `novelagent.yaml`（可选）。环境变量也支持：

- `NOVELAGENT_WORKSPACE`：工作区路径
- `NOVELAGENT_BASE_URL`：兼容OpenAI的API地址（DeepSeek等）
- `NOVELAGENT_API_KEY`：API Key
- `NOVELAGENT_MODEL`：默认模型名

