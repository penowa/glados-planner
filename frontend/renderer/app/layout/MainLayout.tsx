import { useEffect, useState } from 'react'
import { Sidebar, MenuItemId } from './Sidebar'

import { DashboardScreen } from '@/screens/Dashboard/DashboardScreen'
import { AgendaScreen } from '@/screens/Agenda/AgendaScreen'
import { SessionsScreen } from '@/screens/Sessions/SessionsScreen'
import { BooksScreen } from '@/screens/Books/BooksScreen'
import { QueryScreen } from '@/screens/Query/QueryScreen'
import { ReportsScreen } from '@/screens/Reports/ReportsScreen'
import { SettingsScreen } from '@/screens/Settings/SettingsScreen'

export function MainLayout() {
  const [selectedItem, setSelectedItem] = useState<MenuItemId>('dashboard')
  const [activeItem, setActiveItem] = useState<MenuItemId>('dashboard')

  // Esc sempre retorna para a dashboard
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setActiveItem('dashboard')
        setSelectedItem('dashboard')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  function renderScreen() {
    switch (activeItem) {
      case 'agenda':
        return <AgendaScreen />

      case 'sessions':
        return <SessionsScreen />

      case 'books':
        return <BooksScreen />

      case 'query':
        return <QueryScreen />

      case 'reports':
        return <ReportsScreen />

      case 'settings':
        return <SettingsScreen />

      case 'dashboard':
      default:
        return <DashboardScreen selectedItem={selectedItem} />
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <Sidebar
        selectedItem={selectedItem}
        activeItem={activeItem}
        onSelect={setSelectedItem}
        onActivate={setActiveItem}
      />

      <main style={{ flex: 1 }}>
        {renderScreen()}
      </main>
    </div>
  )
}
