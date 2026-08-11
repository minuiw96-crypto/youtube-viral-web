export default function DashboardHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="dashboard-header">
      <div>
        {eyebrow && <p className="dashboard-eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="dashboard-description">{description}</p>}
      </div>
      {actions && <div className="dashboard-header-actions">{actions}</div>}
    </header>
  )
}
