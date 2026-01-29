import { registerSystemHandlers } from './handlers/system.ipc'
import { registerAgendaHandlers } from './handlers/agenda.ipc'
// depois: reading, llm, vault...

export function registerIPCHandlers() {
  registerSystemHandlers()
  registerAgendaHandlers()
}
