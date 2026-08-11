import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'

const POWER_BI_PAGES = {
  overview: {
    title: '운영 개요',
    url: import.meta.env.VITE_POWER_BI_ADMIN_OVERVIEW_URL,
  },
  pipeline: {
    title: '데이터 파이프라인',
    url: import.meta.env.VITE_POWER_BI_ADMIN_PIPELINE_URL,
  },
  quality: {
    title: '모델 품질',
    url: import.meta.env.VITE_POWER_BI_ADMIN_MODEL_QUALITY_URL,
  },
}

export default function AdminPage({ view = 'overview' }) {
  const page = POWER_BI_PAGES[view] || POWER_BI_PAGES.overview

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page admin-dashboard">
        <DashboardHeader title={page.title} />

        <section className="admin-powerbi-section" aria-label={`${page.title} Power BI 보고서`}>
          {page.url ? (
            <iframe
              className="admin-powerbi-frame"
              title={`${page.title} Power BI 보고서`}
              src={page.url}
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
