/**
 * Main Application Component with Routing
 */
import { useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { BurgerMenu } from './components/BurgerMenu';
import { TransactionsPage } from './pages/TransactionsPage';
import { ReferencePage } from './pages/ReferencePage';
import { AutomationPage } from './pages/AutomationPage';
import { UserbotPage } from './pages/UserbotPage';

function AppContent() {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const location = useLocation();

    const getPageTitle = () => {
        switch (location.pathname) {
            case '/':
                return 'Транзакции';
            case '/reference':
                return 'Справочник операторов';
            case '/automation':
                return 'Автоматизация';
            case '/userbot':
                return 'Telegram Bots';
            default:
                return 'Транзакции';
        }
    };

    return (
        <div className="h-screen w-full bg-bg flex flex-col">
            <BurgerMenu isOpen={isMenuOpen} onClose={() => setIsMenuOpen(false)} />

            {/* Top Header */}
            <header className="flex items-center h-14 px-4 bg-surface border-b border-border shadow-sm z-10 flex-shrink-0">
                <button
                    onClick={() => setIsMenuOpen(true)}
                    className="p-2 mr-4 rounded-lg hover:bg-surface-2 text-foreground-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
                >
                    <Menu className="w-5 h-5" />
                </button>
                <h1 className="text-lg font-semibold text-foreground">{getPageTitle()}</h1>
            </header>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden">
                <Routes>
                    <Route path="/" element={<TransactionsPage />} />
                    <Route path="/reference" element={<ReferencePage />} />
                    <Route path="/automation" element={<AutomationPage />} />
                    <Route path="/userbot" element={<UserbotPage />} />
                </Routes>
            </div>
        </div>
    );
}

function App() {
    return (
        <BrowserRouter>
            <AppContent />
        </BrowserRouter>
    );
}

export default App;
