// Runtime configuration. `apiBase` is relative so the SPA works behind a proxy
// (dev: proxy.conf.json; prod: nginx rewrites /api -> backend).
export const environment = {
  production: false,
  apiBase: '/api/v1',
};
