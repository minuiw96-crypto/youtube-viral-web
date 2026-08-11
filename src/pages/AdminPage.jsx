import { useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'
import { getAdminOverview } from '../api/client'
import { formatCategory } from '../utils/categoryLabels'

const KPI_ITEMS = [
  { key: 'channel_count', label: '수집 채널' },
  { key: 'video_count', label: '수집 영상' },
  { key: 'prediction_count', label: '예측 데이터' },
  { key: 'label_count', label: '평가 라벨' },
  { key: 'snapshot_count', label: '영상 스냅샷' },
  { key: 'user_count', label: '가입 계정' },
]

function formatCount(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toLocaleString('ko-KR') : '-'
}

function formatCoverage(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? `${parsed.toFixed(1)}%` : '-'
}

export default function AdminPage() {
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getAdminOverview()
      .then((data) => active && setOverview(data))
      .catch((requestError) => active && setError(requestError.message || '관리자 현황을 불러오지 못했습니다.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  const categories = overview?.categories || []
  const totalCategoryChannels = categories.reduce((sum, item) => sum + (Number(item.channel_count) || 0), 0)
  const topVideos = (overview?.video_ranking || []).slice(0, 5)
  const stats = overview?.stats || {}

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page admin-dashboard">
        <DashboardHeader title="관리자 대시보드" />

        {loading && <div className="panel-state"><span className="loading-spinner" />운영 현황을 불러오는 중입니다.</div>}
        {!loading && error && <div className="panel-state error-state">{error}</div>}

        {!loading && !error && overview && (
          <>
            <section className="admin-kpi-grid" aria-label="서비스 주요 지표">
              {KPI_ITEMS.map((item) => (
                <article className="admin-kpi-card" key={item.key}>
                  <span>{item.label}</span>
                  <strong>{formatCount(stats[item.key])}</strong>
                </article>
              ))}
            </section>

            <div className="admin-overview-grid">
              <section className="report-panel admin-coverage-panel">
                <div className="panel-heading"><div><h2>데이터 적용률</h2></div></div>
                <div className="admin-coverage-item">
                  <div><span>예측 완료 영상</span><strong>{formatCoverage(stats.prediction_coverage)}</strong></div>
                  <progress max="100" value={Number(stats.prediction_coverage) || 0} />
                </div>
                <div className="admin-coverage-item">
                  <div><span>라벨 확보 영상</span><strong>{formatCoverage(stats.label_coverage)}</strong></div>
                  <progress max="100" value={Number(stats.label_coverage) || 0} />
                </div>
              </section>

              <section className="report-panel admin-category-panel">
                <div className="panel-heading"><div><h2>채널 카테고리</h2></div></div>
                <div className="admin-category-list">
                  {categories.length ? categories.map((item) => {
                    const count = Number(item.channel_count) || 0
                    const share = totalCategoryChannels ? (count / totalCategoryChannels) * 100 : 0
                    return (
                      <div key={item.name}>
                        <span>{formatCategory(item.name)}</span>
                        <div><i style={{ width: `${share}%` }} /></div>
                        <strong>{formatCount(count)}</strong>
                      </div>
                    )
                  }) : <p className="compact-empty">카테고리 데이터가 없습니다.</p>}
                </div>
              </section>
            </div>

            <section className="report-panel admin-ranking-panel">
              <div className="panel-heading"><div><h2>상위 바이럴 영상</h2></div></div>
              {topVideos.length ? (
                <div className="admin-ranking-table-wrap">
                  <table className="admin-ranking-table">
                    <thead><tr><th>순위</th><th>영상</th><th>채널</th><th>카테고리</th><th>점수</th></tr></thead>
                    <tbody>
                      {topVideos.map((video, index) => (
                        <tr key={`${video.video_id}-${index}`}>
                          <td>{index + 1}</td>
                          <td><span>{video.title || '제목 없음'}</span></td>
                          <td>{video.channel_title || '-'}</td>
                          <td>{formatCategory(video.category)}</td>
                          <td><strong>{Number.isFinite(Number(video.viral_score)) ? Number(video.viral_score).toFixed(1) : '-'}</strong></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <div className="compact-empty">표시할 영상 랭킹이 없습니다.</div>}
            </section>
          </>
        )}
      </main>
    </div>
  )
}
