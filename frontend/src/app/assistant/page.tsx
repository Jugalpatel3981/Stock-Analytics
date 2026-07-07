import { AiChat } from "@/components/assistant/ai-chat";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { requireAuthenticatedUser } from "@/lib/auth-server";

type AssistantPageProps = {
  searchParams?: Promise<{ prompt?: string | string[] }>;
};

export default async function AssistantPage({ searchParams }: AssistantPageProps) {
  const user = await requireAuthenticatedUser();
  const resolvedSearchParams = await searchParams;
  const initialPrompt = Array.isArray(resolvedSearchParams?.prompt)
    ? resolvedSearchParams?.prompt[0]
    : resolvedSearchParams?.prompt;

  return (
    <DashboardShell userName={user.name} activeItem="AI Assistant">
      <div className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase text-muted-foreground">AI research assistant</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal">AI Assistant</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Ask stock research questions using live stock data, news, and sentiment context.
            </p>
          </div>
          <Badge variant="secondary">Informational only</Badge>
        </div>

        <AiChat initialPrompt={initialPrompt} />
      </div>
    </DashboardShell>
  );
}
