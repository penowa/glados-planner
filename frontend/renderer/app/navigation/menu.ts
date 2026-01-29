export type MenuItemId =
  | 'dashboard'
  | 'agenda'
  | 'sessions'
  | 'books'
  | 'glados'
  | 'reports'
  | 'settings'

export type MenuItem = {
  id: MenuItemId
  label: string
}

export const MENU_ITEMS: MenuItem[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'agenda', label: 'Agenda' },
  { id: 'sessions', label: 'Sessões' },
  { id: 'books', label: 'Livros' },
  { id: 'glados', label: 'Consultar GLaDOS' },
  { id: 'reports', label: 'Relatórios' },
  { id: 'settings', label: 'Configurações' }
]
