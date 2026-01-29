import React, { KeyboardEvent } from 'react'

export type MenuItemId =
  | 'dashboard'
  | 'agenda'
  | 'sessions'
  | 'books'
  | 'query'
  | 'reports'
  | 'settings'

type MenuItem = {
  id: MenuItemId
  label: string
}

const MENU_ITEMS: MenuItem[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'agenda', label: 'Agenda' },
  { id: 'sessions', label: 'Sessões' },
  { id: 'books', label: 'Livros' },
  { id: 'query', label: 'Consultar GLaDOS' },
  { id: 'reports', label: 'Relatórios' },
  { id: 'settings', label: 'Sistema' },
]

type Props = {
  selectedItem: MenuItemId
  activeItem: MenuItemId
  onSelect: (item: MenuItemId) => void
  onActivate: (item: MenuItemId) => void
}

export function Sidebar({
  selectedItem,
  activeItem,
  onSelect,
  onActivate,
}: Props) {
  function handleKeyDown(e: KeyboardEvent<HTMLUListElement>) {
    const index = MENU_ITEMS.findIndex(i => i.id === selectedItem)

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = MENU_ITEMS[index + 1] ?? MENU_ITEMS[0]
      onSelect(next.id)
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault()
      const prev = MENU_ITEMS[index - 1] ?? MENU_ITEMS[MENU_ITEMS.length - 1]
      onSelect(prev.id)
    }

    if (e.key === 'Enter') {
      e.preventDefault()
      onActivate(selectedItem)
    }
  }

  return (
    <aside>
      <nav>
        <ul
          tabIndex={0}
          onKeyDown={handleKeyDown}
        >
          {MENU_ITEMS.map(item => {
            const isSelected = item.id === selectedItem
            const isActive = item.id === activeItem

            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => {
                    onSelect(item.id)
                    onActivate(item.id)
                  }}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {item.label}
                  {isActive ? ' •' : ''}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}
