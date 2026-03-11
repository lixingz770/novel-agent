import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Link, useParams } from 'react-router-dom'
import { apiGet, apiPost } from '../api/client'
import './pages.css'

type ProjectDetail = {
  id: string
  brief: {
    name: string
    genre?: string | null
    audience?: string | null
    tone?: string | null
    pov?: string | null
    taboo?: string[]
    must_have?: string[]
    extra?: Record<string, unknown>
  }
  latest_outline: { version: number; created_at: string; logline: string | null } | null
  approved_outline_version?: number | null
}

type OutlineSummary = { version: number; created_at: string; file: string }
type OutlineFull = { version: number; created_at: string; structure: Record<string, unknown>; markdown: string }
type ChapterIndex = { project_id: string; outline_version: number; chapters: { chapter: number; file: string; title: string }[] }
type Draft = { path: string; content: string }

export function ProjectWorkflowPage() {
  const { projectId } = useParams()
  const pid = projectId ? decodeURIComponent(projectId) : ''

  const [detail, setDetail] = useState<ProjectDetail | null>(null)
  const [outlines, setOutlines] = useState<OutlineSummary[]>([])
  const [viewVersion, setViewVersion] = useState<number | null>(null)
  const [outline, setOutline] = useState<OutlineFull | null>(null)
  const [chapters, setChapters] = useState<ChapterIndex | null>(null)
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const approved = detail?.approved_outline_version ?? null
  const latestVersion = outlines.length > 0 ? outlines[outlines.length - 1].version : null
  const canOperate = useMemo(() => !!pid, [pid])

  const loadAll = async () => {
    if (!pid) return
    setLoading(true)
    setError(null)
    try {
      const [d, list, chapterData] = await Promise.all([
        apiGet<ProjectDetail>(`/projects/${encodeURIComponent(pid)}`),
        apiGet<OutlineSummary[]>(`/projects/${encodeURIComponent(pid)}/outlines`),
        apiGet<ChapterIndex | null>(`/projects/${encodeURIComponent(pid)}/chapter-outlines`),
      ])
      setDetail(d)
      setOutlines(list)
      setChapters(chapterData)
      setOutline(null)
      setViewVersion(null)
      setSelectedChapter(null)
      setDraft(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pid])

  const openOutline = async (v: number) => {
    setLoading(true)
    setError(null)
    try {
      const full = await apiGet<OutlineFull>(`/projects/${encodeURIComponent(pid)}/outlines/${v}`)
      setOutline(full)
      setViewVersion(v)
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  const generateInitial = async () => {
    setLoading(true)
    setError(null)
    try {
      await apiPost(`/projects/${encodeURIComponent(pid)}/outline`)
      await loadAll()
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  const refineWithRoles = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiPost<OutlineFull>(`/projects/${encodeURIComponent(pid)}/outline/refine-with-roles`)
      setOutline(res)
      setViewVersion(res.version)
      await loadAll()
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  const approve = async () => {
    const v = viewVersion ?? latestVersion
    if (!v) return
    setLoading(true)
    setError(null)
    try {
      await apiPost(`/projects/${encodeURIComponent(pid)}/approve-outline`, { version: v })
      await loadAll()
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  const genChapters = async () => {
    setLoading(true)
    setError(null)
    try {
      const idx = await apiPost<ChapterIndex>(`/projects/${encodeURIComponent(pid)}/chapter-outlines`)
      setChapters(idx)
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  const genDraft = async () => {
    if (!selectedChapter) return
    setLoading(true)
    setError(null)
    try {
      const d = await apiPost<Draft>(`/projects/${encodeURIComponent(pid)}/chapters/${selectedChapter}/draft`)
      setDraft(d)
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
          <h2 className="pageTitle">工作流</h2>
          <p className="pageDesc">项目：{detail?.brief?.name ?? pid}</p>
        </div>
        <div className="pageActions">
          <Link className="linkBtn" to="/projects">
            返回项目列表
          </Link>
          <Link className="linkBtn" to={`/projects/${encodeURIComponent(pid)}/settings`}>
            任务与设定
          </Link>
          <Link className="linkBtn primary" to={`/projects/${encodeURIComponent(pid)}/modules`}>
            分部大纲
          </Link>
        </div>
      </div>

      {error && <div className="alert alertError">错误：{error}</div>}

      <div className="grid2">
        <div className="cardX">
          <div className="cardXTitle">步骤</div>
          <ol className="steps">
            <li>生成初步大纲（v1）</li>
            <li>按角色学习笔记细化并汇总（生成 v2/v3…）</li>
            <li>查看并确认大纲</li>
            <li>生成分章大纲 → 生成章节草稿</li>
          </ol>
        </div>

        <div className="cardX">
          <div className="cardXTitle">状态</div>
          <div className="muted2">已确认版本：{approved ? `v${approved}` : '未确认'}</div>
          <div className="muted2">大纲版本数：{outlines.length}</div>
          <div className="muted2">分章大纲：{chapters ? `已生成（v${chapters.outline_version}）` : '未生成'}</div>
        </div>
      </div>

      <div className="cardX">
        <div className="cardXTitle">操作</div>
        <div className="chips">
          <button className="chip" disabled={loading || !canOperate} onClick={generateInitial}>
            {loading ? '处理中…' : '生成初步大纲'}
          </button>
          <button className="chip" disabled={loading || !canOperate || outlines.length === 0} onClick={refineWithRoles}>
            {loading ? '处理中…' : '角色笔记细化汇总'}
          </button>
          <button className="chip" disabled={loading || !canOperate || outlines.length === 0} onClick={approve}>
            {loading ? '处理中…' : '确认当前大纲'}
          </button>
          <button className="chip" disabled={loading || !canOperate || outlines.length === 0} onClick={genChapters}>
            {loading ? '处理中…' : '生成分章大纲'}
          </button>
        </div>
        <div className="muted2">提示：确认大纲后再写作更稳（但不强制）。</div>
      </div>

      <div className="grid2">
        <div className="cardX">
          <div className="cardXTitle">大纲版本</div>
          {outlines.length === 0 ? (
            <div className="muted2">暂无大纲，请先生成初步大纲。</div>
          ) : (
            <div className="chips">
              {outlines.map((o) => (
                <button key={o.version} className={viewVersion === o.version ? 'chip active' : 'chip'} onClick={() => openOutline(o.version)}>
                  v{o.version}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="cardX">
          <div className="cardXTitle">分章大纲</div>
          {!chapters ? (
            <div className="muted2">尚未生成分章大纲。</div>
          ) : (
            <div className="chips">
              {chapters.chapters.map((c) => (
                <button
                  key={c.chapter}
                  className={selectedChapter === c.chapter ? 'chip active' : 'chip'}
                  onClick={() => {
                    setSelectedChapter(c.chapter)
                    setDraft(null)
                  }}
                >
                  第{c.chapter}章
                </button>
              ))}
              <button className="chip" disabled={loading || !selectedChapter} onClick={genDraft}>
                {loading ? '生成中…' : '生成本章草稿'}
              </button>
            </div>
          )}
        </div>
      </div>

      {outline && (
        <div className="cardX">
          <div className="cardXTitle">大纲预览（v{outline.version}）</div>
          <div className="md">
            <ReactMarkdown>{outline.markdown}</ReactMarkdown>
          </div>
        </div>
      )}

      {draft && (
        <div className="cardX">
          <div className="cardXTitle">草稿预览（第{selectedChapter}章）</div>
          <div className="md">
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{draft.content}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

