import { useState } from 'react'
import { StoreProvider, useStore } from './store'
import Home from './screens/Home'
import Schedule from './screens/Schedule'
import Trip from './screens/Trip'
import Journey from './screens/Journey'
import Booked from './screens/Booked'
import Insights from './screens/Insights'
import Wallet from './screens/Wallet'
import History from './screens/History'
import { useT } from './useT'
import { DevDrawer } from './components/DevDrawer'
import { BottomNav, NotificationsSheet, SideMenu, SubHeader } from './components/Chrome'
import { anyMock } from './api'

function Shell() {
  const t = useT()
  const { view } = useStore()
  const [menu, setMenu] = useState(false)
  const [notif, setNotif] = useState(false)
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-plum text-white">
      {view !== 'home' && <SubHeader onMenu={() => setMenu(true)} />}

      {anyMock() && (
        <p className="mx-4 mt-2 rounded-lg bg-amber-200 px-3 py-1.5 text-center text-xs font-bold text-plum" role="note">
          {t('Demo build: some screens use temporary MOCK data (not the real engine yet).')}
        </p>
      )}

      {view === 'home' ? (
        <Home onMenu={() => setMenu(true)} onNotif={() => setNotif(true)} />
      ) : (
        <main className="flex-1 px-4 pb-32 pt-4">
          {view === 'schedule' && <Schedule />}
          {view === 'trip' && <Trip />}
          {view === 'journey' && <Journey />}
          {view === 'booked' && <Booked />}
          {view === 'insights' && <Insights />}
          {view === 'wallet' && <Wallet />}
          {view === 'history' && <History />}
          <p className="mt-8 text-center text-xs text-white/55">{t('UniLink — hackathon prototype, simulation data.')}</p>
        </main>
      )}

      <BottomNav />
      <SideMenu open={menu} onClose={() => setMenu(false)} />
      <NotificationsSheet open={notif} onClose={() => setNotif(false)} />
      <DevDrawer />
    </div>
  )
}

export default function App() {
  return (
    <StoreProvider>
      <Shell />
    </StoreProvider>
  )
}
