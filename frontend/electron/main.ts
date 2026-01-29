import { app, BrowserWindow } from "electron";
import * as path from "path";
import { registerIPCHandlers } from './ipc'

function createWindow() {
  const win = new BrowserWindow({
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

app.whenReady().then(() => {
  registerIPCHandlers()
  createWindow()
})