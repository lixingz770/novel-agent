import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { apiGet } from '../api/client'
import './pages.css'

type RoleInfo = { role: string; md_count: number; json_count: number }
type RoleNoteInfo = { id: string; file: string }
type RoleNote = { role: string; id: string; content: string }

export function RolesPage() {
  const [roles, setRoles] = useState<RoleInfo[]>([])
  const [selectedRole, setSelectedRole] = useState<string | null>(null)
  const [notes, setNotes] = useState<RoleNoteInfo[]>([])
  const [selectedNote, setSelectedNote] = useState<string | null>(null)
  const [note, setNote] = useState<RoleNote | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadRoles = async () => {
      setLoading(true)
      setError(null)
      try {
        const r = await apiGet<RoleInfo[]>('/library/role-notes')
        setRoles(r)
        if (r.length > 0) setSelectedRole((cur) => cur ?? r[0].role)
      } catch (e) {
        setError(e instanceof Error ? e.message : '未知错误')
      } finally {
        setLoading(false)
      }
    }
    loadRoles()
  }, [])

  useEffect(() => {
    if (!selectedRole) return
    const loadNotes = async () => {
      setLoading(true)
      setError(null)
      try {
        const list = await apiGet<RoleNoteInfo[]>(`/library/role-notes/${encodeURIComponent(selectedRole)}`)
        setNotes(list)
        setSelectedNote((cur) => cur ?? (list[0]?.id ?? null))
      } catch (e) {
        setError(e instanceof Error ? e.message : '未知错误')
      } finally {
        setLoading(false)
      }
    }
    loadNotes()
  }, [selectedRole])

  useEffect(() => {
    if (!selectedRole || !selectedNote) return
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const n = await apiGet<RoleNote>(
          `/library/role-notes/${encodeURIComponent(selectedRole)}/${encodeURIComponent(selectedNote)}`,
        )
        setNote(n)
      } catch (e) {
        setError(e instanceof Error ? e.message : '未知错误')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [selectedRole, selectedNote])

  return (
    <div className="page">
      <div className="pageHead">
        <div>
          <h2 className="pageTitle">角色学习笔记</h2>
          <p className="pageDesc">
            这些笔记将被用于「分部大纲」生成：不同模块绑定不同角色笔记，形成可控、可追踪的生成依据。
          </p>
        </div>
      </div>

      {error && <div className="alert alertError">错误：{error}</div>}

      <div className="grid2">
        <div className="cardX">
          <div className="cardXTitle">角色</div>
          <div className="chips">
            {roles.map((r) => (
              <button
                key={r.role}
                className={selectedRole === r.role ? 'chip active' : 'chip'}
                onClick={() => setSelectedRole(r.role)}
              >
                {r.role} <span className="chipMeta">md {r.md_count}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="cardX">
          <div className="cardXTitle">该角色的笔记</div>
          {notes.length === 0 ? (
            <div className="muted2">暂无笔记。</div>
          ) : (
            <div className="chips">
              {notes.map((n) => (
                <button
                  key={n.id}
                  className={selectedNote === n.id ? 'chip active' : 'chip'}
                  onClick={() => setSelectedNote(n.id)}
                >
                  {n.file}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="cardX">
        <div className="cardXTitle">内容预览</div>
        {loading && <div className="muted2">加载中…</div>}
        {note ? (
          <div className="md">
            <ReactMarkdown>{note.content}</ReactMarkdown>
          </div>
        ) : (
          <div className="muted2">请选择一个角色与笔记。</div>
        )}
      </div>
    </div>
  )
}

