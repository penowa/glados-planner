import { ipcMain } from 'electron'
import { apiGet } from '../../backend/backendIntegration'

export function registerSystemHandlers() {
  ipcMain.handle('system:ping', async () => {
    return apiGet<string>('/system/ping')
  })
}
