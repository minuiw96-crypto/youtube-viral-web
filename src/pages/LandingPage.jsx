import { Link } from 'react-router-dom'
import NavBar from '../components/NavBar'
import Footer from '../components/Footer'
import heroBg from '../assets/hero-bg.png'

const FEATURES = [
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </svg>
    ),
    title: '바이럴 예측 및 스코어링',
    desc: 'URL 하나만 입력하면 AI가 조회수·참여도 패턴을 분석해 100점 만점의 바이럴 스코어와 등급을 알려줍니다. 게시 전 예측부터 게시 후 추적까지 한 번에.',
    cta: '바이럴 스코어 확인하기',
    to: '/register',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="9" rx="1.5" />
        <rect x="14" y="3" width="7" height="5" rx="1.5" />
        <rect x="14" y="12" width="7" height="9" rx="1.5" />
        <rect x="3" y="16" width="7" height="5" rx="1.5" />
      </svg>
    ),
    title: '채널 대시보드 및 리포팅',
    desc: '구독자, 조회수, 참여도 성장을 통합 대시보드에서 관리하고, 실시간 추적과 랭킹으로 채널 성과를 한눈에 파악하세요.',
    cta: '대시보드 살펴보기',
    to: '/register',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 11.5a8.5 8.5 0 1 1-4-7.2" />
        <path d="M21 4v6h-6" />
      </svg>
    ),
    title: '데이터 기반 인사이트 (AI 챗봇)',
    desc: '실시간 채널 데이터와 업계 트렌드를 학습한 AI에게 직접 물어보고, 우리 채널만을 위한 맞춤 인사이트를 얻으세요.',
    cta: 'AI에게 물어보기',
    to: '/register',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M9 3H5a2 2 0 0 0-2 2v4M15 3h4a2 2 0 0 1 2 2v4M9 21H5a2 2 0 0 1-2-2v-4M15 21h4a2 2 0 0 0 2-2v-4" />
      </svg>
    ),
    title: 'API 연동을 통한 커스텀 데이터 제공',
    desc: '브랜드·파트너를 위한 맞춤형 데이터 및 분석 리포트를 API로 연동해 제공합니다.',
    cta: '문의하기',
    to: '/register',
  },
]

const PLANS = [
  {
    name: 'Free',
    price: '₩0',
    period: '/ 월',
    features: [
      '월 5회 바이럴 스코어 조회',
      '기본 채널 대시보드',
      '커뮤니티 지원',
    ],
    cta: '무료로 시작하기',
    featured: false,
  },
  {
    name: 'Pro',
    price: '₩29,000',
    period: '/ 월',
    features: [
      '무제한 바이럴 스코어 조회',
      'AI 인사이트 챗봇',
      '채널 성과 리포트 다운로드',
      '우선 지원',
    ],
    cta: 'Pro 시작하기',
    featured: true,
  },
  {
    name: 'Enterprise',
    price: '문의',
    period: '',
    features: [
      '커스텀 API 연동',
      '맞춤형 데이터 리포트',
      '전담 매니저',
      'SLA 지원',
    ],
    cta: '문의하기',
    featured: false,
  },
]

export default function LandingPage() {
  return (
    <>
      <NavBar />

      <section className="hero">
        <img src={heroBg} alt="" className="hero-bg" />
        <div className="hero-overlay" />
        <div className="container hero-content">
          <span className="hero-eyebrow">YouTube Viral Success Predictor</span>
          <h1 className="hero-title">영상이 뜨기 전에, 먼저 확인하세요</h1>
          <p className="hero-subtitle">
            AI 기반 바이럴 스코어와 채널 분석으로 유튜브 크리에이터의 다음 성장을 예측하는
            인플루언서 마케팅 통합 솔루션입니다.
          </p>
          <div className="hero-actions">
            <Link to="/register" className="btn btn-primary">무료로 시작하기</Link>
            <a href="#features" className="btn btn-outline">기능 살펴보기</a>
          </div>
        </div>
      </section>

      <section className="section" id="features">
        <div className="container">
          <div className="section-head">
            <span className="section-eyebrow">Features</span>
            <h2 className="section-title">바이럴 마케팅을 위한 통합 솔루션</h2>
            <p className="section-desc">
              예측부터 분석, 리포팅까지 — PredicTube 하나로 끝냅니다.
            </p>
          </div>
          <div className="features">
            {FEATURES.map((f) => (
              <div className="feature-card" key={f.title}>
                <div className="feature-icon">{f.icon}</div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
                <Link to={f.to} className="btn btn-outline btn-sm">{f.cta}</Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-soft" id="pricing">
        <div className="container">
          <div className="section-head">
            <span className="section-eyebrow">Pricing</span>
            <h2 className="section-title">우리 채널에 맞는 요금제를 선택하세요</h2>
            <p className="section-desc">
              언제든 변경 가능하며, 숨겨진 비용 없이 투명하게 운영됩니다.
            </p>
          </div>
          <div className="pricing">
            {PLANS.map((p) => (
              <div className={`price-card${p.featured ? ' featured' : ''}`} key={p.name}>
                {p.featured && <span className="price-badge">가장 인기</span>}
                <span className="price-name">{p.name}</span>
                <span className="price-amount">
                  {p.price}
                  {p.period && <span>{p.period}</span>}
                </span>
                <ul className="price-list">
                  {p.features.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <Link
                  to="/register"
                  className={`btn ${p.featured ? 'btn-primary' : 'btn-outline'} btn-block`}
                >
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </>
  )
}
