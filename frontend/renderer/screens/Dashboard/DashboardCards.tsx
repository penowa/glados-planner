import { MenuItemId } from '@/app/layout/Sidebar'

// Previews (mockados por enquanto)
function SystemPreview() {
  return <div>Estado geral do sistema</div>
}

function AgendaPreview() {
  return <div>Resumo da agenda do dia</div>
}

function SessionsPreview() {
  return <div>Sessões planejadas e em andamento</div>
}

function BooksPreview() {
  return <div>Livros ativos e progresso</div>
}

function QueryPreview() {
  return <div>Últimas consultas e sugestões</div>
}

function ReportsPreview() {
  return <div>Indicadores e relatórios recentes</div>
}

function SettingsPreview() {
  return <div>Configurações do sistema</div>
}

type Props = {
  selectedItem: MenuItemId
}

export function DashboardCards({ selectedItem }: Props) {
  switch (selectedItem) {
    case 'agenda':
      return <AgendaPreview />

    case 'sessions':
      return <SessionsPreview />

    case 'books':
      return <BooksPreview />

    case 'query':
      return <QueryPreview />

    case 'reports':
      return <ReportsPreview />

    case 'settings':
      return <SettingsPreview />

    default:
      return <SystemPreview />
  }
}
