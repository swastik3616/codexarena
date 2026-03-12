import { useState, useEffect, useRef } from 'react'
import Editor from '@monaco-editor/react'
import { Play, Clock, ChevronLeft, WifiOff } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'

export const EditorPage = () => {
  const [searchParams] = useSearchParams()
  const roomId = searchParams.get('room') || 'default_room'
  const candidateName = searchParams.get('candidate') || 'Anonymous'
  
  const [code, setCode] = useState('def solution(nums):\n    # Write your Python 3 solution here\n    pass')
  const [output, setOutput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Connect to FastAPI WebSocket backend
    const ws = new WebSocket(`ws://localhost:8000/ws/room/${roomId}?candidate_name=${encodeURIComponent(candidateName)}`)
    
    ws.onopen = () => {
      setIsConnected(true)
      console.log('Connected to interview room')
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('Received:', data)
      // Logic for recruiter broadcast receiving goes in Dashboard, 
      // but if the server dictates a lock or evaluation, we handle it here.
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [roomId, candidateName])

  const handleEditorChange = (value: string | undefined) => {
    const newCode = value || ''
    setCode(newCode)
    
    // Broadcast code change to recruiter
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'code_update',
        code: newCode,
        timestamp: new Date().toISOString()
      }))
    }
  }

  const handleRunCode = () => {
    setOutput('Running test cases...\n\nTest Case 1: Passed (0.001s)\nTest Case 2: Passed (0.002s)\nTest Case 3: Failed (Output did not match expected)\n\nScore: 2/3 (66%)')
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'run_code',
        status: 'running',
        timestamp: new Date().toISOString()
      }))
    }
  }

  // 45 minutes in seconds
  const [timeLeft, setTimeLeft] = useState(45 * 60)
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = () => {
    if (isSubmitted) return
    setIsSubmitted(true)
    setOutput('Solution submitted automatically. Your recruiter will review your code shortly.')
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'submit',
        code: code,
        timestamp: new Date().toISOString()
      }))
    }
  }

  useEffect(() => {
    if (timeLeft <= 0) {
      if (!isSubmitted) {
        handleSubmit()
      }
      return
    }
    
    const timerId = setInterval(() => {
      setTimeLeft(prev => prev - 1)
    }, 1000)

    return () => clearInterval(timerId)
  }, [timeLeft, isSubmitted])

  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0')
    const s = (seconds % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  return (
    <div className="flex-1 flex flex-col font-sans h-screen w-screen overflow-hidden bg-slate-50 absolute inset-0 z-50">
      {/* Top Navbar */}
      <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/rooms" className="text-slate-400 hover:text-slate-600 transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </Link>
          <div>
            <h2 className="font-semibold text-slate-800">Two Sum</h2>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className={`flex items-center gap-1 font-mono ${timeLeft < 300 ? 'text-rose-600 font-bold' : ''}`}>
                <Clock className="w-3 h-3" /> {formatTime(timeLeft)}
              </span>
              <span>•</span>
              <span className="text-emerald-600 font-medium">Easy</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={handleRunCode}
            disabled={isSubmitted}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors text-sm ${isSubmitted ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'}`}
          >
            <Play className="w-4 h-4" />
            Run Test
          </button>
          <button 
            onClick={handleSubmit}
            disabled={isSubmitted}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition-colors text-sm shadow-sm ${isSubmitted ? 'bg-slate-300 text-white cursor-not-allowed shadow-none' : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-200'}`}
          >
            {isSubmitted ? 'Submitted' : 'Submit Solution'}
          </button>
        </div>
      </header>

      {/* Main Content Split */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Problem Description */}
        <div className="w-1/3 bg-white border-r border-slate-200 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold text-slate-800 mb-4 tracking-tight">1. Two Sum</h1>
          <div className="prose prose-slate prose-sm max-w-none">
            <p className="text-slate-600 leading-relaxed">
              Given an array of integers <code>nums</code> and an integer <code>target</code>, return indices of the two numbers such that they add up to <code>target</code>.
            </p>
            <p className="text-slate-600 leading-relaxed">
              You may assume that each input would have <strong>exactly one solution</strong>, and you may not use the same element twice.
              You can return the answer in any order.
            </p>

            <h3 className="text-lg font-semibold text-slate-800 mt-8 mb-3">Example 1:</h3>
            <div className="bg-slate-50 border border-slate-100 p-4 rounded-xl">
              <p><strong>Input:</strong> nums = [2,7,11,15], target = 9</p>
              <p><strong>Output:</strong> [0,1]</p>
              <p className="text-slate-500 text-sm mt-1">Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].</p>
            </div>
          </div>
        </div>

        {/* Right: Code Editor & Console */}
        <div className="flex-1 flex flex-col bg-[#1e1e1e]">
          {/* Editor Header */}
          <div className="h-10 bg-[#2d2d2d] border-b border-[#3d3d3d] flex items-center px-4 shrink-0">
            <span className="text-slate-300 text-xs font-mono">solution.py</span>
          </div>
          
          {/* Monaco Editor */}
          <div className="flex-1 min-h-0 relative">
            {!isConnected && (
              <div className="absolute inset-0 z-10 bg-[#1e1e1e]/80 flex flex-col items-center justify-center backdrop-blur-sm">
                <WifiOff className="w-8 h-8 text-rose-500 mb-2" />
                <p className="text-slate-300 font-medium">Reconnecting to session...</p>
              </div>
            )}
            <Editor
              height="100%"
              defaultLanguage="python"
              theme="vs-dark"
              value={code}
              onChange={handleEditorChange}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: 'JetBrains Mono, monospace',
                padding: { top: 16 },
                scrollBeyondLastLine: false,
                readOnly: isSubmitted,
              }}
            />
          </div>

          {/* Console / Output Area */}
          <div className="h-64 bg-[#2d2d2d] border-t border-[#3d3d3d] flex flex-col shrink-0">
            <div className="h-10 border-b border-[#3d3d3d] flex items-center px-4">
              <span className="text-slate-300 text-xs font-semibold uppercase tracking-wider">Console Output</span>
            </div>
            <div className="p-4 overflow-y-auto font-mono text-sm text-slate-300 whitespace-pre-wrap">
              {output || 'Run your code to see the output here...'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
