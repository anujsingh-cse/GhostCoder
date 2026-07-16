import * as vscode from 'vscode';
import { DaemonClient } from './daemon';
import { DecorationManager } from './decorations';

let daemonClient: DaemonClient | null = null;
let decorationManager: DecorationManager | null = null;
let statusBarItem: vscode.StatusBarItem | null = null;
let isEnabled = true;

export function activate(context: vscode.ExtensionContext) {
    console.log('GhostCoder is now active.');

    const config = vscode.workspace.getConfiguration('ghostcoder');
    const socketPath = config.get<string>('socketPath', '~/.ghostcoder/ghostcoder.sock');
    const fallbackPort = config.get<number>('fallbackPort', 48673);

    daemonClient = new DaemonClient(socketPath, fallbackPort);
    decorationManager = new DecorationManager();

    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '👻 GhostCoder: Idle';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Initialize connection
    connectDaemon();

    // Handle incoming suggestions
    daemonClient.onSuggestion((suggestion) => {
        const editor = vscode.window.activeTextEditor;
        if (editor && isEnabled && decorationManager) {
            decorationManager.showSuggestion(editor, suggestion);
            if (statusBarItem) {
                statusBarItem.text = `👻 GhostCoder: Active (${suggestion.agent})`;
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
            }
        }
    });

    daemonClient.onClear(() => {
        const editor = vscode.window.activeTextEditor;
        if (editor && decorationManager) {
            decorationManager.clearSuggestion(editor);
            resetStatusBar();
        }
    });

    // Listen to changes in the active text editor
    vscode.workspace.onDidChangeTextDocument((event) => {
        if (!isEnabled || !daemonClient) { return; }
        const editor = vscode.window.activeTextEditor;
        if (editor && event.document === editor.document) {
            daemonClient.send({
                type: 'editor_change',
                file: event.document.fileName,
                content: event.document.getText(),
                line: editor.selection.active.line
            });
        }
    });

    // Command bindings
    const enableCmd = vscode.commands.registerCommand('ghostcoder.enable', () => {
        isEnabled = true;
        connectDaemon();
        vscode.window.showInformationMessage('GhostCoder enabled.');
    });

    const disableCmd = vscode.commands.registerCommand('ghostcoder.disable', () => {
        isEnabled = false;
        if (daemonClient) {
            daemonClient.disconnect();
        }
        const editor = vscode.window.activeTextEditor;
        if (editor && decorationManager) {
            decorationManager.clearSuggestion(editor);
        }
        if (statusBarItem) {
            statusBarItem.text = '👻 GhostCoder: Disabled';
            statusBarItem.backgroundColor = undefined;
        }
        vscode.window.showInformationMessage('GhostCoder disabled.');
    });

    const showHintCmd = vscode.commands.registerCommand('ghostcoder.showLastHint', () => {
        if (decorationManager) {
            const sugg = decorationManager.getActiveSuggestion();
            if (sugg) {
                vscode.window.showInformationMessage(`[${sugg.agent}]: ${sugg.hint}`);
            } else {
                vscode.window.showInformationMessage('No active suggestion.');
            }
        }
    });

    const applyCmd = vscode.commands.registerCommand('ghostcoder.applySuggestion', () => {
        const editor = vscode.window.activeTextEditor;
        const decManager = decorationManager;
        if (editor && decManager) {
            const sugg = decManager.getActiveSuggestion();
            const activeLine = decManager.getActiveSuggestionLine();
            if (sugg && activeLine !== null) {
                const fix = sugg.fix;
                if (fix) {
                    editor.edit((editBuilder) => {
                        const line = editor.document.lineAt(activeLine);
                        editBuilder.replace(line.range, fix);
                    }).then((success) => {
                        if (success) {
                            if (daemonClient) {
                                daemonClient.send({ type: 'action', action: 'apply' });
                            }
                            decManager.clearSuggestion(editor);
                            resetStatusBar();
                            vscode.window.showInformationMessage('Suggestion applied!');
                        }
                    });
                } else {
                    vscode.window.showInformationMessage('No automated fix available for this suggestion.');
                }
            }
        }
    });

    const applySkepticCmd = vscode.commands.registerCommand('ghostcoder.applySkepticSuggestion', () => {
        const editor = vscode.window.activeTextEditor;
        const decManager = decorationManager;
        if (editor && decManager) {
            const sugg = decManager.getActiveSuggestion();
            const activeLine = decManager.getActiveSuggestionLine();
            if (sugg && activeLine !== null) {
                const skeptic_fix = sugg.skeptic_fix;
                if (skeptic_fix) {
                    editor.edit((editBuilder) => {
                        const line = editor.document.lineAt(activeLine);
                        editBuilder.replace(line.range, skeptic_fix);
                    }).then((success) => {
                        if (success) {
                            if (daemonClient) {
                                daemonClient.send({ type: 'action', action: 'apply_skeptic' });
                            }
                            decManager.clearSuggestion(editor);
                            resetStatusBar();
                            vscode.window.showInformationMessage('Skeptic\'s improved suggestion applied!');
                        }
                    });
                } else {
                    vscode.window.showInformationMessage('No Skeptic improved fix available for this suggestion.');
                }
            }
        }
    });

    const dismissCmd = vscode.commands.registerCommand('ghostcoder.dismissSuggestion', () => {
        const editor = vscode.window.activeTextEditor;
        const decManager = decorationManager;
        if (editor && decManager) {
            if (daemonClient) {
                daemonClient.send({ type: 'action', action: 'dismiss' });
            }
            decManager.clearSuggestion(editor);
            resetStatusBar();
            vscode.window.showInformationMessage('Suggestion dismissed.');
        }
    });

    const hoverProvider = vscode.languages.registerHoverProvider({ scheme: 'file' }, {
        provideHover(document, position, token) {
            const decManager = decorationManager;
            if (decManager) {
                const sugg = decManager.getActiveSuggestion();
                const activeLine = decManager.getActiveSuggestionLine();
                if (sugg && activeLine !== null && position.line === activeLine) {
                    const markdown = new vscode.MarkdownString();
                    markdown.isTrusted = true;
                    
                    if (sugg.skeptic_blocked) {
                        markdown.appendMarkdown(`### 👻 GhostCoder [Skeptic Blocked]\n\n`);
                        markdown.appendMarkdown(`**The original suggestion was blocked due to critical flaws.**\n\n`);
                    } else {
                        markdown.appendMarkdown(`### 👻 GhostCoder Suggestion\n\n`);
                        markdown.appendMarkdown(`**Agent**: \`${sugg.agent}\`\n\n`);
                        markdown.appendMarkdown(`**Suggestion**:\n${sugg.hint}\n\n`);
                    }

                    if (sugg.challenges && sugg.challenges.length > 0) {
                        markdown.appendMarkdown(`#### Skeptic Challenges:\n`);
                        sugg.challenges.forEach((c: any) => {
                            markdown.appendMarkdown(`- **[${c.severity.toUpperCase()}]** ${c.flaw}\n`);
                            markdown.appendMarkdown(`  *Scenario:* ${c.scenario}\n`);
                            markdown.appendMarkdown(`  *Proposed Fix:* \`${c.fix}\`\n`);
                        });
                        markdown.appendMarkdown(`\n`);
                    }

                    if (sugg.skeptic_blocked) {
                        markdown.appendMarkdown(`---\n\n`);
                        if (sugg.skeptic_fix) {
                            markdown.appendMarkdown(`[⚡ Apply Skeptic Fix](command:ghostcoder.applySkepticSuggestion) | `);
                        }
                        markdown.appendMarkdown(`[❌ Dismiss](command:ghostcoder.dismissSuggestion)\n\n`);
                        markdown.appendMarkdown(`*Press **Alt+S** to apply Skeptic's improved version, or **Alt+D** to dismiss.*`);
                    } else {
                        markdown.appendMarkdown(`---\n\n`);
                        if (sugg.fix) {
                            markdown.appendMarkdown(`[⚡ Apply Fix](command:ghostcoder.applySuggestion) | `);
                        }
                        if (sugg.skeptic_fix) {
                            markdown.appendMarkdown(`[⚡ Apply Skeptic Fix](command:ghostcoder.applySkepticSuggestion) | `);
                        }
                        markdown.appendMarkdown(`[❌ Dismiss](command:ghostcoder.dismissSuggestion)\n\n`);
                        markdown.appendMarkdown(`*Press **Alt+A** to apply original recommendation, **Alt+S** to apply Skeptic's version, or **Alt+D** to dismiss.*`);
                    }
                    return new vscode.Hover(markdown);
                }
            }
            return null;
        }
    });

    const codeActionProvider = vscode.languages.registerCodeActionsProvider({ scheme: 'file' }, new GhostCodeActionProvider(), {
        providedCodeActionKinds: [vscode.CodeActionKind.QuickFix]
    });

    context.subscriptions.push(enableCmd, disableCmd, showHintCmd, applyCmd, applySkepticCmd, dismissCmd, hoverProvider, codeActionProvider);
}

