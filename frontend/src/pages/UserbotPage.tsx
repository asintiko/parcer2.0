import React, { useState, useRef } from 'react';
import { Info } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useTelegramThemeSync } from '../hooks/useTelegramThemeSync';

const TELEGRAM_WEB_SRC = '/tweb/index.html';

export const UserbotPage: React.FC = () => {
    const [showInstructions, setShowInstructions] = useState(true);
    const { isDark } = useTheme();
    const iframeRef = useRef<HTMLIFrameElement>(null);

    // Синхронизация темы с Telegram Web K
    useTelegramThemeSync(iframeRef);

    // Формируем URL с параметром темы
    const iframeSrc = `${TELEGRAM_WEB_SRC}?theme=${isDark ? 'dark' : 'light'}`;

    return (
        <div className="h-full w-full bg-bg flex flex-col relative">
            {/* Instructions Banner */}
            {showInstructions && (
                <div className="bg-info-light border-b border-info/30 px-4 py-3 flex items-start gap-3 relative z-10">
                    <Info className="w-5 h-5 text-info flex-shrink-0 mt-0.5" />
                    <div className="flex-1 text-sm text-info">
                        <p className="font-semibold mb-1">Добро пожаловать в Telegram Bots</p>
                        <p className="text-info">
                            Войдите в свой Telegram аккаунт, чтобы начать работу с ботами.
                            После входа вы сможете взаимодействовать только с ботами.
                        </p>
                        <ul className="mt-2 space-y-1 text-info list-disc list-inside">
                            <li>Используйте QR-код или номер телефона для входа</li>
                            <li>Доступ только к ботам (режим Bot-Only)</li>
                            <li>Все сообщения синхронизируются с вашим основным аккаунтом</li>
                        </ul>
                    </div>
                    <button
                        onClick={() => setShowInstructions(false)}
                        className="text-info hover:text-info-hover focus:outline-none focus:ring-2 focus:ring-primary rounded"
                    >
                        ✕
                    </button>
                </div>
            )}

            {/* Telegram Web K iframe */}
            <div className="flex-1 relative bg-bg">
                <iframe
                    ref={iframeRef}
                    title="Telegram Web (Bots only)"
                    src={iframeSrc}
                    className="w-full h-full border-0"
                    allow="clipboard-read; clipboard-write; microphone; camera"
                    sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals allow-storage-access-by-user-activation"
                />
            </div>
        </div>
    );
};
