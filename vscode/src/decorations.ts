import * as vscode from 'vscode';

export class DecorationManager {
    private decorationType: vscode.TextEditorDecorationType | null = null;
    private activeSuggestion: any = null;
    private activeLine: number | null = null;

    constructor() {
        this.createDecorationType();
    }

    private createDecorationType() {
        this.decorationType = vscode.window.createTextEditorDecorationType({
            after: {
                color: '#888888',
                fontStyle: 'italic',
                margin: '0 0 0 1em'
            }
        });
    }

    public showSuggestion(editor: vscode.TextEditor, suggestion: any) {
        if (!this.decorationType) {
            this.createDecorationType();
        }

        this.activeSuggestion = suggestion;
        const hint = suggestion.hint || '';
        const agent = suggestion.agent || 'GhostCoder';
        
        // Clean multi-lines for inline rendering
        const singleLineHint = hint.split('\n')[0];
        
        let displayText = "";
        if (suggestion.skeptic_blocked) {
            let flaws = "Blocked by Skeptic";
            if (suggestion.challenges && suggestion.challenges.length > 0) {
                flaws = "Blocked: " + suggestion.challenges.map((c: any) => c.flaw).join(', ');
            }
            displayText = `👻 [Skeptic Blocked]: ${flaws}`;
        } else {
            displayText = `👻 [${agent}]: ${singleLineHint}`;
        }

        // Anchor decoration to the end of the line
        const cursorPosition = editor.selection.active;
        this.activeLine = cursorPosition.line;
        const line = editor.document.lineAt(cursorPosition.line);
        const endPosition = new vscode.Position(cursorPosition.line, line.text.length);
        const range = new vscode.Range(endPosition, endPosition);

        const decoration: vscode.DecorationOptions = {
            range,
            renderOptions: {
                after: {
                    contentText: displayText
                }
            }
        };

        if (this.decorationType) {
            editor.setDecorations(this.decorationType, [decoration]);
        }
    }

    public clearSuggestion(editor: vscode.TextEditor) {
        this.activeSuggestion = null;
        this.activeLine = null;
        if (this.decorationType) {
            editor.setDecorations(this.decorationType, []);
        }
    }

    public getActiveSuggestion() {
        return this.activeSuggestion;
    }

    public getActiveSuggestionLine() {
        return this.activeLine;
    }
}