class GhostCodeActionProvider implements vscode.CodeActionProvider {
    public provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<(vscode.Command | vscode.CodeAction)[]> {
        const decManager = decorationManager;
        if (!decManager) return [];
        
        const sugg = decManager.getActiveSuggestion();
        const activeLine = decManager.getActiveSuggestionLine();
        
        if (sugg && activeLine !== null && (range.start.line === activeLine || range.end.line === activeLine)) {
            const actions: vscode.CodeAction[] = [];
            
            if (sugg.skeptic_blocked) {
                if (sugg.skeptic_fix) {
                    const action = new vscode.CodeAction('👻 Apply Skeptic Improved Fix', vscode.CodeActionKind.QuickFix);
                    action.command = {
                        command: 'ghostcoder.applySkepticSuggestion',
                        title: 'Apply Skeptic Improved Fix'
                    };
                    action.isPreferred = true;
                    actions.push(action);
                }
            } else {
                if (sugg.fix) {
                    const action = new vscode.CodeAction('👻 Apply GhostCoder Fix', vscode.CodeActionKind.QuickFix);
                    action.command = {
                        command: 'ghostcoder.applySuggestion',
                        title: 'Apply GhostCoder Fix'
                    };
                    action.isPreferred = true;
                    actions.push(action);
                }
                if (sugg.skeptic_fix) {
                    const action = new vscode.CodeAction('👻 Apply Skeptic Improved Fix', vscode.CodeActionKind.QuickFix);
                    action.command = {
                        command: 'ghostcoder.applySkepticSuggestion',
                        title: 'Apply Skeptic Improved Fix'
                    };
                    actions.push(action);
                }
            }
            
            const dismissAction = new vscode.CodeAction('👻 Dismiss Suggestion', vscode.CodeActionKind.QuickFix);
            dismissAction.command = {
                command: 'ghostcoder.dismissSuggestion',
                title: 'Dismiss Suggestion'
            };
            actions.push(dismissAction);
            
            return actions;
        }
        return [];
    }
}

function connectDaemon() {
    if (daemonClient) {
        daemonClient.connect((connected) => {
            if (connected) {
                resetStatusBar();
            } else {
                if (statusBarItem) {
                    statusBarItem.text = '👻 GhostCoder: Offline';
                    statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                }
            }
        });
    }
}

function resetStatusBar() {
    if (statusBarItem) {
        statusBarItem.text = '👻 GhostCoder: Watching';
        statusBarItem.backgroundColor = undefined;
        statusBarItem.tooltip = 'GhostCoder is watching files and command logs.';
    }
}

export function deactivate() {
    if (daemonClient) {
        daemonClient.disconnect();
    }
}
