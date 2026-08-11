export default function DashboardHeader({ title, description }) {
  return (
    <header className="dashboard-header">
      <div>
        <h1>{title}</h1>
        {description && <p className="dashboard-description">{description}</p>}
      </div>
    </header>
  )
}
