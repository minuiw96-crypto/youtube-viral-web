import { Outlet } from 'react-router-dom'
import ChatWidget from './ChatWidget'

export default function RootLayout() {
  return (
    <>
      <Outlet />
      <ChatWidget />
    </>
  )
}
