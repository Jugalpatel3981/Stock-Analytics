import Link from "next/link";

import { AuthShell } from "@/components/auth/auth-shell";
import { DemoLoginButton } from "@/components/auth/demo-login-button";
import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <AuthShell
      title="Sign in"
      description="Access your portfolio intelligence dashboard."
      footer={(
        <>
          New to the platform?{" "}
          <Link className="font-medium text-primary hover:underline" href="/register">
            Create an account
          </Link>
        </>
      )}
    >
      <LoginForm />
      <div className="my-5 flex items-center gap-3 text-xs uppercase text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>
      <DemoLoginButton className="w-full" variant="outline" />
    </AuthShell>
  );
}
