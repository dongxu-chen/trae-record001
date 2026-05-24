import React, { useEffect, useState } from 'react'
import { useDispatch } from 'react-redux'
import Toolbar from './components/Toolbar'
import ComponentPalette from './components/ComponentPalette'
import DashboardCanvas from './components/DashboardCanvas'
import ComponentMarket from './components/ComponentMarket'
import AlertCenter from './components/AlertCenter'
import CollaborationPanel from './components/CollaborationPanel'
import { loadLayout } from './store/dashboardSlice'

function App() {
  const dispatch = useDispatch()
  const [showMarket, setShowMarket] = useState(false)
  const [showAlerts, setShowAlerts] = useState(false)

  useEffect(() => {
    dispatch(loadLayout())
  }, [dispatch])

  return (
    <div className="app">
      <Toolbar onOpenMarket={() => setShowMarket(true)} onOpenAlerts={() => setShowAlerts(true)} />
      <div className="app-body">
        <ComponentPalette onOpenMarket={() => setShowMarket(true)} />
        <main id="dashboard-content" className="dashboard-content">
          <CollaborationPanel />
          <DashboardCanvas />
        </main>
      </div>

      {showMarket && <ComponentMarket onClose={() => setShowMarket(false)} />}
      {showAlerts && <AlertCenter onClose={() => setShowAlerts(false)} />}
    </div>
  )
}

export default App
