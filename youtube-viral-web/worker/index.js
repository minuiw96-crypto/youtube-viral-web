export default {
  async fetch(request, env) {
    const url = new URL(request.url)

    if (url.pathname === '/api/config') {
      return Response.json({
        powerbi: {
          admin: env.VITE_POWER_BI_ADMIN_OVERVIEW_URL || env.POWERBI_ADMIN_URL || null,
          home: env.POWERBI_HOME_URL || null,
          user: env.POWERBI_USER_URL || null,
        },
      })
    }

    if (url.pathname.startsWith('/api/predict')) {
      return proxy(request, url, env.PREDICT_FUNCTION_BASE_URL, env.PREDICT_FUNCTION_KEY, '/api/predict')
    }

    if (url.pathname.startsWith('/api/')) {
      return proxy(request, url, env.AZURE_FUNCTION_BASE_URL, env.AZURE_FUNCTION_KEY, '/api')
    }

    return new Response('Not found', { status: 404 })
  },
}

async function proxy(request, url, baseUrl, functionKey, stripPrefix) {
  if (!baseUrl) {
    return Response.json(
      { error: '백엔드가 아직 설정되지 않았습니다.', code: 'BACKEND_NOT_CONFIGURED' },
      { status: 503 },
    )
  }

  const targetPath = url.pathname.slice(stripPrefix.length) || '/'
  const target = new URL(baseUrl.replace(/\/$/, '') + targetPath + url.search)

  const headers = new Headers(request.headers)
  headers.delete('host')
  if (functionKey) headers.set('x-functions-key', functionKey)

  const upstream = await fetch(target.toString(), {
    method: request.method,
    headers,
    body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
  })

  const responseHeaders = new Headers(upstream.headers)
  responseHeaders.delete('content-encoding')
  responseHeaders.delete('content-length')

  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders })
}
