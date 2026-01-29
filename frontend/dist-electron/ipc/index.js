"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerIPCHandlers = registerIPCHandlers;
const system_ipc_1 = require("./handlers/system.ipc");
const agenda_ipc_1 = require("./handlers/agenda.ipc");
// depois: reading, llm, vault...
function registerIPCHandlers() {
    (0, system_ipc_1.registerSystemHandlers)();
    (0, agenda_ipc_1.registerAgendaHandlers)();
}
