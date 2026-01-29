export function useIPC() {
  if (!window.glados) {
    throw new Error('GLaDOS IPC not available')
  }

  return {
    system: {
      ping: () => window.glados.system.ping()
    }
  }
}
