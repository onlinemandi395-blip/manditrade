import Hero3D from "../components/Hero3D";
import GlassCard from "../components/GlassCard";
import type { PageProps } from "../app/routes";

export default function LoginPage(_: PageProps) {
  return (
    <section className="login-layout">
      <Hero3D height={420} scene="login-hero" />
      <GlassCard className="login-card">
        <p className="section-heading__eyebrow">Digital Bharat Mandi</p>
        <h2>Trade, jobs, khata, and local operations in one warm control center.</h2>
        <p>
          This starter shell keeps identity abstracted. Plug your existing Google sign-in
          button here and land each user into their RBAC workspace.
        </p>
        <button className="primary-button primary-button--large" type="button">
          Continue with Google
        </button>
        <div className="login-card__meta">
          <span className="badge badge--SUCCESS">Google-only access</span>
          <span className="badge badge--OPEN">WebGL hero optional</span>
        </div>
      </GlassCard>
    </section>
  );
}
