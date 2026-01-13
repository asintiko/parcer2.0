import { useCallback, useEffect, useRef, useState } from 'react';
import { transactionsApi, Transaction } from '../services/api';
import { db } from '../storage/db';

type SyncProgress = {
    downloaded: number;
    pages: number;
    status?: 'idle' | 'running' | 'done' | 'error';
};

export const useOfflineTransactions = () => {
    const META_VERSION = '1';
    const [data, setData] = useState<Transaction[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isOfflineReady, setIsOfflineReady] = useState(false);
    const [syncProgress, setSyncProgress] = useState<SyncProgress>({ downloaded: 0, pages: 0, status: 'idle' });
    const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
    const retryDelayRef = useRef<number>(5 * 60 * 1000); // 5 minutes

    const sortTransactions = useCallback((items: Transaction[]) => {
        return [...items].sort((a, b) => {
            const at = a.transaction_date ? new Date(a.transaction_date).getTime() : 0;
            const bt = b.transaction_date ? new Date(b.transaction_date).getTime() : 0;
            return at - bt;
        });
    }, []);

    const loadTransactions = useCallback(async () => {
        setIsLoading(true);
        try {
            const [items, meta, versionEntry] = await Promise.all([
                db.transactions.toArray(),
                db.meta.get('lastSyncAt'),
                db.meta.get('version'),
            ]);
            const sorted = sortTransactions(items);
            setData(sorted);
            setIsOfflineReady(items.length > 0);
            setLastSyncAt(meta?.value ?? null);
            if (!versionEntry?.value) {
                db.meta.put({ key: 'version', value: META_VERSION }).catch(() => null);
            }
            return items;
        } catch (error) {
            console.error('Failed to load transactions cache', error);
            setData([]);
            setIsOfflineReady(false);
            setLastSyncAt(null);
            return [];
        } finally {
            setIsLoading(false);
        }
    }, []);

    const syncFromServer = useCallback(async (background = false) => {
        setSyncProgress({ downloaded: 0, pages: 0, status: 'running' });
        if (!background) setIsLoading(true);
        try {
            const pageSize = 1000;
            let page = 1;
            let fetched: Transaction[] = [];

            while (true) {
                const response = await transactionsApi.getTransactions({
                    page,
                    page_size: pageSize,
                    sort_by: 'transaction_date',
                    sort_dir: 'asc',
                });
                const items = response.items || [];
                if (!items.length) break;

                fetched = fetched.concat(items);
                setSyncProgress({
                    downloaded: fetched.length,
                    pages: page,
                    status: 'running',
                });

                if (items.length < pageSize) break;
                page += 1;
            }

            const sortedFetched = sortTransactions(fetched);

            await db.transaction('rw', db.transactions, db.meta, async () => {
                await db.transactions.clear();
                if (sortedFetched.length) {
                    await db.transactions.bulkPut(sortedFetched);
                }
                const now = new Date().toISOString();
                await db.meta.put({ key: 'lastSyncAt', value: now });
                setLastSyncAt(now);
                await db.meta.put({ key: 'version', value: META_VERSION });
            });

            setData(sortedFetched);
            setIsOfflineReady(sortedFetched.length > 0);
            setSyncProgress((prev) => ({ ...prev, status: 'done' }));
            retryDelayRef.current = 5 * 60 * 1000;
        } catch (error) {
            console.error('Failed to sync from server', error);
            setSyncProgress((prev) => ({ ...prev, status: 'error' }));
            retryDelayRef.current = Math.min(retryDelayRef.current * 2, 30 * 60 * 1000);
        } finally {
            if (!background) setIsLoading(false);
        }
    }, [sortTransactions]);

    const upsertTransactions = useCallback(async (transactions: Transaction | Transaction[]) => {
        const list = Array.isArray(transactions) ? transactions : [transactions];
        if (!list.length) return;
        await db.transactions.bulkPut(list);
        setData((prev) => {
            const map = new Map(prev.map((tx) => [tx.id, tx]));
            list.forEach((tx) => {
                const existing = map.get(tx.id) || {};
                map.set(tx.id, { ...existing, ...tx });
            });
            return sortTransactions(Array.from(map.values()));
        });
    }, [sortTransactions]);

    const updateTransactionFields = useCallback(async (updates: Array<{ id: number; fields: Record<string, any> }>) => {
        if (!updates.length) return;
        await db.transaction('rw', db.transactions, async () => {
            for (const update of updates) {
                const existing = await db.transactions.get(update.id);
                if (existing) {
                    await db.transactions.put({ ...existing, ...update.fields });
                }
            }
        });
        setData((prev) =>
            sortTransactions(
                prev.map((tx) => {
                    const update = updates.find((u) => u.id === tx.id);
                    return update ? { ...tx, ...update.fields } : tx;
                })
            )
        );
    }, [sortTransactions]);

    const removeTransactions = useCallback(async (ids: number[]) => {
        if (!ids.length) return;
        await db.transactions.bulkDelete(ids);
        setData((prev) => prev.filter((tx) => !ids.includes(tx.id)));
    }, []);

    useEffect(() => {
        let cancelled = false;
        const init = async () => {
            const items = await loadTransactions();
            if (cancelled) return;
            if (items.length === 0) {
                await syncFromServer(false);
            } else {
                syncFromServer(true);
            }
        };
        init();
        return () => {
            cancelled = true;
        };
    }, [loadTransactions, syncFromServer]);

    useEffect(() => {
        const interval = setInterval(() => {
            syncFromServer(true);
        }, retryDelayRef.current);
        return () => clearInterval(interval);
    }, [syncFromServer]);

    return {
        data,
        isLoading,
        isOfflineReady,
        syncProgress,
        loadTransactions,
        syncFromServer,
        upsertTransactions,
        removeTransactions,
        updateTransactionFields,
        lastSyncAt,
    };
};
