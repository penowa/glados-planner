"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('glados', {
    system: {
        ping: () => electron_1.ipcRenderer.invoke('system:ping')
    },
    agenda: {
        list: () => electron_1.ipcRenderer.invoke('agenda:list'),
        create: (data) => electron_1.ipcRenderer.invoke('agenda:create', data)
    }
});
