"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerAgendaHandlers = registerAgendaHandlers;
const electron_1 = require("electron");
const backendIntegration_1 = require("../../backend/backendIntegration");
function registerAgendaHandlers() {
    electron_1.ipcMain.handle('agenda:list', async () => {
        return (0, backendIntegration_1.apiGet)('/agenda');
    });
    electron_1.ipcMain.handle('agenda:create', async (_, payload) => {
        return (0, backendIntegration_1.apiPost)('/agenda', payload);
    });
}
