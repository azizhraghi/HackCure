const AsyncStorage = {
  async getItem(key: string): Promise<string | null> {
    try { return window.localStorage.getItem(key); } catch { return null; }
  },
  async setItem(key: string, value: string): Promise<void> {
    try { window.localStorage.setItem(key, value); } catch {}
  },
  async removeItem(key: string): Promise<void> {
    try { window.localStorage.removeItem(key); } catch {}
  },
};

export default AsyncStorage;
