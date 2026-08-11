import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import RootLayout from './components/RootLayout'
import RequireAuth from './components/RequireAuth'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import HomePage from './pages/HomePage'
import MyChannelPage from './pages/MyChannelPage'
import PredictPage from './pages/PredictPage'
import SettingsPage from './pages/SettingsPage'

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
