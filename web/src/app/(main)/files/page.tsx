"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import {
  Folder,
  File,
  FileText,
  Image,
  Upload,
  Download,
  Trash2,
  MoreHorizontal,
  Search,
  ChevronRight,
  Home,
} from "lucide-react"

const files = [
  { name: "documents", type: "folder", size: "-", modified: "2024-01-15 10:30" },
  { name: "images", type: "folder", size: "-", modified: "2024-01-15 09:00" },
  { name: "reports", type: "folder", size: "-", modified: "2024-01-14 16:00" },
  { name: "readme.md", type: "text", size: "2.4 KB", modified: "2024-01-15 11:00" },
  { name: "data.csv", type: "text", size: "156 KB", modified: "2024-01-14 14:30" },
  { name: "screenshot.png", type: "image", size: "1.2 MB", modified: "2024-01-13 10:00" },
]

const getIcon = (type: string) => {
  switch (type) {
    case "folder":
      return Folder
    case "image":
      return Image
    case "text":
      return FileText
    default:
      return File
  }
}

export default function FilesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Files</h2>
        <Button>
          <Upload className="w-4 h-4 mr-2" />
          Upload
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/files">
                <Home className="w-4 h-4" />
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="w-4 h-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href="/files/documents">documents</BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Search files..." className="pl-9" />
        </div>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Modified</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {files.map((file) => {
              const Icon = getIcon(file.type)
              return (
                <TableRow key={file.name}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Icon className="w-5 h-5 text-muted-foreground" />
                      <span className="font-medium">{file.name}</span>
                      {file.type === "folder" && (
                        <Badge variant="secondary">Folder</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{file.size}</TableCell>
                  <TableCell>{file.modified}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon">
                        <Download className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="icon">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
