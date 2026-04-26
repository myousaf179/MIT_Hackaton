import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Copy } from "lucide-react";
import { toast } from "sonner";
import type { PortableCredential } from "@/api";

interface Props {
  credential: PortableCredential;
}

export function PortableCredentialCard({ credential }: Props) {
  const json = JSON.stringify(credential, null, 2);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(json);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Could not copy");
    }
  };

  return (
    <Card className="shadow-[var(--shadow-soft)]">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="text-lg">Portable Credential</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            W3C Verifiable Credential — works across borders
          </p>
        </div>
        <Button onClick={copy} variant="outline" size="sm" className="shrink-0">
          <Copy className="h-4 w-4 mr-2" />
          Copy
        </Button>
      </CardHeader>
      <CardContent>
        <details className="group rounded-lg border bg-muted/40">
          <summary className="cursor-pointer list-none p-3 flex items-center justify-between text-sm font-medium hover:bg-muted/60 rounded-lg">
            <span>View raw JSON</span>
            <span className="text-xs text-muted-foreground group-open:rotate-90 transition-transform">
              ▶
            </span>
          </summary>
          <pre className="p-3 text-xs overflow-auto max-h-96 font-mono text-foreground border-t">
            {json}
          </pre>
        </details>
      </CardContent>
    </Card>
  );
}
