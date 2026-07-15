import * as net from 'net';
import * as path from 'path';
import * as os from 'os';
import * as vscode from 'vscode';

export class DaemonClient {
    private socket: net.Socket | null = null;
    private isConnected: boolean = false;
    private onSuggestionCallback: (suggestion: any) => void = () => {};
    private onClearCallback: () => void = () => {};

    constructor(
        private socketPath: string,
        private fallbackPort: number
    ) {}

    public connect(onStatus: (connected: boolean) => void) {
        if (this.isConnected) {
            return;
        }

        const resolvedPath = this.resolveHome(this.socketPath);
        this.socket = new net.Socket();

        // Try Unix Domain Socket
        this.socket.connect(resolvedPath, () => {
            this.isConnected = true;
            onStatus(true);
            this.setupListeners();
        });

        this.socket.on('error', (err) => {
            // Fallback to TCP loopback
            console.log('Unix socket connection failed, trying TCP fallback...', err.message);
            this.socket = new net.Socket();
            this.socket.connect(this.fallbackPort, '127.0.0.1', () => {
                this.isConnected = true;
                onStatus(true);
                this.setupListeners();
            });

            this.socket.on('error', (tcpErr) => {
                console.error('TCP fallback failed:', tcpErr.message);
                this.isConnected = false;
                onStatus(false);
            });
        });
    }

    private setupListeners() {
        if (!this.socket) { return; }

        let buffer = '';
        this.socket.on('data', (data) => {
            buffer += data.toString();
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.trim()) {
                    try {
                        const msg = JSON.parse(line);
                        if (msg.type === 'suggestion') {
                            this.onSuggestionCallback(msg);
                        } else if (msg.type === 'clear_suggestion') {
                            this.onClearCallback();
                        }
                    } catch (e) {
                        console.error('Failed to parse socket message:', e);
                    }
                }
            }
        });

        this.socket.on('close', () => {
            this.isConnected = false;
        });
    }

    public onSuggestion(callback: (suggestion: any) => void) {
        this.onSuggestionCallback = callback;
    }

    public onClear(callback: () => void) {
        this.onClearCallback = callback;
    }

    public send(data: any) {
        if (this.isConnected && this.socket) {
            this.socket.write(JSON.stringify(data) + '\n');
        }
    }

    public disconnect() {
        if (this.socket) {
            this.socket.destroy();
            this.socket = null;
        }
        this.isConnected = false;
    }

    private resolveHome(filepath: string): string {
        if (filepath.startsWith('~')) {
            return path.join(os.homedir(), filepath.slice(1));
        }
        return path.resolve(filepath);
    }
}
