import { useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'
import { getAdminOverview } from '../api/client'

const PAGE_TITLES = {
  overview: '운영 개요',
  pipeline: '파이프라인',
  quality: '모델 품질',
}

function number(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function formatCount(value) {
  const parsed = number(value)
  return parsed === null ? '-' : Math.round(parsed).toLocaleString('ko-KR')
}

function completedCount(total, coverage) {
  const totalValue = number(total)
  const coverageValue = number(coverage)
  if (totalValue === null || coverageValue === null) return null
  return Math.round(totalValue * coverageValue / 100)
}

function StageCard({ step, title, value, detail, state = 'waiting' }) {
  const stateLabel = state === 'ready' ? '데이터 확인' : state === 'warning' ? '누락 확인' : '연결 대기'
  return (
    <article className={`admin-stage-card ${state}`}>
      <div className="admin-stage-heading"><span>{step}</span><b>{stateLabel}</b></div>
      <h2>{title}</h2>
      <strong>{formatCount(value)}</strong>
      <p>{detail}</p>
    </article>
  )
}

function PowerBiPlaceholder({ title }) {
  return (
    <section className="admin-powerbi-section">
      <div className="admin-powerbi-heading"><h2>{title}</h2><span>Power BI 연결 예정</span></div>
      <div className="admin-powerbi-placeholder" aria-label={`${title} Power BI 삽입 영역`} />
    </section>
  )
}

export default function AdminPage({ view = 'overview' }) {
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

  const stats = overview?.stats || {}
  const videoCount = number(stats.video_count)
  const predictedCount = number(stats.prediction_count) ?? completedCount(videoCount, stats.prediction_coverage)
  const labeledCount = number(stats.label_count) ?? completedCount(videoCount, stats.label_coverage)
  const predictionMissing = videoCount === null || predictedCount === null ? null : Math.max(0, videoCount - predictedCount)
  const labelMissing = videoCount === null || labeledCount === null ? null : Math.max(0, videoCount - labeledCount)
  const stateForMissing = (value) => value === null ? 'waiting' : value > 0 ? 'warning' : 'ready'

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page admin-dashboard">
        <DashboardHeader title={PAGE_TITLES[view] || PAGE_TITLES.overview} />

        {loading && <div className="panel-state"><span className="loading-spinner" />운영 현황을 불러오는 중입니다.</div>}
        {!loading && error && <div className="panel-state error-state">{error}</div>}

        {!loading && !error && overview && view === 'overview' && (
          <>
            <section className="admin-pipeline-flow" aria-label="수집, 예측, 평가 처리 현황">
              <StageCard step="01" title="수집 상태" value={stats.video_count} detail={`스냅샷 ${formatCount(stats.snapshot_count)}개 · 마지막 수집 시각 연결 대기`} state="ready" />
              <StageCard step="02" title="예측 상태" value={predictedCount} detail={`예측 누락 ${formatCount(predictionMissing)}건 · 마지막 예측 시각 연결 대기`} state={stateForMissing(predictionMissing)} />
              <StageCard step="03" title="평가 상태" value={labeledCount} detail={`라벨 누락 ${formatCount(labelMissing)}건 · 마지막 평가 시각 연결 대기`} state={stateForMissing(labelMissing)} />
            </section>

            <section className="admin-ops-summary">
              <div><span>수집 채널</span><strong>{formatCount(stats.channel_count)}</strong></div>
              <div><span>예측 누락</span><strong>{formatCount(predictionMissing)}</strong></div>
              <div><span>라벨 누락</span><strong>{formatCount(labelMissing)}</strong></div>
              <div><span>현재 모델</span><strong className="admin-pending-value">연결 대기</strong></div>
            </section>

            <PowerBiPlaceholder title="전체 운영 현황" />
          </>
        )}

        {!loading && !error && overview && view === 'pipeline' && (
          <>
            <section className="admin-pipeline-flow" aria-label="파이프라인 단계별 데이터 현황">
              <StageCard step="01" title="데이터 수집" value={stats.video_count} detail={`채널 ${formatCount(stats.channel_count)}개 · 스냅샷 ${formatCount(stats.snapshot_count)}개`} state="ready" />
              <StageCard step="02" title="예측 생성" value={predictedCount} detail={`전체 영상 대비 누락 ${formatCount(predictionMissing)}건`} state={stateForMissing(predictionMissing)} />
              <StageCard step="03" title="라벨 생성" value={labeledCount} detail={`전체 영상 대비 누락 ${formatCount(labelMissing)}건`} state={stateForMissing(labelMissing)} />
            </section>

            <section className="admin-native-panel">
              <div className="admin-native-panel-heading"><h2>운영 데이터 연결 상태</h2><span>React 실시간 영역</span></div>
              <div className="admin-connection-list">
                <div><span>마지막 데이터 수집 시각</span><strong>연결 대기</strong></div>
                <div><span>마지막 예측 생성 시각</span><strong>연결 대기</strong></div>
                <div><span>마지막 라벨 생성 시각</span><strong>연결 대기</strong></div>
                <div><span>Azure 작업 오류</span><strong>연결 대기</strong></div>
              </div>
            </section>

            <PowerBiPlaceholder title="파이프라인 상세 분석" />
          </>
        )}

        {!loading && !error && overview && view === 'quality' && (
          <>
            <section className="admin-quality-summary">
              <article><span>현재 모델 버전</span><strong className="admin-pending-value">연결 대기</strong></article>
              <article><span>평균 절대 오차 · MAE</span><strong className="admin-pending-value">연결 대기</strong></article>
              <article><span>RMSE</span><strong className="admin-pending-value">연결 대기</strong></article>
              <article><span>평가 완료 영상</span><strong>{formatCount(labeledCount)}</strong></article>
            </section>

            <section className="admin-native-panel">
              <div className="admin-native-panel-heading"><h2>모델 운영 상태</h2><span>React 실시간 영역</span></div>
              <div className="admin-model-state">
                <span>모델 버전과 예측 오차 API를 연결하면 현재 운영 모델, MAE, RMSE 및 품질 경고를 이 영역에 표시합니다.</span>
              </div>
            </section>

            <PowerBiPlaceholder title="예측값과 실제값 분석" />
          </>
        )}
      </main>
    </div>
  )
}
