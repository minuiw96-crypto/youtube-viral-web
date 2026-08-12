import { Outlet } from 'react-router-dom'
import ChatWidget from './ChatWidget'
import { ActiveVideoProvider } from '../context/ActiveVideoContext'

export default function RootLayout() {
  return (
    <ActiveVideoProvider>
      <Outlet />
      <ChatWidget />
    </ActiveVideoProvider>
  )
}
