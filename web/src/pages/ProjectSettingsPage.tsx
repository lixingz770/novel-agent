import { useEffect, useMemo, useState, type FormEvent } from 'react'
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
    nice_to_have?: string[]
    length_words?: number | null
    references?: string[]
    delivery?: string | null
    extra?: Record<string, unknown>
  }
}

function parseList(text: string): string[] {
  return text
    .split(/[,，\\n]/g)
    .map((s) => s.trim())
    .filter(Boolean)
}

export function ProjectSettingsPage() {
  const { projectId } = useParams()
  const pid = projectId ? decodeURIComponent(projectId) : ''

  const [detail, setDetail] = useState<ProjectDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  const [genre, setGenre] = useState('')
  const [audience, setAudience] = useState('')
  const [tone, setTone] = useState('')
  const [pov, setPov] = useState('')
  const [taboo, setTaboo] = useState('')
  const [mustHave, setMustHave] = useState('')
  const [niceToHave, setNiceToHave] = useState('')
  const [references, setReferences] = useState('')
  const [lengthWords, setLengthWords] = useState('')
  const [delivery, setDelivery] = useState('markdown')
  const [taskSetting, setTaskSetting] = useState('')

  const canSave = useMemo(() => !!pid, [pid])

  const load = async () => {
    if (!pid) return
    setLoading(true)
    setError(null)
    setSaved(null)
    try {
      const d = await apiGet<ProjectDetail>(`/projects/${encodeURIComponent(pid)}`)
      setDetail(d)
      setGenre(d.brief.genre ?? '')
      setAudience(d.brief.audience ?? '')
      setTone(d.brief.tone ?? '')
      setPov(d.brief.pov ?? '')
      setTaboo((d.brief.taboo ?? []).join('\\n'))
      setMustHave((d.brief.must_have ?? []).join('\\n'))
      setNiceToHave((d.brief.nice_to_have ?? []).join('\\n'))
      setReferences((d.brief.references ?? []).join('\\n'))
      setLengthWords(d.brief.length_words != null ? String(d.brief.length_words) : '')
      setDelivery(d.brief.delivery ?? 'markdown')
      setTaskSetting(String(d.brief.extra?.task_setting ?? ''))
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pid])

  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!canSave) return
    setLoading(true)
    setError(null)
    setSaved(null)
    try {
      await apiPost(`/projects/${encodeURIComponent(pid)}/brief/update`, {
        genre: genre || null,
        audience: audience || null,
        tone: tone || null,
        pov: pov || null,
        taboo: parseList(taboo),
        must_have: parseList(mustHave),
        nice_to_have: parseList(niceToHave),
        references: parseList(references),
        length_words: lengthWords ? Number(lengthWords) : null,
        delivery: delivery || 'markdown',
        extra: { task_setting: taskSetting || '' },
      })
      setSaved('已保存。接下来去「工作流」生成大纲，或去「分部大纲」做模块化生成。')
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
          <h2 className="pageTitle">任务与设定</h2>
          <p className="pageDesc">项目：{detail?.brief?.name ?? pid}</p>
        </div>
        <div className="pageActions">
          <Link className="linkBtn" to={`/projects/${encodeURIComponent(pid)}/workflow`}>
            返回工作流
          </Link>
          <Link className="linkBtn primary" to={`/projects/${encodeURIComponent(pid)}/modules`}>
            去分部大纲
          </Link>
        </div>
      </div>

      {error && <div className="alert alertError">错误：{error}</div>}
      {saved && <div className="alert">{saved}</div>}

      <div className="cardX">
        <div className="cardXTitle">结构化配置（会写入 brief.json，直接影响大纲与写作）</div>
        <form className="gridForm" onSubmit={save}>
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
          <label>
            视角（POV）
            <input value={pov} onChange={(e) => setPov(e.target.value)} placeholder="第一人称 / 第三人称…" />
          </label>

          <label className="span2">
            禁忌/雷点（每行一条，或用逗号分隔）
            <textarea value={taboo} onChange={(e) => setTaboo(e.target.value)} rows={3} placeholder="例如：不虐主、不后宫…" />
          </label>
          <label className="span2">
            必须包含（每行一条）
            <textarea value={mustHave} onChange={(e) => setMustHave(e.target.value)} rows={3} placeholder="例如：反转、打脸、关键道具…" />
          </label>
          <label className="span2">
            加分项（每行一条）
            <textarea value={niceToHave} onChange={(e) => setNiceToHave(e.target.value)} rows={3} placeholder="例如：群像、轻松吐槽…" />
          </label>
          <label className="span2">
            参考作品（每行一条）
            <textarea value={references} onChange={(e) => setReferences(e.target.value)} rows={2} placeholder="例如：某某作品名…" />
          </label>

          <label>
            目标字数（可选）
            <input value={lengthWords} onChange={(e) => setLengthWords(e.target.value)} placeholder="例如：80000" />
          </label>
          <label>
            交付格式
            <input value={delivery} onChange={(e) => setDelivery(e.target.value)} placeholder="markdown" />
          </label>

          <label className="span2">
            任务设定（主线/支线/里程碑等，给大纲用）
            <textarea
              value={taskSetting}
              onChange={(e) => setTaskSetting(e.target.value)}
              rows={4}
              placeholder="例如：主线目标、阶段里程碑、失败代价、支线触发条件、与主线交汇点…"
            />
          </label>

          <div className="span2">
            <button disabled={loading || !canSave} type="submit">
              {loading ? '保存中…' : '保存设定'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

