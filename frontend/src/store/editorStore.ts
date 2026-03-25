import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type EditorLanguage = 'python' | 'javascript' | 'java' | 'cpp' | 'go'

export const DEFAULT_SNIPPETS: Record<EditorLanguage, string> = {
  python: 'def solution(nums, target):\n    # Write your solution here\n    return []\n',
  javascript: 'function solution(nums, target) {\n  // Write your solution here\n  return []\n}\n',
  java: 'class Solution {\n  public int[] solution(int[] nums, int target) {\n    return new int[] {};\n  }\n}\n',
  cpp: '#include <vector>\nusing namespace std;\n\nvector<int> solution(vector<int>& nums, int target) {\n  return {};\n}\n',
  go: 'package main\n\nfunc solution(nums []int, target int) []int {\n\treturn []int{}\n}\n',
}

type EditorState = {
  language: EditorLanguage
  codeByLanguage: Record<EditorLanguage, string>
  // Derived convenience getter — current language's code
  code: string
  setLanguage: (language: EditorLanguage) => void
  setCode: (code: string) => void
  resetAllCode: () => void
}

export const useEditorStore = create<EditorState>()(
  persist(
    (set, get) => ({
      language: 'python',
      codeByLanguage: { ...DEFAULT_SNIPPETS },
      get code() {
        return get().codeByLanguage[get().language]
      },
      setLanguage: (language) => {
        set({ language })
      },
      setCode: (code) => {
        const lang = get().language
        set((s) => ({
          codeByLanguage: { ...s.codeByLanguage, [lang]: code },
        }))
      },
      resetAllCode: () => {
        set({ codeByLanguage: { ...DEFAULT_SNIPPETS } })
      },
    }),
    {
      name: 'codexarena-editor',
      partialize: (s) => ({ language: s.language, codeByLanguage: s.codeByLanguage }),
    },
  ),
)
