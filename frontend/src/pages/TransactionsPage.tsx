/**
 * Transactions Page Component
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { transactionsApi } from '../services/api';
import { TransactionTable } from '../components/TransactionTable';

export function TransactionsPage() {
    const [page] = useState(1);

    const { data, isLoading } = useQuery({
        queryKey: ['transactions', page],
        queryFn: () =>
            transactionsApi.getTransactions({
                page,
                page_size: 500,
            }),
        refetchInterval: 30000,
    });

    return (
        <div className="h-full flex flex-col bg-bg">
            <div className="flex-1 overflow-hidden p-4">
                <div className="h-full flex flex-col bg-surface border border-table-border rounded-lg shadow-sm">
                    <div className="flex-1 overflow-hidden p-0">
                        <TransactionTable
                            data={data?.transactions || []}
                            isLoading={isLoading}
                        />
                    </div>
                    {data && (
                        <div className="px-4 py-2 border-t border-table-border text-xs text-foreground-secondary bg-surface-2">
                            Всего записей: {data.total}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
