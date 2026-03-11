import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api/client'
import './pages.css'

type RoleInfo = { role: string; md_count: number; json_count: number }

export function ProjectModulesPage() {
  const { projectId } = useParams()
  const pid = projectId ? decodeURIComponent(projectId) : ''

  const [roles, setRoles] = useState<RoleInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canOperate = useMemo(() => !!pid, [pid])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const r = await apiGet<RoleInfo[]>('/library/role-notes')
        setRoles(r)
      } catch (e) {
        setError(e instanceof Error ? e.message : '未知错误')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const quickRefine = async () => {
    if (!pid) return
    setLoading(true)
    setError(null)
    try {
      await apiPost(`/projects/${encodeURIComponent(pid)}/outline/refine-with-roles`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="pageHead">
        <div>
          <h2 className="pageTitle">分部大纲</h2>
          <p className="pageDesc">
            项目：{pid}。下一阶段会把总纲拆成模块（世界观/人物/主线/情绪/爽点/对话/逻辑/章节规划…），
            每个模块绑定 role 笔记生成，再一键汇总为新版总纲。
          </p>
        </div>
        <div className="pageActions">
          <Link className="linkBtn" to={`/projects/${encodeURIComponent(pid)}/workflow`}>
            返回工作流
          </Link>
          <Link className="linkBtn" to={`/projects/${encodeURIComponent(pid)}/settings`}>
            任务与设定
          </Link>
          <Link className="linkBtn" to="/roles">
            查看角色笔记库
          </Link>
        </div>
      </div>

      {error && <div className="alert alertError">错误：{error}</div>}

      <div className="grid2">
        <div className="cardX">
          <div className="cardXTitle">可用角色笔记</div>
          <div className="chips">
            {roles.map((r) => (
              <div key={r.role} className="chip">
                {r.role} <span className="chipMeta">md {r.md_count}</span>
              </div>
            ))}
          </div>
          {roles.length === 0 && <div className="muted2">暂无角色笔记，请先 learn-roles。</div>}
        </div>

        <div className="cardX">
          <div className="cardXTitle">临时可用：一键细化汇总</div>
          <div className="muted2">
            目前你已有「角色笔记细化汇总」后端能力。模块化生成会在下一步补齐接口与 UI。
          </div>
          <div style={{ marginTop: 10 }}>
            <button disabled={loading || !canOperate} onClick={quickRefine}>
              {loading ? '处理中…' : '按角色笔记细化并汇总总纲'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

