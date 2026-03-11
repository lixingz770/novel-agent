import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost } from '../api/client'
import './pages.css'

type Project = {
  id: string
  name: string
  genre?: string | null
  audience?: string | null
  tone?: string | null
}

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [genre, setGenre] = useState('')
  const [audience, setAudience] = useState('')
  const [tone, setTone] = useState('')
  const [extra, setExtra] = useState('')

  const canSubmit = useMemo(() => name.trim().length > 0, [name])

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiGet<Project[]>('/projects')
      setProjects(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setLoading(true)
    setError(null)
    try {
      await apiPost('/projects', {
        name: name.trim(),
        genre: genre || null,
        audience: audience || null,
        tone: tone || null,
        extra: extra ? { description: extra } : undefined,
      })
      setName('')
      setGenre('')
      setAudience('')
      setTone('')
      setExtra('')
      setCreating(false)
      await load()
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="pageHead">
        <div>
          <h2 className="pageTitle">项目</h2>
          <p className="pageDesc">从需求出发，生成初纲 → 角色细化 → 汇总 → 确认 → 写作。</p>
        </div>
        <div className="pageActions">
          <button onClick={() => setCreating((v) => !v)}>{creating ? '关闭' : '新建项目'}</button>
        </div>
      </div>

      {error && <div className="alert alertError">错误：{error}</div>}

      {creating && (
        <div className="cardX">
          <div className="cardXTitle">提交转写/创作需求</div>
          <form className="gridForm" onSubmit={submit}>
            <label>
              项目名称 *
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：都市爽文·转写" />
            </label>
            <label>
              题材
              <input value={genre} onChange={(e) => setGenre(e.target.value)} placeholder="仙侠 / 都市 / 科幻…" />
            </label>
            <label>
              受众
              <input value={audience} onChange={(e) => setAudience(e.target.value)} placeholder="男频 / 女频 / 青年…" />
            </label>
            <label>
              基调
              <input value={tone} onChange={(e) => setTone(e.target.value)} placeholder="快节奏 / 热血 / 暗黑…" />
            </label>
            <label className="span2">
              需求描述（可选）
              <textarea value={extra} onChange={(e) => setExtra(e.target.value)} rows={3} placeholder="希望的叙事方式、必须要素、禁忌、参考风格…" />
            </label>
            <div className="span2">
              <button disabled={loading || !canSubmit} type="submit">
                {loading ? '提交中…' : '创建项目'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid2">
        <div className="cardX">
          <div className="cardXTitle">项目列表</div>
          {projects.length === 0 ? (
            <div className="muted2">暂无项目。</div>
          ) : (
            <ul className="list">
              {projects.map((p) => (
                <li key={p.id} className="listItem">
                  <div className="listMain">
                    <div className="listTitle">{p.name}</div>
                    <div className="listMeta">
                      <span>题材：{p.genre ?? '未设定'}</span>
                      <span>受众：{p.audience ?? '未设定'}</span>
                      <span>基调：{p.tone ?? '未设定'}</span>
                    </div>
                  </div>
                  <div className="listActions">
                    <Link className="linkBtn" to={`/projects/${encodeURIComponent(p.id)}/workflow`}>
                      工作流
                    </Link>
                    <Link className="linkBtn" to={`/projects/${encodeURIComponent(p.id)}/settings`}>
                      任务与设定
                    </Link>
                    <Link className="linkBtn primary" to={`/projects/${encodeURIComponent(p.id)}/modules`}>
                      分部大纲
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="cardX">
          <div className="cardXTitle">推荐路径</div>
          <ol className="steps">
            <li>新建项目（提交需求）</li>
            <li>进入「工作流」生成初步大纲</li>
            <li>进入「分部大纲」绑定 role 笔记生成各模块</li>
            <li>一键汇总为新版总纲并确认</li>
            <li>生成小说（章节大纲 → 正文草稿）</li>
          </ol>
        </div>
      </div>
    </div>
  )
}

