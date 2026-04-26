import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Download, Trophy } from "lucide-react";
import { toast } from "sonner";
import type { PortableCredential, SkillMatch } from "@/api";

interface Props {
  profile: SkillMatch[];
  credential: PortableCredential;
}

export function SkillsProfileCard({ profile, credential }: Props) {
  const exportCredential = () => {
    const blob = new Blob([JSON.stringify(credential, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "portable-credential.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Credential downloaded");
  };

  return (
    <Card className="shadow-[var(--shadow-soft)]">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="text-lg">Skills Profile</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Matched against ISCO-08 and ESCO taxonomies
          </p>
        </div>
        <Button onClick={exportCredential} size="sm" variant="outline" className="shrink-0">
          <Download className="h-4 w-4 mr-2" />
          Export Credential
        </Button>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {[...profile]
            .sort((a, b) => b.confidence - a.confidence)
            .map((s, idx) => (
            <li
              key={s.isco_code + s.name}
              className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-3 rounded-lg border bg-[var(--gradient-card)]"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium text-foreground">{s.name}</p>
                  {idx === 0 && (
                    <Badge className="bg-primary/10 text-primary border-primary/20 border gap-1">
                      <Trophy className="h-3 w-3" />
                      Top match
                    </Badge>
                  )}
                </div>
                <div className="flex flex-wrap gap-2 mt-1">
                  <Badge variant="secondary" className="font-mono text-xs">
                    ISCO {s.isco_code}
                  </Badge>
                  <Badge variant="outline" className="font-mono text-xs">
                    ESCO {s.esco_code}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${Math.round(s.confidence * 100)}%` }}
                  />
                </div>
                <span className="text-sm font-medium tabular-nums w-10 text-right">
                  {Math.round(s.confidence * 100)}%
                </span>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
