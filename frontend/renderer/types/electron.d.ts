export {}

declare global {
  interface Window {
    glados: {
      system: {
        ping(): Promise<string>
      }
    }
  }
}
