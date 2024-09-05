import React, { useState, useEffect } from 'react';
import axios from 'axios';

function SolanaTracker() {
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTransactions = async () => {
            try {
                const response = await axios.get('/api/solana/transactions');
                setTransactions(response.data);
                setLoading(false);
            } catch (err) {
                setError('Failed to fetch Solana transactions');
                setLoading(false);
            }
        };

        fetchTransactions();
    }, []);

    if (loading) return <div>Loading Solana data...</div>;
    if (error) return <div>{error}</div>;

    return (
        <div>
            <h2>Solana Tracker</h2>
            <div>
                <h3>Recent Transactions</h3>
                {transactions.length === 0 ? (
                    <p>No transactions found</p>
                ) : (
                    <ul>
                        {transactions.map((tx, index) => (
                            <li key={index}>
                                <span>Signature: {tx.signature}</span>
                                <span>Amount: {tx.amount} SOL</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}

export default SolanaTracker;
