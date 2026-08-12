import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'

const PAGE_TITLE = '관리자'
const POWER_BI_URL = import.meta.env.VITE_POWER_BI_ADMIN_OVERVIEW_URL

function getPowerBiEmbedUrl(url) {
  if (!url) return url

  const embedUrl = new URL(url)
  embedUrl.searchParams.set('pageView', 'fitToWidth')
  return embedUrl.toString()
}

export default function AdminPage() {
  const embedUrl = getPowerBiEmbedUrl(POWER_BI_URL)

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page admin-dashboard">
        <DashboardHeader title={PAGE_TITLE} />

        <section className="admin-powerbi-section" aria-label={`${PAGE_TITLE} Power BI 보고서`}>
          {embedUrl ? (
            <iframe
              className="admin-powerbi-frame"
              title={`${PAGE_TITLE} Power BI 보고서`}
              src={embedUrl}
              allowFullScreen
            />
          ) : (
            <div className="admin-powerbi-empty">
              <strong>Power BI 연결 대기</strong>
              <p>보고서 게시 후 이 페이지의 임베드 URL을 환경 변수에 연결해 주세요.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
