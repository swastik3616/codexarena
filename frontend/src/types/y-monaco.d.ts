declare module 'y-monaco' {
  import type * as monaco from 'monaco-editor'
  import type * as Y from 'yjs'

  export class MonacoBinding {
    constructor(
      yText: Y.Text,
      monacoModel: monaco.editor.ITextModel,
      editors: Set<monaco.editor.IStandaloneCodeEditor>,
      awareness?: unknown,
    )
    destroy(): void
  }
}

