const base = import.meta.env.VITE_API_BASE_URL || ''
export async function request(path, data) {
  const response = await fetch(`${base}/api/${path}`, {method: data ? 'POST' : 'GET', headers: {'Content-Type': 'application/json'}, ...(data ? {body: JSON.stringify(data)} : {}), signal: AbortSignal.timeout(path === 'analyze' ? 3_900_000 : 300_000)})
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail) } catch { /* use status */ }
    throw new Error(message)
  }
  return response.json()
}
export async function downloadCapsule(scan_id) {
  const capsule = await request('capsule', {scan_id})
  const blob = new Blob([JSON.stringify(capsule, null, 2)], {type: 'application/json'})
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = `dependiq-${scan_id.slice(0,8)}.json`; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  return capsule
}
