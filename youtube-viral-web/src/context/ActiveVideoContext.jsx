import { createContext, useContext, useMemo, useState } from 'react'

// Lets a page announce "the video the user is currently looking at" so the
// globally-mounted ChatWidget can resolve pronouns like "이 영상" without the
// user having to repeat the video title or link.
const ActiveVideoContext = createContext({ activeVideoId: null, setActiveVideoId: () => {} })

export function ActiveVideoProvider({ children }) {
  const [activeVideoId, setActiveVideoId] = useState(null)
  const value = useMemo(() => ({ activeVideoId, setActiveVideoId }), [activeVideoId])
  return <ActiveVideoContext.Provider value={value}>{children}</ActiveVideoContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components -- tiny context module, not worth a second file
export function useActiveVideo() {
  return useContext(ActiveVideoContext)
}
