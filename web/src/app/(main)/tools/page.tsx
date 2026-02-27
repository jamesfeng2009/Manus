"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import {
  Mail,
  Calendar,
  Github,
  FileText,
  BookOpen,
  CheckCircle2,
  XCircle,
  RefreshCw,
} from "lucide-react"

const tools = [
  {
    id: "email",
    name: "Email",
    description: "Send and receive emails via SMTP or API",
    icon: Mail,
    enabled: true,
    connected: true,
  },
  {
    id: "calendar",
    name: "Calendar",
    description: "Manage calendar events via Google Calendar or Outlook",
    icon: Calendar,
    enabled: true,
    connected: false,
  },
  {
    id: "github",
    name: "GitHub",
    description: "Manage issues, pull requests, and repositories",
    icon: Github,
    enabled: true,
    connected: true,
  },
  {
    id: "notion",
    name: "Notion",
    description: "Create and manage Notion pages and databases",
    icon: FileText,
    enabled: true,
    connected: false,
  },
  {
    id: "obsidian",
    name: "Obsidian",
    description: "Read, write, and search Obsidian notes",
    icon: BookOpen,
    enabled: false,
    connected: false,
  },
]

export default function ToolsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Tools</h2>
      </div>

      <div className="grid gap-6">
        {tools.map((tool) => (
          <Card key={tool.id}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-muted">
                  <tool.icon className="w-6 h-6" />
                </div>
                <div>
                  <CardTitle className="text-lg">{tool.name}</CardTitle>
                  <CardDescription>{tool.description}</CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {tool.connected ? (
                  <Badge variant="default" className="bg-green-500">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    Connected
                  </Badge>
                ) : (
                  <Badge variant="outline">
                    <XCircle className="w-3 h-3 mr-1" />
                    Not Connected
                  </Badge>
                )}
                <Switch checked={tool.enabled} />
              </div>
            </CardHeader>
            {tool.enabled && (
              <CardContent>
                <div className="flex items-end gap-4">
                  <div className="flex-1 space-y-2">
                    <Label htmlFor={`${tool.id}-api-key`}>API Key / Token</Label>
                    <Input
                      id={`${tool.id}-api-key`}
                      type="password"
                      placeholder="Enter your API key"
                      defaultValue={
                        tool.id === "github" ? "ghp_xxxxxxxxxxxx" : undefined
                      }
                    />
                  </div>
                  <Button variant="outline">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Test
                  </Button>
                  <Button>Save</Button>
                </div>
              </CardContent>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}
