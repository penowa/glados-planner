import React from 'react'
import ReactDOM from 'react-dom/client'

import { MainLayout } from '@/app/layout/MainLayout'
import { DashboardScreen } from '@/screens/Dashboard/DashboardScreen'

import '@/src/styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MainLayout>
      <DashboardScreen />
    </MainLayout>
  </React.StrictMode>
)
