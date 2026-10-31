/**
 * StockWise Frontend -> FastAPI Bridge Adapter
 * 
 * Drop this script in or inject before your bundle loads to route 
 * all API requests directly to the FastAPI Python backend.
 */
(function() {
  const BACKEND_BASE = "http://localhost:8000/api";
  const originalFetch = window.fetch;

  window.connectToFastAPI = async function() {
    try {
      const ping = await originalFetch("http://localhost:8000/");
      if (ping.ok) {
        console.log("[StockWise] Connected to live FastAPI Backend!");
        
        // Proxy all /api requests to FastAPI
        window.fetch = async (input, init) => {
          let url = typeof input === "string" ? input : input.url;
          if (url.includes("/api/")) {
            const apiPath = url.replace(/^.*?\/api/, "");
            return originalFetch(`${BACKEND_BASE}${apiPath}`, init);
          }
          return originalFetch(input, init);
        };
        return true;
      }
    } catch (e) {
      console.warn("[StockWise] FastAPI not running on :8000. Operating in offline simulation mode.");
      return false;
    }
  };

  // Attempt connection on startup
  window.connectToFastAPI();
})();

