import { ipcMain } from 'electron'
import { apiGet, apiPost } from '../../backend/backendIntegration'

export function registerAgendaHandlers() {
  ipcMain.handle('agenda:list', async () => {
    return apiGet('/agenda')
  })

  ipcMain.handle('agenda:create', async (_, payload) => {
    return apiPost('/agenda', payload)
  })
}
