"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path = require("path");
const ipc_1 = require("./ipc");
function createWindow() {
    const win = new electron_1.BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            contextIsolation: true,
            nodeIntegration: false
        },
    });
    win.loadURL("http://localhost:5173");
}
electron_1.app.whenReady().then(() => {
    (0, ipc_1.registerIPCHandlers)();
    createWindow();
});
