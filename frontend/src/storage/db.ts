import Dexie, { Table } from 'dexie';
import { Transaction } from '../services/api';

export type MetaEntry = {
    key: string;
    value: string;
};

class TransactionsDB extends Dexie {
    transactions!: Table<Transaction, number>;
    meta!: Table<MetaEntry, string>;

    constructor() {
        super('transactions-db');
        this.version(1).stores({
            transactions: '&id, transaction_date, currency, operator_raw, application_mapped',
            meta: '&key',
        });
    }
}

export const db = new TransactionsDB();
