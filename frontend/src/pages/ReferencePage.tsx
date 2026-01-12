/**
 * Reference Directory Page
 * CRUD operations for operator/seller reference dictionary
 */
import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { referenceApi, OperatorReference, OperatorReferenceCreate } from '../services/api';
import { Search, Plus, Download, Upload, Edit2, Trash2, X } from 'lucide-react';

export function ReferencePage() {
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingOperator, setEditingOperator] = useState<OperatorReference | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const { data, isLoading } = useQuery({
        queryKey: ['operators', page, search],
        queryFn: () =>
            referenceApi.getOperators({
                page,
                page_size: 50,
                search: search || undefined,
            }),
    });

    const createMutation = useMutation({
        mutationFn: referenceApi.createOperator,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['operators'] });
            setIsModalOpen(false);
        },
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: number; data: OperatorReferenceCreate }) =>
            referenceApi.updateOperator(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['operators'] });
            setIsModalOpen(false);
            setEditingOperator(null);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: referenceApi.deleteOperator,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['operators'] });
        },
    });

    const handleExport = async () => {
        try {
            const blob = await referenceApi.exportToExcel();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'operators.xlsx';
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Export failed:', error);
            alert('Ошибка экспорта');
        }
    };

    const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        try {
            const result = await referenceApi.importFromExcel(file);
            queryClient.invalidateQueries({ queryKey: ['operators'] });
            alert(`Импортировано: ${result.imported}, Пропущено: ${result.skipped}`);
            if (result.errors.length > 0) {
                console.error('Import errors:', result.errors);
            }
        } catch (error) {
            console.error('Import failed:', error);
            alert('Ошибка импорта');
        }

        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleEdit = (operator: OperatorReference) => {
        setEditingOperator(operator);
        setIsModalOpen(true);
    };

    const handleDelete = async (id: number) => {
        if (confirm('Удалить оператора?')) {
            deleteMutation.mutate(id);
        }
    };

    const handleAddNew = () => {
        setEditingOperator(null);
        setIsModalOpen(true);
    };

    return (
        <div className="h-full flex flex-col bg-bg">
            {/* Header */}
            <div className="bg-surface border-b border-border px-6 py-4">
                <div className="flex items-center justify-between mb-4">
                    <h1 className="text-2xl font-bold text-foreground">Справочник операторов</h1>
                    <div className="flex gap-2">
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="flex items-center gap-2 px-4 py-2 bg-success text-foreground-inverse rounded-lg hover:bg-success-hover transition-colors focus:outline-none focus:ring-2 focus:ring-success"
                        >
                            <Upload size={18} />
                            Импорт Excel
                        </button>
                        <button
                            onClick={handleExport}
                            className="flex items-center gap-2 px-4 py-2 bg-primary text-foreground-inverse rounded-lg hover:bg-primary-hover transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                            <Download size={18} />
                            Экспорт Excel
                        </button>
                        <button
                            onClick={handleAddNew}
                            className="flex items-center gap-2 px-4 py-2 bg-primary-dark text-foreground-inverse rounded-lg hover:bg-primary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                            <Plus size={18} />
                            Добавить
                        </button>
                    </div>
                </div>

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted" size={20} />
                    <input
                        type="text"
                        placeholder="Поиск по оператору или приложению..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-surface text-foreground"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="flex-1 overflow-auto px-6 py-4">
                <div className="bg-surface rounded-lg border border-border overflow-hidden">
                    <table className="w-full">
                        <thead className="bg-table-header border-b border-table-border">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider">
                                    ID
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider">
                                    Оператор/Продавец
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider">
                                    Приложение
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider">
                                    P2P
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider">
                                    Статус
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-foreground-secondary uppercase tracking-wider">
                                    Действия
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {isLoading ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-foreground-secondary">
                                        Загрузка...
                                    </td>
                                </tr>
                            ) : data?.items.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-foreground-secondary">
                                        Нет данных
                                    </td>
                                </tr>
                            ) : (
                                data?.items.map((operator) => (
                                    <tr key={operator.id} className="hover:bg-table-row-hover">
                                        <td className="px-6 py-4 text-sm text-foreground">{operator.id}</td>
                                        <td className="px-6 py-4 text-sm text-foreground">{operator.operator_name}</td>
                                        <td className="px-6 py-4 text-sm text-foreground">{operator.application_name}</td>
                                        <td className="px-6 py-4 text-sm">
                                            <span
                                                className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                                    operator.is_p2p
                                                        ? 'bg-success-light text-success'
                                                        : 'bg-surface-2 text-foreground-secondary'
                                                }`}
                                            >
                                                {operator.is_p2p ? 'Да' : 'Нет'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm">
                                            <span
                                                className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                                    operator.is_active
                                                        ? 'bg-success-light text-success'
                                                        : 'bg-danger-light text-danger'
                                                }`}
                                            >
                                                {operator.is_active ? 'Активен' : 'Неактивен'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-right">
                                            <button
                                                onClick={() => handleEdit(operator)}
                                                className="text-primary hover:text-primary-hover mr-3 focus:outline-none focus:ring-2 focus:ring-primary rounded"
                                            >
                                                <Edit2 size={18} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(operator.id)}
                                                className="text-danger hover:text-danger-hover focus:outline-none focus:ring-2 focus:ring-danger rounded"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {data && data.total > 0 && (
                    <div className="mt-4 flex items-center justify-between">
                        <div className="text-sm text-foreground-secondary">
                            Показано {(page - 1) * 50 + 1}-{Math.min(page * 50, data.total)} из {data.total}
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setPage(page - 1)}
                                disabled={page === 1}
                                className="px-4 py-2 border border-border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface-2 bg-surface text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                            >
                                Назад
                            </button>
                            <button
                                onClick={() => setPage(page + 1)}
                                disabled={page * 50 >= data.total}
                                className="px-4 py-2 border border-border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface-2 bg-surface text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                            >
                                Вперед
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Hidden file input */}
            <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleImport}
                className="hidden"
            />

            {/* Add/Edit Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-modal-overlay flex items-center justify-center z-50" onClick={(e) => {
                    if (e.target === e.currentTarget) {
                        setIsModalOpen(false);
                        setEditingOperator(null);
                    }
                }}>
                    <OperatorModal
                        operator={editingOperator}
                        onClose={() => {
                            setIsModalOpen(false);
                            setEditingOperator(null);
                        }}
                        onSubmit={(data) => {
                            if (editingOperator) {
                                updateMutation.mutate({ id: editingOperator.id, data });
                            } else {
                                createMutation.mutate(data);
                            }
                        }}
                    />
                </div>
            )}
        </div>
    );
}

interface OperatorModalProps {
    operator: OperatorReference | null;
    onClose: () => void;
    onSubmit: (data: OperatorReferenceCreate) => void;
}

function OperatorModal({ operator, onClose, onSubmit }: OperatorModalProps) {
    const [formData, setFormData] = useState<OperatorReferenceCreate>({
        operator_name: operator?.operator_name || '',
        application_name: operator?.application_name || '',
        is_p2p: operator?.is_p2p ?? true,
        is_active: operator?.is_active ?? true,
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit(formData);
    };

    return (
        <div className="bg-modal-bg rounded-lg shadow-xl w-full max-w-md border border-modal-border"
             onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <h2 className="text-xl font-semibold text-foreground">
                        {operator ? 'Редактировать оператора' : 'Добавить оператора'}
                    </h2>
                    <button onClick={onClose} className="text-foreground-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary rounded">
                        <X size={24} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="px-6 py-4">
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">
                                Оператор/Продавец
                            </label>
                            <input
                                type="text"
                                required
                                value={formData.operator_name}
                                onChange={(e) => setFormData({ ...formData, operator_name: e.target.value })}
                                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-surface text-foreground"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">Приложение</label>
                            <input
                                type="text"
                                required
                                value={formData.application_name}
                                onChange={(e) => setFormData({ ...formData, application_name: e.target.value })}
                                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-surface text-foreground"
                            />
                        </div>

                        <div className="flex items-center">
                            <input
                                type="checkbox"
                                id="is_p2p"
                                checked={formData.is_p2p}
                                onChange={(e) => setFormData({ ...formData, is_p2p: e.target.checked })}
                                className="w-4 h-4 text-primary border-border rounded focus:ring-primary"
                            />
                            <label htmlFor="is_p2p" className="ml-2 text-sm text-foreground">
                                P2P транзакция
                            </label>
                        </div>

                        <div className="flex items-center">
                            <input
                                type="checkbox"
                                id="is_active"
                                checked={formData.is_active}
                                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                className="w-4 h-4 text-primary border-border rounded focus:ring-primary"
                            />
                            <label htmlFor="is_active" className="ml-2 text-sm text-foreground">
                                Активен
                            </label>
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 mt-6">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 border border-border rounded-lg hover:bg-surface-2 bg-surface text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                            Отмена
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-primary text-foreground-inverse rounded-lg hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-surface"
                        >
                            {operator ? 'Сохранить' : 'Добавить'}
                        </button>
                    </div>
                </form>
        </div>
    );
}
