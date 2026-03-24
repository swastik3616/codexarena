import { ArcElement, Chart as ChartJS, Legend, Tooltip } from 'chart.js'
import { Doughnut } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend)

type Props = {
  correctness: number
  efficiency: number
  readability: number
  edgeCases: number
}

export function ScoreBreakdown({ correctness, efficiency, readability, edgeCases }: Props) {
  const total = correctness + efficiency + readability + edgeCases
  const data = {
    labels: ['Correctness', 'Efficiency', 'Readability', 'Edge Cases'],
    datasets: [
      {
        data: [correctness, efficiency, readability, edgeCases],
        backgroundColor: ['#3b82f6', '#22c55e', '#a855f7', '#f59e0b'],
        borderColor: '#0f172a',
        borderWidth: 3,
      },
    ],
  }

  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-sm font-semibold text-slate-100 mb-3">Score Breakdown</h3>
      <div className="relative h-64">
        <Doughnut data={data} options={{ cutout: '68%', plugins: { legend: { display: false } } }} />
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <p className="text-3xl font-bold text-slate-100">{total}/100</p>
          <p className="text-xs text-slate-400">Total score</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded bg-slate-950 p-2 text-blue-300">Correctness: {correctness}/40</div>
        <div className="rounded bg-slate-950 p-2 text-green-300">Efficiency: {efficiency}/30</div>
        <div className="rounded bg-slate-950 p-2 text-purple-300">Readability: {readability}/20</div>
        <div className="rounded bg-slate-950 p-2 text-amber-300">Edge Cases: {edgeCases}/10</div>
      </div>
    </section>
  )
}

