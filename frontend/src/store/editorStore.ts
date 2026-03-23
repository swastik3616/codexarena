import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type EditorLanguage = 'python' | 'javascript' | 'java' | 'cpp' | 'go'

type EditorState = {
  language: EditorLanguage
  code: string
  setLanguage: (language: EditorLanguage) => void
  setCode: (code: string) => void
}

const DEFAULT_SNIPPETS: Record<EditorLanguage, string> = {
  python: 'def solution(nums, target):\n    # Write your solution here\n    return []\n',
  javascript: 'function solution(nums, target) {\n  // Write your solution here\n  return []\n}\n',
  java: 'class Solution {\n  public int[] solution(int[] nums, int target) {\n    return new int[] {};\n  }\n}\n',
  cpp: '#include <vector>\nusing namespace std;\n\nvector<int> solution(vector<int>& nums, int target) {\n  return {};\n}\n',
  go: 'package main\n\nfunc solution(nums []int, target int) []int {\n\treturn []int{}\n}\n',
}

export const useEditorStore = create<EditorState>()(
  persist(
    (set, get) => ({
      language: 'python',
      code: DEFAULT_SNIPPETS.python,
      setLanguage: (language) => {
        const current = get().language
        set({
          language,
          // If current code is empty-ish, reset to language template.
          code: get().code.trim().length === 0 || get().code === DEFAULT_SNIPPETS[current] ? DEFAULT_SNIPPETS[language] : get().code,
        })
      },
      setCode: (code) => set({ code }),
    }),
    {
      name: 'codexarena-editor',
      partialize: (s) => ({ language: s.language, code: s.code }),
    },
  ),
)

