import React, { useState, createContext, useContext, ReactNode } from 'react';
import { CheckCircle, XCircle, Info, AlertTriangle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
    id: string;
    type: ToastType;
    message: string;
    duration?: number;
}

interface ToastContextValue {
    showToast: (type: ToastType, message: string, duration?: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
};

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const showToast = (type: ToastType, message: string, duration = 3000) => {
        const id = `${Date.now()}-${Math.random()}`;
        const newToast: Toast = { id, type, message, duration };
        setToasts((prev) => [...prev, newToast]);

        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, duration);
    };

    return (
        <ToastContext.Provider value={{ showToast }}>
            {children}
            <div className="fixed bottom-4 right-4 z-[9999] space-y-2">
                {toasts.map((toast) => (
                    <ToastItem key={toast.id} toast={toast} />
                ))}
            </div>
        </ToastContext.Provider>
    );
};

const ToastItem: React.FC<{ toast: Toast }> = ({ toast }) => {
    const icons = {
        success: CheckCircle,
        error: XCircle,
        info: Info,
        warning: AlertTriangle,
    };

    const colors = {
        success: 'bg-success-light text-success border-success/30 dark:bg-success-light dark:text-success dark:border-success/30',
        error: 'bg-danger-light text-danger border-danger/30 dark:bg-danger-light dark:text-danger dark:border-danger/30',
        info: 'bg-info-light text-info border-info/30 dark:bg-info-light dark:text-info dark:border-info/30',
        warning: 'bg-warning-light text-warning border-warning/30 dark:bg-warning-light dark:text-warning dark:border-warning/30',
    };

    const Icon = icons[toast.type];

    return (
        <div
            className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg min-w-[300px] animate-slide-in ${colors[toast.type]}`}
        >
            <Icon className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm font-medium">{toast.message}</p>
        </div>
    );
};
