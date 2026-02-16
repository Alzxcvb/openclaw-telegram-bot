// Simple proxy that rewrites the model in OpenRouter API calls
import http from 'http';
import https from 'https';

const TARGET_MODEL = process.env.OVERRIDE_MODEL || 'google/gemma-3n-e2b-it:free';
const OPENROUTER_HOST = 'openrouter.ai';

const server = http.createServer((req, res) => {
  let body = '';
  req.on('data', chunk => body += chunk);
  req.on('end', () => {
    // Rewrite model in request body
    try {
      if (body) {
        const parsed = JSON.parse(body);
        if (parsed.model) {
          console.log(`[proxy] Rewriting model: ${parsed.model} -> ${TARGET_MODEL}`);
          parsed.model = TARGET_MODEL;
          body = JSON.stringify(parsed);
        }
      }
    } catch (e) { /* not JSON, pass through */ }

    const options = {
      hostname: OPENROUTER_HOST,
      port: 443,
      path: req.url,
      method: req.method,
      headers: {
        ...req.headers,
        host: OPENROUTER_HOST,
        'content-length': Buffer.byteLength(body),
      },
    };

    const proxyReq = https.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });

    proxyReq.on('error', (e) => {
      console.error('[proxy] Error:', e.message);
      res.writeHead(502);
      res.end('Proxy error');
    });

    proxyReq.write(body);
    proxyReq.end();
  });
});

const PORT = process.env.PROXY_PORT || 3456;
server.listen(PORT, '127.0.0.1', () => {
  console.log(`[proxy] Model rewrite proxy listening on http://127.0.0.1:${PORT}`);
  console.log(`[proxy] Rewriting all models to: ${TARGET_MODEL}`);
});
