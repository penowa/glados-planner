"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerSystemHandlers = registerSystemHandlers;
const electron_1 = require("electron");
const backendIntegration_1 = require("../../backend/backendIntegration");
function registerSystemHandlers() {
    electron_1.ipcMain.handle('system:ping', async () => {
        return (0, backendIntegration_1.apiGet)('/system/ping');
    });
}
