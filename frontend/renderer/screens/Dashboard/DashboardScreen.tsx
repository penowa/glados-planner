import { DashboardCards } from './DashboardCards'
import { MenuItemId } from '@/app/layout/Sidebar'

type Props = {
  selectedItem: MenuItemId
}

function labelFor(item: MenuItemId): string {
  switch (item) {
    case 'agenda':
      return 'Agenda'
    case 'sessions':
      return 'Sessões'
    case 'books':
      return 'Livros'
    case 'query':
      return 'Consultar GLaDOS'
    case 'reports':
      return 'Relatórios'
    case 'settings':
      return 'Sistema'
    default:
      return 'Dashboard'
  }
}

export function DashboardScreen({ selectedItem }: Props) {
  return (
    <section>
      <h2>{labelFor(selectedItem)}</h2>

      <DashboardCards selectedItem={selectedItem} />
    </section>
  )
}
