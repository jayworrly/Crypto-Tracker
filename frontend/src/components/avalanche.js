import React, { useEffect, useState, useRef } from 'react';
import './avalanche.css';

function Avalanche({ ScrollableOutput }) {
    const [output, setOutput] = useState('');
    const [error, setError] = useState('');
    const eventSourceRef = useRef(null);
    const intervalRef = useRef(null);

    const startAvalancheScript = async () => {
        try {
            const response = await fetch('/start-flask', {
                method: 'POST',
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            console.log("Received data:", data);

            if (data.status === 'running' || data.status === 'already_running') {
                setOutput(prevOutput => prevOutput + data.output);
                if (!eventSourceRef.current) {
                    startSSE();
                }
            } else if (data.status === 'error') {
                setError(data.error || 'An unknown error occurred');
                console.error('Error from server:', data.error);
            } else {
                setError('Unexpected response status: ' + data.status);
                console.error('Unexpected response status:', data.status, 'Full response:', data);
            }
        } catch (err) {
            console.error("Fetch error:", err);
            setError('Failed to start Avalanche script: ' + err.message);
        }
    };

    const startSSE = () => {
        eventSourceRef.current = new EventSource('/stream-output');
        
        eventSourceRef.current.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setOutput(prevOutput => prevOutput + data.output);
        };

        eventSourceRef.current.onerror = (error) => {
            console.error("SSE error:", error);
            setError('Failed to receive updates: ' + error.message);
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        };
    };

    useEffect(() => {
        startAvalancheScript(); // Initial call

        // Set up interval for continuous polling every 1 second
        intervalRef.current = setInterval(startAvalancheScript, 1000);

        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, []);

    return (
        <div className="avalanche-container">
            <h1>Avalanche DEX Transactions</h1>
            <p>Here you can view recent DEX transactions on the Avalanche network.</p>
            {output && (
                <div className="scrollable-output-container">
                    <h2>Output:</h2>
                    <ScrollableOutput content={output} />
                </div>
            )}
            {error && <p className="error-message">Error: {error}</p>}
        </div>
    );
}

export default Avalanche;
