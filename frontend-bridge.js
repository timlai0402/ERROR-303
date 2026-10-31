/**
 * StockWise Hardware Tracker - Unified Frontend Bridge
 * Connects the web app to FastAPI backend and Supabase PostgreSQL.
 * Secure: Privileged secret keys are strictly excluded from the browser client.
 */

(function () {
  const STORAGE_KEY = "stockwise_hardware_config";
  const DEFAULT_CONFIG = {
    url: "https://qrqcjxlexwvvgvisnphx.supabase.co",
    anonKey: "sb_publishable_im4IGU7Cwf4VAcQN87H0aA_5KQjoZB5",
    fastApiUrl: "http://localhost:8000",
    businessId: "biz-hardware-01",
    businessName: "Ah Huat Hardware & Auto Parts",
    currency: "MYR",
    isConnected: false,
  };

  let config = (function () {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
    } catch (e) {}
    return { ...DEFAULT_CONFIG };
  })();

  let backendHealth = {
    isAlive: false,
    version: "3.0.0",
    supabaseConnected: false,
  };

  // Expose bridge globally
  window.StockWiseBridge = {
    getConfig: () => ({ ...config }),
    saveConfig,
    checkBackendHealth,
    apiFetch,
    sbFetch,
    getHealthState: () => ({ ...backendHealth }),
  };

  function saveConfig(newCfg) {
    config = { ...config, ...newCfg };
    // Security: Ensure secretKey is never saved to client localStorage
    delete config.secretKey;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }

  async function checkBackendHealth() {
    const baseUrl = (config.fastApiUrl || "http://localhost:8000").replace(/\/+$/, "");
    try {
      const res = await fetch(`${baseUrl}/health`, {
        method: "GET",
        headers: { "Accept": "application/json" }
      });
      if (res.ok) {
        const data = await res.json();
        backendHealth = {
          isAlive: true,
          version: data.version || "3.0.0",
          supabaseConnected: Boolean(data.supabase?.connected),
        };
        return { ok: true, data };
      }
    } catch (e) {
      // Backend not running locally
    }
    backendHealth.isAlive = false;
    return { ok: false };
  }

  async function apiFetch(endpoint, method = "GET", body = null) {
    const baseUrl = (config.fastApiUrl || "http://localhost:8000").replace(/\/+$/, "");
    const cleanEp = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const url = `${baseUrl}${cleanEp}`;

    const headers = {
      "Accept": "application/json",
      "Content-Type": "application/json"
    };

    const opts = { method, headers };
    if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
      opts.body = typeof body === "string" ? body : JSON.stringify(body);
    }

    const res = await fetch(url, opts);
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("text/csv")) {
      return await res.text();
    }
    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }
    if (!res.ok) {
      const msg = (data && data.detail) ? data.detail : res.statusText;
      const err = new Error(msg);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  async function sbFetch(tableEndpoint, method = "GET", body = null) {
    if (!config.url || !config.anonKey) {
      throw new Error("Supabase credentials not configured.");
    }
    const cleanUrl = config.url.replace(/\/+$/, "");
    const fullUrl = `${cleanUrl}/rest/v1/${tableEndpoint.replace(/^\/+/, "")}`;

    const headers = {
      apikey: config.anonKey,
      Authorization: `Bearer ${config.anonKey}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    };

    const options = { method, headers };
    if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
      options.body = JSON.stringify(body);
    }

    const res = await fetch(fullUrl, options);
    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }
    if (!res.ok) {
      const msg = (data && data.message) ? data.message : res.statusText;
      throw new Error(msg);
    }
    return data;
  }
})();
