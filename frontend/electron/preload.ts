export {};
import { contextBridge, ipcRenderer } from 'electron'
contextBridge.exposeInMainWorld('glados', {
  system: {
    ping: () => ipcRenderer.invoke('system:ping')
  },

  agenda: {
    list: () => ipcRenderer.invoke('agenda:list'),
    create: (data: any) =>
      ipcRenderer.invoke('agenda:create', data)
  }
})
