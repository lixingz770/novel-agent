import './App.css'
import { Navigate, Route, Routes } from 'react-router-dom'
import { DashboardLayout } from './layout/DashboardLayout'
import { ProjectsPage } from './pages/ProjectsPage'
import { ProjectModulesPage } from './pages/ProjectModulesPage'
import { ProjectSettingsPage } from './pages/ProjectSettingsPage'
import { ProjectWorkflowPage } from './pages/ProjectWorkflowPage'
import { RolesPage } from './pages/RolesPage'
import { StudioPage } from './pages/StudioPage'

export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route index element={<Navigate to="/projects" replace />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId/workflow" element={<ProjectWorkflowPage />} />
        <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />
        <Route path="/projects/:projectId/modules" element={<ProjectModulesPage />} />
        <Route path="/studio" element={<StudioPage />} />
        <Route path="/roles" element={<RolesPage />} />
        <Route path="*" element={<Navigate to="/projects" replace />} />
      </Route>
    </Routes>
  )
}
