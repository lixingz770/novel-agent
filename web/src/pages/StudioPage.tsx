import './pages.css'

export function StudioPage() {
  return (
    <div className="page">
      <div className="pageHead">
        <div>
          <h2 className="pageTitle">分部大纲 Studio</h2>
          <p className="pageDesc">
            这里会把总纲拆成「世界观 / 人物 / 主线 / 情绪 / 爽点 / 场景 / 对话 / 逻辑 / 章节规划」等模块，
            每个模块绑定对应 role 学习笔记来生成，然后一键汇总为新版总纲。
          </p>
        </div>
      </div>

      <div className="cardX">
        <div className="muted2">
          该页面的模块化生成与汇总将作为下一步实现（需要新增项目级模块配置与输出接口）。
          你现在可以先从「项目」进入某个项目的「分部大纲」页面使用。
        </div>
      </div>
    </div>
  )
}

