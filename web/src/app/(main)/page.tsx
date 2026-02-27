import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  ListTodo,
  Play,
  CheckCircle2,
  Clock,
  TrendingUp,
} from "lucide-react"

const stats = [
  { label: "Total Tasks", value: "156", icon: ListTodo, trend: "+12%" },
  { label: "Running", value: "3", icon: Play, trend: "-2%" },
  { label: "Completed", value: "142", icon: CheckCircle2, trend: "+8%" },
  { label: "Avg Time", value: "2.5m", icon: Clock, trend: "-15%" },
]

const recentTasks = [
  { id: 1, name: "Research AI agents", status: "completed", progress: 100 },
  { id: 2, name: "Generate report", status: "running", progress: 65 },
  { id: 3, name: "Web scraping task", status: "pending", progress: 0 },
  { id: 4, name: "Data analysis", status: "completed", progress: 100 },
]

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <Button>New Task</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.label}
              </CardTitle>
              <stat.icon className="w-4 h-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <TrendingUp className="w-3 h-3" />
                {stat.trend} from last month
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentTasks.map((task) => (
                <div key={task.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-medium leading-none">
                        {task.name}
                      </p>
                      <Badge
                        variant={
                          task.status === "completed"
                            ? "default"
                            : task.status === "running"
                            ? "secondary"
                            : "outline"
                        }
                      >
                        {task.status}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Progress value={task.progress} className="w-20" />
                    <span className="text-sm text-muted-foreground">
                      {task.progress}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            <Button variant="outline" className="justify-start">
              <ListTodo className="w-4 h-4 mr-2" />
              Create new task
            </Button>
            <Button variant="outline" className="justify-start">
              <Clock className="w-4 h-4 mr-2" />
              View scheduled tasks
            </Button>
            <Button variant="outline" className="justify-start">
              <TrendingUp className="w-4 h-4 mr-2" />
              Usage statistics
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
