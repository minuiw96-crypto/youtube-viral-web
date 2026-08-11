import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import './index.css'
import RootLayout from './components/RootLayout'
import RequireAuth from './components/RequireAuth'
import RequireAdmin from './components/RequireAdmin'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import HomePage from './pages/HomePage'
import MyChannelPage from './pages/MyChannelPage'
import PredictPage from './pages/PredictPage'
import SettingsPage from './pages/SettingsPage'
import AdminPage from './pages/AdminPage'

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      {
        path: '/home',
        element: (
          <RequireAuth>
            <HomePage />
          </RequireAuth>
        ),
      },
      {
        path: '/my-channel',
        element: (
          <RequireAuth>
            <MyChannelPage view="benchmark" />
          </RequireAuth>
        ),
      },
      {
        path: '/my-channel/performance',
        element: <Navigate to="/lab/video-insights" replace />,
      },
      {
        path: '/lab',
        element: <Navigate to="/lab/video-insights" replace />,
      },
      {
        path: '/lab/video-insights',
        element: (
          <RequireAuth>
            <MyChannelPage view="performance" />
          </RequireAuth>
        ),
      },
      {
        path: '/predict',
        element: (
          <RequireAuth>
            <PredictPage />
          </RequireAuth>
        ),
      },
      {
        path: '/admin',
        element: (
          <RequireAdmin>
            <AdminPage view="overview" />
          </RequireAdmin>
        ),
      },
      {
        path: '/admin/pipeline',
        element: (
          <RequireAdmin>
            <AdminPage view="pipeline" />
          </RequireAdmin>
        ),
      },
      {
        path: '/admin/model-quality',
        element: (
          <RequireAdmin>
            <AdminPage view="quality" />
          </RequireAdmin>
        ),
      },
      {
        path: '/settings',
        element: (
          <RequireAuth>
            <SettingsPage />
          </RequireAuth>
        ),
      },
    ],
  },
])

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
