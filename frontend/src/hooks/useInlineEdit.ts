import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { transactionsApi, TransactionUpdateRequest } from '../services/api';
import { useToast } from '../components/Toast';

export interface EditingCell {
    rowId: number;
    columnId: string;
}

export interface UseInlineEditOptions {
    onSuccess?: (rowId: number, columnId: string) => void;
    onError?: (error: Error, rowId: number, columnId: string) => void;
}

export const useInlineEdit = (options?: UseInlineEditOptions) => {
    const queryClient = useQueryClient();
    const [editingCell, setEditingCell] = useState<EditingCell | null>(null);
    const { showToast } = useToast();

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: number; data: TransactionUpdateRequest }) =>
            transactionsApi.updateTransaction(id, data),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['transactions'] });
            showToast('success', 'Изменения сохранены');
            options?.onSuccess?.(variables.id, Object.keys(variables.data)[0]);
        },
        onError: (error: Error, variables) => {
            showToast('error', `Ошибка сохранения: ${error.message}`);
            options?.onError?.(error, variables.id, Object.keys(variables.data)[0]);
        },
    });

    const startEdit = useCallback((rowId: number, columnId: string) => {
        setEditingCell({ rowId, columnId });
    }, []);

    const cancelEdit = useCallback(() => {
        setEditingCell(null);
    }, []);

    const saveEdit = useCallback(
        async (rowId: number, columnId: string, newValue: any) => {
            // Map UI column IDs to API field names
            const fieldMap: Record<string, string> = {
                transaction_date: 'datetime',
                operator_raw: 'operator',
                application_mapped: 'app',
                amount: 'amount',
                balance_after: 'balance',
                card_last_4: 'card_last4',
                is_p2p: 'is_p2p',
                transaction_type: 'transaction_type',
                currency: 'currency',
                source_type: 'source',
            };

            const apiField = fieldMap[columnId] || columnId;
            const updateData: TransactionUpdateRequest = {
                [apiField]: newValue,
            };

            await updateMutation.mutateAsync({ id: rowId, data: updateData });
        },
        [updateMutation]
    );

    return {
        editingCell,
        startEdit,
        cancelEdit,
        saveEdit,
        isSaving: updateMutation.isPending,
    };
};
