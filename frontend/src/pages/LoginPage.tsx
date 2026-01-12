import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, AlertCircle, CheckCircle, QrCode, Send } from 'lucide-react';
import { authApi } from '../services/api';

export const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const [qrCode, setQrCode] = useState<string | null>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [status, setStatus] = useState<'idle' | 'loading' | 'qr_ready' | 'authenticating' | 'error'>('idle');
    const [error, setError] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState<string>('');

    useEffect(() => {
        // Generate QR code on mount
        generateQRCode();
    }, []);

    useEffect(() => {
        // Poll for authentication status
        if (sessionId && status === 'qr_ready') {
            const interval = setInterval(checkLoginStatus, 2000);
            return () => clearInterval(interval);
        }
    }, [sessionId, status]);

    const generateQRCode = async () => {
        setStatus('loading');
        setError(null);

        try {
            const response = await authApi.generateQR();
            setQrCode(response.qr_code);
            setSessionId(response.session_id);
            setStatus('qr_ready');
            setStatusMessage('Отсканируйте QR-код с помощью Telegram');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Не удалось сгенерировать QR-код');
            setStatus('error');
        }
    };

    const checkLoginStatus = async () => {
        if (!sessionId) return;

        try {
            const response = await authApi.checkQRStatus(sessionId);

            if (response.status === 'authenticated' && response.token) {
                setStatus('authenticating');
                setStatusMessage('Авторизация успешна! Перенаправление...');

                // Save token
                localStorage.setItem('auth_token', response.token);

                // Redirect to main page
                setTimeout(() => {
                    navigate('/');
                    window.location.reload(); // Reload to update auth context
                }, 1000);
            } else if (response.status === 'pending') {
                setStatusMessage('Ожидание сканирования QR-кода...');
            } else if (response.status === 'error' || response.status === 'expired') {
                setError(response.message || 'Сессия истекла');
                setStatus('error');
            }
        } catch (err: any) {
            console.error('Error checking login status:', err);
        }
    };

    const handleRetry = () => {
        setQrCode(null);
        setSessionId(null);
        setError(null);
        setStatusMessage('');
        generateQRCode();
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-bg">
            <div className="w-full max-w-md p-8">
                {/* Logo and Title */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-2xl mb-4">
                        <Send className="w-8 h-8 text-foreground-inverse" />
                    </div>
                    <h1 className="text-3xl font-semibold tracking-wide text-foreground mb-2">
                        PARCER 2.0
                    </h1>
                    <p className="text-foreground-secondary">
                        Вход через Telegram
                    </p>
                </div>

                {/* Main Card */}
                <div className="bg-surface rounded-2xl shadow-xl p-8 border border-border">
                    {/* QR Code Display */}
                    {status === 'loading' && (
                        <div className="flex flex-col items-center justify-center py-12">
                            <Loader2 className="w-12 h-12 text-primary animate-spin mb-4" />
                            <p className="text-foreground-secondary">Генерация QR-кода...</p>
                        </div>
                    )}

                    {status === 'qr_ready' && qrCode && (
                        <div className="flex flex-col items-center">
                            <div className="bg-surface-2 p-4 rounded-xl border-2 border-border mb-4">
                                <img
                                    src={qrCode}
                                    alt="QR Code"
                                    className="w-64 h-64"
                                />
                            </div>

                            <div className="flex items-center gap-2 text-primary mb-2">
                                <QrCode className="w-5 h-5" />
                                <span className="font-medium">Сканируйте QR-код</span>
                            </div>

                            <p className="text-sm text-foreground-secondary text-center mb-4">
                                {statusMessage}
                            </p>

                            <div className="w-full bg-info-light rounded-lg p-4 mt-4 border border-info/30">
                                <p className="text-sm text-info font-medium mb-2">
                                    Как войти:
                                </p>
                                <ol className="text-xs text-info space-y-1 list-decimal list-inside">
                                    <li>Откройте Telegram на телефоне</li>
                                    <li>Перейдите в Настройки → Устройства</li>
                                    <li>Нажмите "Подключить устройство"</li>
                                    <li>Отсканируйте этот QR-код</li>
                                </ol>
                            </div>

                            <button
                                onClick={handleRetry}
                                className="mt-4 text-sm text-foreground-secondary hover:text-foreground underline focus:outline-none focus:ring-2 focus:ring-primary rounded"
                            >
                                Обновить QR-код
                            </button>
                        </div>
                    )}

                    {status === 'authenticating' && (
                        <div className="flex flex-col items-center justify-center py-12">
                            <CheckCircle className="w-16 h-16 text-success mb-4" />
                            <p className="text-lg font-medium text-foreground mb-2">
                                Успешно!
                            </p>
                            <p className="text-sm text-foreground-secondary">
                                {statusMessage}
                            </p>
                        </div>
                    )}

                    {status === 'error' && (
                        <div className="flex flex-col items-center justify-center py-12">
                            <AlertCircle className="w-16 h-16 text-danger mb-4" />
                            <p className="text-lg font-medium text-foreground mb-2">
                                Ошибка
                            </p>
                            <p className="text-sm text-foreground-secondary text-center mb-6">
                                {error}
                            </p>
                            <button
                                onClick={handleRetry}
                                className="px-6 py-2 bg-primary text-foreground-inverse rounded-lg hover:bg-primary-hover transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-surface"
                            >
                                Попробовать снова
                            </button>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <p className="text-center text-sm text-foreground-muted mt-6">
                    Безопасная авторизация через Telegram
                </p>
            </div>
        </div>
    );
};
